"""
Handle data module for the Flask server.

This module provides functions to interact with the MongoDB database and retrieve data related to video annotations.

Functions
---------
get_graphs(video_id)
    Retrieves all graphs associated with the given video ID.
check_graphs(video_id, email)
    Checks if there are any graphs associated with the given video ID and email.
get_definitions_fragments(email, video_id, fragments)
    Retrieves definitions for the specified email, video ID, and fragments.
"""
from rdflib import Namespace


import data

oa = Namespace("http://www.w3.org/ns/oa#")
dctypes = Namespace("http://purl.org/dc/dcmitype/")
dcterms = Namespace("http://purl.org/dc/terms/")
edu = Namespace("http://edurell.com/")
skos = Namespace("http://www.w3.org/2004/02/skos#")


def get_graphs(video_id):
    """
    Retrieves all graphs associated with the given video ID.

    Parameters
    ----------
    video_id : str
        The ID of the video.

    Returns
    -------
    list
        A list of dictionaries containing annotator ID and video ID.
    """
    db = data.load_db()
    collection = db.graphs
    q = collection.find({"video_id":video_id})
    res = []
    for graph in q:
        res.append({"annotator_id": graph["annotator_id"], "video_id": video_id})
    return res


# check if exist video annotated by user (email)
def check_graphs(video_id, email):
    """
    Checks if there are any graphs associated with the given video ID and email.

    Parameters
    ----------
    video_id : str
        The ID of the video.
    email : str
        The email address associated with the graphs.

    Returns
    -------
    list
        A list of dictionaries containing annotator ID and video ID.
    """
    db = data.load_db()
    collection = db.graphs
    q = collection.find({"video_id":video_id,"email":email})
    res = []
    for graph in q:
        res.append({"annotator_id": graph["annotator_id"], "video_id": video_id})
    return res


def get_definitions_fragments(email, video_id, fragments):
    """
    Retrieves definitions for the specified email, video ID, and fragments.

    Parameters
    ----------
    email : str
        The email address associated with the definitions.
    video_id : str
        The ID of the video.
    fragments : list
        A list of fragments with start and end times.

    Returns
    -------
    list
        A list of definitions for the specified fragments.
    """
    db = data.load_db()
    collection = db.graphs
    print(email, video_id)
    defs = []

    

    pipeline = [
        {"$unwind": "$graph.@graph"},
        {
            "$match":
                {
                    "video_id": str(video_id),
                    "email": str(email),
                    "graph.@graph.type": "oa:annotation",
                    "graph.@graph.motivation": "describing",
                    "graph.@graph.skos:note": "Definition",
                    

                }

        },

        {"$project":
            {
                "concept": "$graph.@graph.body",
                "start": "$graph.@graph.target.selector.startSelector.value",
                "end": "$graph.@graph.target.selector.endSelector.value",
                "_id": 0
            }
        },

        {"$sort": {"start": 1}}

    ]

    aggregation = collection.aggregate(pipeline)
    definitions = list(aggregation)

    

    for d in definitions:
        d["concept"] = d["concept"].replace("edu:", "").replace("_", " ") 
        d["end"] = d["end"].replace("^^xsd:dateTime","")
        d["start"] = d["start"].replace("^^xsd:dateTime", "")

    

    if fragments is not None:
        for f in fragments:

            start_time = f['start']
            end_time = f['end']

            concepts = ""
            added = []

            for d in definitions:   
                if d["start"] < end_time and d["start"] > start_time and d["concept"] not in added:
                    concepts += d["concept"] + ","
                    added.append(d["concept"])
            
            
            defs.append(concepts[0:-1])


    return defs





