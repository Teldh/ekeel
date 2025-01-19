"""
Data handling module for the Flask server.

This module provides functions to interact with the MongoDB database, retrieve and process data related to video annotations and concepts.

Functions
---------
load_db()
    Connects to the MongoDB database and returns the database object.
delete_graphs(email)
    Deletes all graph documents associated with the given email.
get_conll(video_id)
    Retrieves the CoNLL data for the specified video ID.
get_sentences(parsed_conll, start_id, end_id)
    Extracts sentences from the parsed CoNLL data between the specified start and end IDs.
format_datetime(str)
    Formats a datetime string by removing the type annotation.
get_concept_list(annotator, video_id)
    Retrieves a list of concepts for the specified annotator and video ID.
get_concept_map(annotator, video_id)
    Retrieves a concept map for the specified annotator and video ID.
get_concept_vocabulary(annotator, video_id)
    Retrieves the concept vocabulary for the specified annotator and video ID.
get_concept_instants(annotator, video_id)
    Retrieves concept instants for the specified annotator and video ID.
get_concept_targets(concept_map, concept_id)
    Retrieves the target concepts for the specified concept ID.
get_concept_prerequisites(concept_map, concept_id)
    Retrieves the prerequisite concepts for the specified concept ID.
build_concept_without_sub_graph(concept_instants, concept_id)
    Builds a concept object without subgraph information.
build_concept_sub_graph_without_target_recursively(concept_map, concept_instants, concept_id)
    Builds a subgraph for a concept recursively without target information.
build_concept_sub_graph(concept_map, concept_instants, concept_id)
    Builds a subgraph for a concept including target information.
retrieve_primary_notions(concept_instance)
    Retrieves primary notions from a concept instance.
build_array(annotator, video_id)
    Builds an array of concepts for the specified annotator and video ID.
"""
import pymongo


from conllu import parse
from environment import MONGO_CLUSTER_USERNAME,MONGO_CLUSTER_PASSWORD

def load_db():
    """
    Connects to the MongoDB database and returns the database object.

    Returns
    -------
    db : pymongo.database.Database
        The MongoDB database object.
    """
    client = pymongo.MongoClient("mongodb+srv://"+MONGO_CLUSTER_USERNAME+":"+MONGO_CLUSTER_PASSWORD+"@clusteredurell.z8aeh.mongodb.net/edurell?retryWrites=true&w=majority")
    db = client.edurell
    return db

db = load_db()


def delete_graphs(email):
    """
    Deletes all graph documents associated with the given email.

    Parameters
    ----------
    email : str
        The email address associated with the graph documents to delete.

    Returns
    -------
    pymongo.results.DeleteResult
        The result of the delete operation.
    """
    collection = db.graphs
    if collection.find({"email":email}) is not None:
        return collection.delete_many({"email":email})

def get_conll(video_id):
    """
    Retrieves the CoNLL data for the specified video ID.

    Parameters
    ----------
    video_id : str
        The ID of the video.

    Returns
    -------
    str or None
        The CoNLL data if found, otherwise None.
    """
    collection = db.conlls
    if collection.find_one({"video_id":video_id}) is not None:
        return collection.find_one({"video_id":video_id})["conll"]
    else:
        return None
    
    
def get_sentences(parsed_conll,start_id,end_id):
    """
    Extracts sentences from the parsed CoNLL data between the specified start and end IDs.

    Parameters
    ----------
    parsed_conll : list
        The parsed CoNLL data.
    start_id : int
        The starting sentence ID.
    end_id : int
        The ending sentence ID.

    Returns
    -------
    str
        The extracted sentences.
    """
    sentences = ""
    start_id = int(start_id)
    end_id = int(end_id)
    # print(start_id)
    # print(end_id)
    for i in range(start_id, end_id):
        for k in range(0,len(parsed_conll[i])):
            sentences += parsed_conll[i][k]["lemma"] +" "
    return sentences


def format_datetime(str):
    """
    Formats a datetime string by removing the type annotation.

    Parameters
    ----------
    str : str
        The datetime string to format.

    Returns
    -------
    str
        The formatted datetime string.
    """
    s = str.split("^^")
    return s[0]


def get_concept_list(annotator, video_id):
    """
    Retrieves a list of concepts for the specified annotator and video ID.

    Parameters
    ----------
    annotator : str
        The ID of the annotator.
    video_id : str
        The ID of the video.

    Returns
    -------
    list
        A list of concepts.
    """
    collection = db.graphs
    pipeline = [
        {"$unwind": "$graph.@graph"},
        {
            "$match":
                {
                    "video_id": str(video_id),
                    "annotator_id": str(annotator),
                    "graph.@graph.type": "skos:Concept",
                }

        },

        {"$project":
            {
                "id": "$graph.@graph.id",
                "name": "$graph.@graph.id"
            }
        },

        {"$sort": {"time": 1}}

    ]

    aggregation = collection.aggregate(pipeline)
    concept_list = list(aggregation)
    for c in concept_list:
        c["id"] = c["id"].replace("edu:","").replace("_"," ")

    #get_concept_vocabulary(annotator, video_id)
    
    return concept_list


def get_concept_map(annotator,video_id):
    """
    Retrieves a concept map for the specified annotator and video ID.

    Parameters
    ----------
    annotator : str
        The ID of the annotator.
    video_id : str
        The ID of the video.

    Returns
    -------
    list
        A list representing the concept map.
    """
    collection = db.graphs

    pipeline = [
       {"$unwind": "$graph.@graph"},
       {
           "$match":
               {
                   "video_id": str(video_id),
                   "annotator_id": str(annotator),
                   "graph.@graph.type": "oa:annotation",
                   "graph.@graph.motivation": "edu:linkingPrerequisite",
               }
       },

        {"$project":
            {
                "prerequisite": "$graph.@graph.body",
                "target": "$graph.@graph.target.dcterms:subject.id",
                "weight": "$graph.@graph.skos:note",
                "time": "$graph.@graph.target.selector.value",
                "sent_id": "$graph.@graph.target.selector.edu:conllSentId",
                "word_id": "$graph.@graph.target.selector.edu:conllWordId",
                "xywh": "$graph.@graph.target.selector.edu:hasMediaFrag",
                "creator": "$graph.@graph.dcterms:creator",
                "_id": 0
            }
        },
    
        {"$sort": {"time": 1}}

    ]

    aggregation = collection.aggregate(pipeline)
    concept_map = list(aggregation)

    for rel in concept_map:
        rel["prerequisite"] = rel["prerequisite"].replace("edu:","").replace("_"," ")
        rel["target"] = rel["target"].replace("edu:","").replace("_"," ")
        rel["weight"] = rel["weight"].replace("Prerequisite","")
        rel["time"] = rel["time"].replace("^^xsd:dateTime","")
        if "xywh" not in rel:
            rel["xywh"] = "None"

    return concept_map


def get_concept_vocabulary(annotator, video_id):
    """
    Retrieves the concept vocabulary for the specified annotator and video ID.

    Parameters
    ----------
    annotator : str
        The ID of the annotator.
    video_id : str
        The ID of the video.

    Returns
    -------
    dict or None
        A dictionary representing the concept vocabulary, or None if not found.
    """
    collection = db.graphs

    pipeline = [
        {"$unwind": "$conceptVocabulary.@graph"},
        {
            "$match":
                {
                    "video_id": str(video_id),
                    "annotator_id": str(annotator),
                    "conceptVocabulary.@graph.type": "skos:Concept"
                }
        },

        {"$project":
            {
                "prefLabel": "$conceptVocabulary.@graph.skos:prefLabel.@value",
                "altLabel": "$conceptVocabulary.@graph.skos:altLabel.@value",
                "_id": 0
            }
        }

    ]

    aggregation = collection.aggregate(pipeline)
    results = list(aggregation)

    # define new concept vocabulary
    conceptVocabulary = {}

    # if there is none on DB
    if len(results) == 0:
        print(conceptVocabulary)
        return None

    # iterate for each concept and build the vocabulary basing on the number of synonyms
    for concept in results: 
 
        if "altLabel" in concept :
            if isinstance(concept["altLabel"], list):
                conceptVocabulary[concept["prefLabel"]] = concept["altLabel"]
            else:
                conceptVocabulary[concept["prefLabel"]] = [concept["altLabel"]]
        else:
            conceptVocabulary[concept["prefLabel"]]=[]

    #print(conceptVocabulary)

    return conceptVocabulary



def get_concept_instants(annotator, video_id):
    """
    Retrieves concept instants for the specified annotator and video ID.

    Parameters
    ----------
    annotator : str
        The ID of the annotator.
    video_id : str
        The ID of the video.

    Returns
    -------
    list
        A list of concept instants.
    """
    pipeline = [
        {"$unwind": "$graph.@graph"},
        {
            "$match":
                {
                    "video_id": str(video_id),
                    "annotator_id": str(annotator),
                    "graph.@graph.type": "oa:annotation",
                    "graph.@graph.motivation": "describing",
                }

        },

        {"$project":
            {
                "concept_id": "$graph.@graph.body",
                "start_time":"$graph.@graph.target.selector.startSelector.value",
                "end_time": "$graph.@graph.target.selector.endSelector.value",
                "start_sent_id": "$graph.@graph.target.selector.startSelector.edu:conllSentId",
                "end_sent_id":  "$graph.@graph.target.selector.endSelector.edu:conllSentId",
            }
        },


        {"$sort": {"time": 1}}]

    collection = db.graphs
    aggregation = collection.aggregate(pipeline)
    concept_instants = list(aggregation)
    for c in concept_instants:
        c["start_time"] = format_datetime(c["start_time"])
        c["end_time"] = format_datetime(c["end_time"])
        c["concept_id"] = c["concept_id"].replace("edu:","").replace("_"," ")
    return concept_instants
   
   
def get_concept_targets(concept_map, concept_id):
    """
    Retrieves the target concepts for the specified concept ID.

    Parameters
    ----------
    concept_map : list
        The concept map.
    concept_id : str
        The ID of the concept.

    Returns
    -------
    list
        A list of target concepts.
    """
    targets = []
    for relation in concept_map:
        if relation["prerequisite"] == concept_id:
            targets.append(relation["target"])
    return targets


def get_concept_prerequisites(concept_map, concept_id):
    """
    Retrieves the prerequisite concepts for the specified concept ID.

    Parameters
    ----------
    concept_map : list
        The concept map.
    concept_id : str
        The ID of the concept.

    Returns
    -------
    list
        A list of prerequisite concepts.
    """
    prerequisites = []
    for relation in concept_map:
        if relation["target"] == concept_id:
            prerequisites.append(relation["prerequisite"])
    return prerequisites


def build_concept_without_sub_graph(concept_instants,concept_id):
    """
    Builds a concept object without subgraph information.

    Parameters
    ----------
    concept_instants : list
        The list of concept instants.
    concept_id : str
        The ID of the concept.

    Returns
    -------
    dict
        A dictionary representing the concept.
    """
    concept = {"conceptName": "", 
                        "type": "", 
                        "description": "", 
                        "startTimestamp": "",
                        "endTimestamp": "",
                        "image": "",
                        "subgraph": []}
    concept["conceptName"] = concept_id

    for c in concept_instants:
        if c["concept_id"] == concept_id:
            concept["startTimestamp"] = c["start_time"]
            concept["endTimestamp"] = c["end_time"]
    return concept


def build_concept_sub_graph_without_target_recursively(concept_map, concept_instants, concept_id):
    """
    Builds a subgraph for a concept recursively without target information.

    Parameters
    ----------
    concept_map : list
        The concept map.
    concept_instants : list
        The list of concept instants.
    concept_id : str
        The ID of the concept.

    Returns
    -------
    dict
        A dictionary representing the subgraph.
    """
    sub_graph = {"targets": [], "prerequisites": [], "primary_notions": []}
    prerequisites = get_concept_prerequisites(concept_map, concept_id)
    prerequisites_concept = []
    for c in prerequisites:
        concept = build_concept_without_sub_graph(concept_instants, c)
        if concept not in prerequisites_concept:
            prerequisites_concept.append(concept)
    sub_graph["prerequisites"] = prerequisites_concept
    for c in sub_graph["prerequisites"]:
        c["subgraph"] =  build_concept_sub_graph_without_target_recursively(concept_map,concept_instants, c["conceptName"])
    return sub_graph


def build_concept_sub_graph(concept_map, concept_instants, concept_id):
    """
    Builds a subgraph for a concept including target information.

    Parameters
    ----------
    concept_map : list
        The concept map.
    concept_instants : list
        The list of concept instants.
    concept_id : str
        The ID of the concept.

    Returns
    -------
    dict
        A dictionary representing the subgraph.
    """
    sub_graph = {"targets": [], "prerequisites": [], "primary_notions": [] }
    primary_targets = get_concept_targets(concept_map, concept_id)
    for c in primary_targets:
        sub_graph["targets"].append(build_concept_without_sub_graph(concept_instants, c))

    prerequisites = get_concept_prerequisites(concept_map, concept_id)
    prerequisites_concept = []
    for c in prerequisites:
        c = build_concept_without_sub_graph(concept_instants, c)
        prerequisites_concept.append(c)
    sub_graph["prerequisites"] = prerequisites_concept
    for concept in sub_graph["prerequisites"]:
        concept["subgraph"] = build_concept_sub_graph_without_target_recursively(concept_map,concept_instants, c["conceptName"])

    sub_graph["relations"] = concept_map
    return sub_graph

def retrieve_primary_notions(concept_instance):
    """
    Retrieves primary notions from a concept instance.

    Parameters
    ----------
    concept_instance : dict
        The concept instance.

    Returns
    -------
    list
        A list of primary notions.
    """
    primary_notions = []
    for c in concept_instance["subgraph"]["prerequisites"]:
        if c["subgraph"]["prerequisites"] == []:
            primary_notions.append(c)
        else:
            primary_notions = primary_notions + retrieve_primary_notions(c)
    return primary_notions

def build_array(annotator,video_id):
    """
    Builds an array of concepts for the specified annotator and video ID.

    Parameters
    ----------
    annotator : str
        The ID of the annotator.
    video_id : str
        The ID of the video.

    Returns
    -------
    list
        A list of concepts.
    """
    concept_map = get_concept_map(annotator,video_id)
    concept_instants = get_concept_instants(annotator,video_id)
    primary_concept_list = get_concept_list(annotator,video_id)
    parsed_conll = parse(get_conll(video_id))
    conceptsList = []
    for c in primary_concept_list:
        conceptsList.append(build_concept_without_sub_graph(concept_instants,c["id"]))
    for c in conceptsList:
        c["subgraph"] =  build_concept_sub_graph(concept_map, concept_instants, c["conceptName"])
        c["subgraph"]["primary_notions"] = retrieve_primary_notions(c)
        for c_i in concept_instants:
            if c_i["concept_id"] == c["conceptName"]:
                c["description"] = get_sentences(parsed_conll, c_i["start_sent_id"], c_i["end_sent_id"])

    return conceptsList



"""concept_map = get_concept_map('60659634a320492e72f72598','sXLhYStO0m8')
concept_instants = get_concept_instants('60659634a320492e72f72598','sXLhYStO0m8')
concept = build_concept_without_sub_graph(concept_instants,'sciatic notch")
concept["subgraph"] = build_concept_sub_graph(concept_map, concept_instants, "sciatic notch")
concept["subgraph"]["primary_notions"] = retrieve_primary_notions(concept)

print(build_array('60659634a320492e72f72598','sXLhYStO0m8'))
"""
conll = get_conll("sXLhYStO0m8")
conll = parse(conll)
sentences = get_sentences(conll,50,60)
# print(sentences)