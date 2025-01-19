"""
This module provides functionality to convert video annotations into JSON-LD format.
It includes the following main functions:

1. annotations_to_jsonLD(annotations, isAutomatic: bool):
    - Converts video annotations into a JSON-LD graph.
    - Binds various namespaces to the RDF graph.
    - Adds nodes and triples for video, concepts, and prerequisites.
    - Serializes the RDF graph into JSON-LD format.
    - Compacts the JSON-LD using a provided context.
    - Returns the RDF graph and the compacted JSON-LD data.

2. graph_to_rdf(jsonld):
    - Converts JSON-LD data into an RDF graph.

"""
from rdflib import Graph, URIRef, RDF, BNode, ConjunctiveGraph, Namespace
from rdflib.namespace import SKOS, XSD
from rdflib.term import Literal
from rdflib.serializer import Serializer

import json
import pyld
import time
from datetime import datetime
import database.mongo as mongo


oa = Namespace("http://www.w3.org/ns/oa#")
dc = Namespace("http://purl.org/dc/elements/1.1/")
dctypes = Namespace("http://purl.org/dc/dcmitype/")
dcterms = Namespace("http://purl.org/dc/terms/")
edu = Namespace("https://teldh.github.io/edurell#")

edurell = "https://teldh.github.io/edurell#"
context = ["http://www.w3.org/ns/anno.jsonld", {"edu": edurell}]


def annotations_to_jsonLD(annotations, isAutomatic:bool):
    """
    Converts video annotations into a JSON-LD graph.

    Parameters
    ----------
    annotations : dict
        A dictionary containing video annotations.
    isAutomatic : bool
        A flag indicating whether the annotations are automatic.

    Returns
    -------
    g : rdflib.Graph
        The RDF graph containing the annotations.
    data : dict
        The compacted JSON-LD data.

    Examples
    --------
    >>> annotations = {
    ...     "id": "video1",
    ...     "definitions": [{"concept": "example", "description_type": "type", "start": "2023-01-01T00:00:00", "start_sent_id": "1", "end": "2023-01-01T00:01:00", "end_sent_id": "2"}],
    ...     "relations": [{"target": "example", "prerequisite": "example2", "time": "2023-01-01T00:00:00", "xywh": "None", "sent_id": "1", "word_id": "None"}],
    ...     "annotator": "http://example.org/annotator"
    ... }
    >>> g, data = annotations_to_jsonLD(annotations, isAutomatic=False)
    """

    print("***** EKEEL - Video Annotation: ontology.py::to_jsonLD(): Inizio ******")

    concepts_anno = []
    prereq_anno = []

    if "definitions" in annotations:
        concepts_anno = annotations["definitions"]
    if "relations" in annotations:    
        prereq_anno = annotations["relations"]
    video_id = annotations["id"]

    if not isAutomatic:
        creator = annotations["annotator"]
        creator = URIRef(creator)

    g = Graph()

    g.bind("oa", oa)
    g.bind("dctypes", dctypes)
    g.bind("edu", edu)
    g.bind("SKOS", SKOS)
    g.bind("dcterms", dcterms)


    # aggiunge un nodo
    video = URIRef("video_" + str(video_id))
    #video = URIRef(edurell + "video_" + str(video_id))
    g.add((video, RDF.type, dctypes.MovingImage))

    conll = URIRef("conll_" + str(video_id))
    #conll = URIRef(edurell + "conll_" + str(video_id))
    g.add((conll, RDF.type, dctypes.Text))


    # collegamento video conll
    ann_linking_conll = URIRef("ann0")
    #ann_linking_conll = URIRef(edurell + "ann0")
    g.add((ann_linking_conll, RDF.type, oa.Annotation))
    g.add((ann_linking_conll, oa.motivatedBy, edu.linkingConll))
    g.add((ann_linking_conll, oa.hasBody, conll))
    g.add((ann_linking_conll, oa.hasTarget, video))

    date = Literal(datetime.now())

    #creo il nuovo nodo dei concetti
    #localVocabulary = URIRef("localVocabulary")
    #g.add((localVocabulary, RDF.type, SKOS.Collection))


    # per ogni annotazione di concetto spiegato aggiungo le triple
    for i, annotation in enumerate(concepts_anno):
        ann = URIRef("ann" + str(i + 1))

        g.add((ann, RDF.type, oa.Annotation))

        if isAutomatic:
            g.add((ann, dcterms.creator, URIRef(annotation["creator"])))
        else:
            g.add((ann, dcterms.creator, creator))

        g.add((ann, dcterms.created, date))
        g.add((ann, oa.motivatedBy, oa.describing))
        g.add((ann, SKOS.note, Literal("concept"+annotation["description_type"])))


        concept = URIRef("concept_" + annotation["concept"].replace(" ", "_"))

        #crea un nodo concetto
        
        #g.add((localVocabulary, SKOS.member, concept))
        #g.add((concept, RDF.type, SKOS.Concept))


        g.add((ann, oa.hasBody, concept))

        blank_target = BNode()

        
        blank_selector = BNode()

        g.add((ann, oa.hasTarget, blank_target))
        g.add((blank_target, RDF.type, oa.SpecificResource))

        g.add((blank_target, oa.hasSelector, blank_selector))
        g.add((blank_selector, RDF.type, oa.RangeSelector))

        g.add((blank_target, oa.hasSource, video))

        blank_startSelector = BNode()
        blank_endSelector = BNode()

        g.add((blank_startSelector, RDF.type, edu.InstantSelector))
        g.add((blank_endSelector, RDF.type, edu.InstantSelector))

        g.add((blank_selector, oa.hasStartSelector, blank_startSelector))
        g.add((blank_selector, oa.hasEndSelector, blank_endSelector))

        g.add((blank_startSelector, RDF.value, Literal(annotation["start"] + "^^xsd:dateTime")))
        g.add((blank_startSelector, edu.conllSentId, Literal(annotation["start_sent_id"])))
        #g.add((blank_startSelector, edu.conllWordId, Literal(annotation["word_id"])))

        g.add((blank_endSelector, RDF.value, Literal(annotation["end"] + "^^xsd:dateTime")))
        g.add((blank_endSelector, edu.conllSentId, Literal(annotation["end_sent_id"])))
        

    num_definitions = len(concepts_anno) + 1

    # per ogni annotazione di prerequisito aggiungo le triple
    for i, annotation in enumerate(prereq_anno):
        ann = URIRef("ann" + str(num_definitions + i))

        target_concept = URIRef("concept_" +  annotation["target"].replace(" ", "_"))
        prereq_concept = URIRef("concept_" +  annotation["prerequisite"].replace(" ", "_"))

        #g.add((target_concept, RDF.type, SKOS.Concept))
        #g.add((prereq_concept, RDF.type, SKOS.Concept))

        g.add((ann, RDF.type, oa.Annotation))

        if isAutomatic:
            g.add((ann, dcterms.creator, URIRef(annotation["creator"])))
        else:
            g.add((ann, dcterms.creator, creator))

        g.add((ann, dcterms.created, date))
        g.add((ann, oa.motivatedBy, edu.linkingPrerequisite))

        g.add((ann, oa.hasBody, prereq_concept))
        g.add((ann, SKOS.note, Literal(annotation["weight"] + "Prerequisite")))

        blank_target = BNode()

        g.add((ann, oa.hasTarget, blank_target))
        g.add((blank_target, RDF.type, oa.SpecificResource))
        g.add((blank_target, dcterms.subject, target_concept))

        g.add((blank_target, oa.hasSource, video))

        blank_selector_video = BNode()

        g.add((blank_target, oa.hasSelector, blank_selector_video))
        g.add((blank_selector_video, RDF.type, edu.InstantSelector))
        g.add((blank_selector_video, RDF.value, Literal(annotation["time"] + "^^xsd:dateTime")))

        if annotation["xywh"] != "None":
            g.add((blank_selector_video, edu.hasMediaFrag, Literal(annotation["xywh"])))


        g.add((blank_selector_video, edu.conllSentId, Literal(annotation["sent_id"])))

        if annotation["word_id"] != "None":
            g.add((blank_selector_video, edu.conllWordId, Literal(annotation["word_id"])))

    # stampo il grafo in formato turtle
    # turtle = g.serialize(format='turtle').decode("utf-8")
    # print(turtle)

    # creo file json-ld

    #jsonld = json.loads(g.serialize(format='json-ld', context=context))

    jsonld = json.loads(g.serialize(format='json-ld'))
    jsonld = pyld.jsonld.compact(jsonld, context)

    '''
    Nested nodes creation
    
    FROM:                            |  TO:
    {                                |  {
        ...                          |    ...
        "target": 123                |     "target":{
    },                               |                 "id":123,
    {                                |                  "type":example
        "id": 123,                   |               }
        "type": example              |   }
    }
    
    '''

    for o in jsonld["@graph"]:
        if "target" in o:
            for i, t in enumerate(jsonld["@graph"]):
                if o["motivation"] != "edu:linkingConll" and o["target"] == t["id"]:
                    o["target"] = t
                    del jsonld["@graph"][i]
                    for j, s in enumerate(jsonld["@graph"]):
                        if o["target"]["selector"] == s["id"]:
                            o["target"]["selector"] = s
                            del jsonld["@graph"][j]

                            if o["motivation"] == "describing":
                                for k, p in enumerate(jsonld["@graph"]):
                                    if o["target"]["selector"]["startSelector"] == p["id"]:
                                        o["target"]["selector"]["startSelector"] = p
                                        del jsonld["@graph"][k]
                                        break

                                for k, p in enumerate(jsonld["@graph"]):
                                    if o["target"]["selector"]["endSelector"] == p["id"]:
                                        o["target"]["selector"]["endSelector"] = p
                                        del jsonld["@graph"][k]
                                        break

    #print(jsonld)
    data = {
        "graph":jsonld
    }

    #print(data)
    print("***** EKEEL - Video Annotation: ontology.py::to_jsonLD(): Fine ******")

    return g, data


# transform the jsonld graph back to rdflib
def graph_to_rdf(jsonld):
    """
    Converts JSON-LD data into an RDF graph.

    Parameters
    ----------
    jsonld : dict
        A dictionary containing JSON-LD data.

    Returns
    -------
    g : rdflib.Graph
        The RDF graph parsed from the JSON-LD data.

    Examples
    --------
    >>> jsonld = {
    ...     "@context": "http://schema.org",
    ...     "@type": "Person",
    ...     "name": "Jane Doe"
    ... }
    >>> g = graph_to_rdf(jsonld)
    """
    json_expanded = pyld.jsonld.expand(jsonld)

    return Graph().parse(data=json.dumps(json_expanded), format='json-ld')


if __name__ == '__main__':

    #print("***** EKEEL - Video Annotation: ontology.py::__main__: Inizio ******")

    #json_graph = db_mongo.get_graph("616726e4d1a3488902b4b55d", "sXLhYStO0m8")
    json_graph = mongo.get_graph("Burst Analysis", "PPLop4L2eGk")

    from pprint import pprint
    #pprint(json_graph)

    json_expanded = pyld.jsonld.expand(json_graph)
    pprint(json_expanded[0])

    gr = Graph()\
        .parse(data=json.dumps(json_graph), format='json-ld')

    tic = time.time()

    # Seleziona i concetti che sono spiegati nel video
    query1 = """
        PREFIX oa: <http://www.w3.org/ns/oa#>
        PREFIX edu: <'https://teldh.github.io/edurell#>
        SELECT ?explained_concept
           WHERE {
                ?concept_annotation oa:motivatedBy oa:describing.
                ?concept_annotation oa:hasBody ?explained_concept.
            }"""

    query2 = """
        PREFIX oa: <http://www.w3.org/ns/oa#>
        PREFIX edu: <'https://teldh.github.io/edurell#>
        PREFIX rdf: <'http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
        SELECT ?explained_concept ?start
           WHERE {
                ?concept_annotation oa:motivatedBy oa:describing.
                ?concept_annotation oa:hasBody ?explained_concept.
                ?concept_annotation oa:hasTarget ?targ.
                ?targ oa:hasSelector ?selector.
                ?selector oa:hasStartSelector ?start_selector.
                ?start_selector rdf:value ?start_sent_id.
                
            }"""

    qres = gr.query(query2)
    
    toc = time.time()

    print("Results: - obtained in %.4f seconds" % (toc - tic))
    for row in qres:
        print(row)
        print("%s, %d" % row)

    #print("***** EKEEL - Video Annotation: ontology.py::__main__: Fine ******")    
