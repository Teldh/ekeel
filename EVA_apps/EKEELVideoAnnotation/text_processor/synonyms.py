import copy
import json
import pyld
from rdflib.serializer import Serializer
from nltk.corpus import wordnet as wn
from rdflib import Graph, URIRef, Literal, BNode, Namespace, RDF
from rdflib.namespace import FOAF, NamespaceManager
from rdflib.namespace import SKOS, XSD

def get_synonyms_from_list(concepts:list):
    """
    Find synonyms from a list of words using WordNet NLTK.

    Parameters
    ----------
    concepts : list
        List of words to find synonyms for

    Returns
    -------
    dict
        Dictionary with words as keys and lists of found synonyms as values

    Notes
    -----
    Words with spaces are converted to underscore format for WordNet lookup
    and converted back to spaces in the output
    """
    synonyms=dict()

    keywords = copy.copy(concepts)
    converter = lambda x: x.replace(' ', '_')
    keywords = list(map(converter, keywords))

    synonymsFound={}
    for starting_keyword in keywords:
        wordnetSynset1 = wn.synsets(starting_keyword)
        tempList1=[]
        synonymsFoundTemp=[]
        for synset1 in wordnetSynset1:
            for synWords1 in synset1.lemma_names():
                if(synWords1.lower() != starting_keyword.lower()):
                    tempList1.append(synWords1.lower())

        tempList1=list(set(tempList1))        
        
        for synonym in tempList1:
            for word in keywords:
                if (synonym==word):
                    synonymsFoundTemp.append(word.replace('_',' '))
        synonymsFoundTemp=list(set(synonymsFoundTemp))

        synonyms[starting_keyword.replace('_',' ')]=synonymsFoundTemp

    return synonyms 


def create_skos_dictionary(synonyms, video_id:str, mode:str, language:str):
    """
    Create SKOS dictionary from a dict with synonyms.

    Creates an RDF graph with SKOS vocabulary structure from a dictionary
    of words and their synonyms.

    Parameters
    ----------
    synonyms : dict
        Dictionary with words as keys and lists of synonyms as values
    video_id : str
        Identifier for the video
    mode : str
        Mode of operation for the annotator
    language : str
        Language code for the labels

    Returns
    -------
    dict
        JSON-LD representation of the SKOS dictionary

    Notes
    -----
    The output follows the W3C Web Annotation Data Model context
    and includes custom Edurell namespace references
    """
    print("***** EKEEL - Video Annotation: synonyms.py::create_skos_dictionary(): Inizio ******")
    
    graph = Graph()
    skos = Namespace('http://www.w3.org/2004/02/skos/core#')
    graph.bind('skos', skos)
    uri_edurell = 'https://teldh.github.io/edurell#'

    for concept in synonyms.keys():
        
        uri_concept = URIRef("concept_" + concept.replace(" ", "_"))
        graph.add((uri_concept, RDF['type'], skos['Concept']))
        graph.add((uri_concept, skos['prefLabel'], Literal(concept, lang=language)))
        for synonym in synonyms[concept]:
            graph.add((uri_concept, skos['altLabel'], Literal(synonym, lang=language)))

    # Save graph in file
    #graph.serialize(destination='output.txt', format='json-ld')
    #print graph.serialize(format='json-ld').decode('utf-8')

    context = ["http://www.w3.org/ns/anno.jsonld", 
        {"edu": uri_edurell, 
        "@base": "https://edurell.dibris.unige.it/annotator/"+mode+"/"+video_id+"/", "@version": 1.1}]        

    jsonld = json.loads(graph.serialize(format='json-ld'))
    jsonld = pyld.jsonld.compact(jsonld, context)

    if '@graph' not in jsonld:
        node = {}
        for key in list(jsonld.keys()):
            if key != "@context":
                node[key] = jsonld.pop(key)
        jsonld["@graph"] = [node] if len(node.keys()) > 1 else []

    print("***** EKEEL - Video Annotation: synonyms.py::create_skos_dictionary(): Fine ******")

    return jsonld

