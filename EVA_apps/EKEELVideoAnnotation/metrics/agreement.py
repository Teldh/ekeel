"""
Agreement metrics module for concept maps.

This module provides functionality for computing various agreement metrics
between annotators and creating gold standard annotations from multiple
annotators' inputs.

Functions
---------
create_gold
    Creates gold standard from multiple annotators
createAllComb
    Generates all possible concept pairs
createUserRel
    Creates user relationship pairs from annotations
check_trans
    Checks for transitive relationships
creaCoppieAnnot
    Creates annotation pairs and counts agreements
computeK
    Computes kappa coefficient
computeFleiss
    Computes Fleiss' kappa for multiple raters
computeKappaFleiss
    Helper function for Fleiss' kappa computation
checkEachLineCount
    Validates rating consistency across lines
"""

import networkx
from text_processor.synonyms import create_skos_dictionary
import database.mongo as mongo
from ontology.rdf_graph import annotations_to_jsonLD



def create_gold(video, annotators, combination_criteria, name):
    """
    Create gold standard annotations from multiple annotators.

    Parameters
    ----------
    video : str
        Video identifier
    annotators : list
        List of annotator identifiers
    combination_criteria : str
        Criteria for combining annotations ('union' supported)
    name : str
        Name for the gold standard

    Returns
    -------
    None
        Stores results in database
    """
    # Function to merge dictionaries
    def mergeDictionary(d1, d2):
       d3 = {**d1, **d2}
       for key in d3.keys():
           if key in d1 and key in d2:
                d3[key] = list(set(d3[key]+d1[key]))
       return d3

    relations = []
    definitions = []
    conceptVocabulary = {}
    if combination_criteria == "union":
        for annotator in annotators:
            relations += mongo.get_concept_map(annotator, video)
            definitions += mongo.get_definitions(annotator, video)
            #db_conceptVocabulary = db_mongo.get_vocabulary(annotator, video) take from db
            db_conceptVocabulary = None # to start empty
            if(db_conceptVocabulary != None):
                conceptVocabulary = mergeDictionary(conceptVocabulary, db_conceptVocabulary)

        # If the concept vocabulary is new (empty) then initialize it to empty synonyms
        if(conceptVocabulary == {}) :
            for i in mongo.get_concepts(annotators[0], video):
                conceptVocabulary[i] = []

        annotations = {"relations":relations, "definitions":definitions, "id":video}
        _, jsonld = annotations_to_jsonLD(annotations, isAutomatic=True)

        data = jsonld.copy()
        data["video_id"] = video
        data["graph_type"] = "gold standard"
        data["gold_name"] = name
        data["conceptVocabulary"] = create_skos_dictionary(conceptVocabulary, video,"auto")

        mongo.insert_gold(data)


    print(relations)


def createAllComb(words):
    """
    Create all possible concept pairs from word list.

    Parameters
    ----------
    words : list
        List of concepts/words

    Returns
    -------
    list
        All possible unique concept pairs
    """
    #creo tutte le possibili coppie di concetti
    all_combs=[]
    for term in words:
        for i in range(len(words)):
            if term != words[i]:
                combination = term+"/-/"+words[i]
                combination_inv = words[i]+"/-/"+term
                if combination_inv not in all_combs:
                    all_combs.append(combination)
    return all_combs


def createUserRel(file, all_combs):
    """
    Create user relationship pairs from annotations.

    Parameters
    ----------
    file : list
        List of annotation relationships
    all_combs : list
        List of all possible combinations

    Returns
    -------
    tuple
        (relationships, updated combinations, relationship tuples)
    """
    temp = []
    term_pairs_tuple = []
    for annot_pairs in file:
        concept_pair=annot_pairs["prerequisite"]+"/-/"+annot_pairs["target"]
        if(concept_pair not in all_combs):
            all_combs.append(concept_pair)
        temp.append(concept_pair)

        tupla = (annot_pairs["prerequisite"], annot_pairs["target"])
        term_pairs_tuple.append(tupla)


    return temp, all_combs, term_pairs_tuple


def check_trans(rater, term_pairs_tuple, pair):
    """
    Check for transitive relationships in annotations.

    Parameters
    ----------
    rater : str
        Rater identifier
    term_pairs_tuple : dict
        Dictionary of term pairs by rater
    pair : str
        Concept pair to check

    Returns
    -------
    bool
        True if transitive relationship exists
    """
    # print(pair)
    # print(rater2)
    g = networkx.DiGraph(term_pairs_tuple[rater])
    if pair.split("/-/")[0] in g and pair.split("/-/")[1] in g:
        if networkx.has_path(g, source=pair.split("/-/")[0], target=pair.split("/-/")[1]):
            return True
    else:
        return False


def creaCoppieAnnot(rater1, rater2, term_pairs, pairs, term_pairs_tuple):
    """
    Create annotation pairs and compute agreement counts.

    Parameters
    ----------
    rater1 : str
        First rater identifier
    rater2 : str
        Second rater identifier
    term_pairs : dict
        Dictionary of term pairs by rater
    pairs : list
        List of all possible pairs
    term_pairs_tuple : dict
        Dictionary of term pair tuples

    Returns
    -------
    tuple
        (annotation pairs, agreement counts)
    """
    coppieannot = {}
    conteggio = {"1,1": 0, "1,0": 0, "0,1": 0, "0,0": 0}
    for pair in pairs:
        # per ogni concept pair controllo fra le coppie E i paths di r1
        if pair in term_pairs[rater1] or check_trans(rater1, term_pairs_tuple, pair):
            # se presente, controllo fra coppie e paths di r2 e incremento i contatori
            if pair in term_pairs[rater2] or check_trans(rater2, term_pairs_tuple, pair):
                coppieannot[pair] = "1,1"
                conteggio["1,1"] += 2  # inv_pt1: scelgo di considerare le coppie inverse come both agree
                conteggio["0,0"] -= 1  # inv_pt2: compenso la scelta di tenenre conto le inverse in both agree
            # conteggio["1,1"]+=1 #no_inv: le coppie inverse valgolo come both diagree
            else:
                coppieannot[pair] = "1,0"
                conteggio["1,0"] += 1
        # altrimenti, se manca coppia e percorso in r1 e r2 o solo in r1, incrementa questi contatori
        elif pair not in term_pairs[rater1]:
            if pair not in term_pairs[rater2] and not check_trans(rater2, term_pairs_tuple, pair):
                coppieannot[pair] = "0,0"
                conteggio["0,0"] += 1
            else:
                coppieannot[pair] = "0,1"
                conteggio["0,1"] += 1
    return coppieannot, conteggio



def computeK(conteggio, pairs):
    """
    Compute kappa coefficient for inter-rater agreement.

    Parameters
    ----------
    conteggio : dict
        Agreement counts dictionary
    pairs : list
        List of all possible pairs

    Returns
    -------
    float
        Kappa coefficient
    """
    Po = (conteggio["1,1"] + conteggio["0,0"]) / float(len(pairs))
    Pe1 = ((conteggio["1,1"] + conteggio["1,0"]) / float(len(pairs))) * (
                (conteggio["1,1"] + conteggio["0,1"]) / float(len(pairs)))
    Pe2 = ((conteggio["0,1"] + conteggio["0,0"]) / float(len(pairs))) * (
                (conteggio["1,0"] + conteggio["0,0"]) / float(len(pairs)))
    Pe = Pe1 + Pe2
    k = (Po - Pe) / float(1 - Pe)
    return k




def computeFleiss(term_pairs, all_combs):
    """
    Compute Fleiss' kappa for multiple raters.

    Parameters
    ----------
    term_pairs : dict
        Dictionary of term pairs by rater
    all_combs : list
        List of all possible combinations

    Returns
    -------
    float
        Fleiss' kappa coefficient
    """
    matrix_fleiss = []

    for item in all_combs:

        countZero = 0
        countOne = 0
        for rater, values in term_pairs.items():
            lista = []
            if item not in values:
                countZero = countZero + 1
            if item in values:
                countOne = countOne + 1
        lista.insert(0, countZero)
        lista.insert(1, countOne)
        matrix_fleiss.append(lista)

    return computeKappaFleiss(matrix_fleiss)



def computeKappaFleiss(mat):
    """
    Compute Fleiss' kappa from rating matrix.

    Parameters
    ----------
    mat : list
        Matrix of ratings [subjects][categories]

    Returns
    -------
    float
        Fleiss' kappa coefficient
    """
    """ Computes the Kappa value
        @param n Number of rating per subjects (number of human raters)
        @param mat Matrix[subjects][categories]
        @return The Kappa value """
    print(mat)
    n = checkEachLineCount(mat)  # PRE : every line count must be equal to n
    print(n)
    N = len(mat)
    k = len(mat[0])

    # Computing p[] (accordo sugli 0 e accordo sugli 1)
    p = [0.0] * k
    for j in range(k):
        p[j] = 0.0
        for i in range(N):
            p[j] += mat[i][j]
        p[j] /= N * n

    # Computing P[]  (accordo su ogni singola coppia di concetti)
    P = [0.0] * N
    for i in range(N):
        P[i] = 0.0
        for j in range(k):
            P[i] += mat[i][j] * mat[i][j]
        P[i] = (P[i] - n) / (n * (n - 1))

    # Computing Pbar (accordo osservato)
    Pbar = sum(P) / N

    # Computing PbarE (accordo dovuto al caso)
    PbarE = 0.0
    for pj in p:
        PbarE += pj * pj

    kappa = (Pbar - PbarE) / (1 - PbarE)

    return kappa




def checkEachLineCount(mat):
    """
    Check that each line has same number of ratings.

    Parameters
    ----------
    mat : list
        Matrix of ratings to check

    Returns
    -------
    int
        Number of ratings per line

    Raises
    ------
    AssertionError
        If lines have different rating counts
    """
    """ Assert that each line has a constant number of ratings
        @param mat The matrix checked
        @return The number of ratings
        @throws AssertionError If lines contain different number of ratings """
    n = sum(mat[0])


    assert all(sum(line) == n for line in mat[1:]), "Line count != %d (n value)." % n

    return n