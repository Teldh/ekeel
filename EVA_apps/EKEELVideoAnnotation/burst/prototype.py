"""
Burst analysis module for concept mapping.

This module provides functionality for detecting bursts of concepts in video 
transcripts and creating semantic relationships between them.
"""

import pandas as pd
from rdflib import Graph, URIRef, RDF, BNode, ConjunctiveGraph, Namespace
from rdflib.namespace import SKOS, XSD
from rdflib.term import Literal
from rdflib.serializer import Serializer
import sys
import copy
from conllu import parse
from nltk import tokenize
import time
import datetime
from nltk import WordNetLemmatizer
from numpy import delete
import json
import pyld

from burst.extractor import BurstExtractor
from burst.weight import WeightAssigner, WeightsNormalizer
import burst.results_processor as burst_proc
from text_processor.conll import get_text
from database.mongo import get_conll
import metrics.agreement as agreement
from media.segmentation import get_timed_sentences, VideoAnalyzer
from utils.itertools import double_iterator
from database.mongo import get_video_data
from media.segmentation import SemanticText

oa = Namespace("http://www.w3.org/ns/oa#")
dc = Namespace("http://purl.org/dc/elements/1.1/")
dctypes = Namespace("http://purl.org/dc/dcmitype/")
dcterms = Namespace("http://purl.org/dc/terms/")
edu = Namespace("https://teldh.github.io/edurell#")

data = {}
videoid = ""


edurell = "https://teldh.github.io/edurell#"

def burst_extraction(video_id, concepts, n=90):
    """
    Extract burst patterns from video transcripts.

    Parameters
    ----------
    video_id : str
        Identifier for the video to analyze
    concepts : list
        List of concepts to detect bursts for
    n : int, optional
        Number of top bursts to consider

    Returns
    -------
    tuple
        (concept_map_burst, burst_definitions) containing burst analysis results
    """
    print("***** EKEEL - Video Annotation: burst_class.py::burst_extraction(): Inizio ******")

    text, conll = get_text(video_id, return_conll=True)
    text = text.replace("-", " ")


    concept_map_burst, burst_definitions = Burst(text, concepts, video_id, conll, threshold=0.7,
                                                 top_n=n, max_gap=1).launch_burst_analysis()

    return concept_map_burst, burst_definitions

def get_synonyms_mappings(conceptVocabulary:list):
    """
    Create mappings between concepts and their synonyms.

    Parameters
    ----------
    conceptVocabulary : dict
        Dictionary mapping concepts to their synonyms

    Returns
    -------
    tuple
        (syn_map, new_concepts) containing synonym mappings and unique concepts
    """
    print("***** EKEEL - Video Annotation: burst_class.py::get_synonyms_mappings(): Inizio ******")
    
    syn_map = {}
    new_concepts = []

    # get unique id for each syn set
    for concept in conceptVocabulary:
        synset = [concept]
        synset = synset + conceptVocabulary[concept]
        synset.sort()
        syn_map[concept] = synset[0]
        new_concepts.append(synset[0])

    new_concepts = list(set(new_concepts))
    
    print("***** EKEEL - Video Annotation: burst_class.py::get_synonyms_mappings(): Fine ******")
    return syn_map, new_concepts

def burst_extraction_with_synonyms(video_id:str, concepts, conceptVocabulary, n=90):
    """
    Extracts burst patterns from video transcripts considering concept synonyms.
    
    This function extends burst_extraction by incorporating synonym relationships
    between concepts when analyzing the video transcript.

    :param video_id: Identifier for the video to analyze
    :type video_id: str
    :param concepts: List of concepts to detect bursts for
    :type concepts: list
    :param conceptVocabulary: Dictionary mapping concepts to their synonyms
    :type conceptVocabulary: dict
    :param n: Number of top bursts to consider, defaults to 90
    :type n: int, optional
    
    :return: Tuple containing concept map bursts and burst definitions
    :rtype: tuple(dict, dict)
    """
    print("***** EKEEL - Video Annotation: burst_class.py::burst_extraction_with_synonyms(): Inizio ******")

    text, conll = get_text(video_id, return_conll=True)
    text = text.replace("-", " ")

    syn_map, new_concepts = get_synonyms_mappings(conceptVocabulary)

    concept_map_burst, burst_definitions = Burst(text, new_concepts, video_id, conll, syn_map, threshold=0.7,
                                                 top_n=n, max_gap=1).launch_burst_analysis()

    print("***** EKEEL - Video Annotation: burst_class.py::burst_extraction_with_synonyms(): Fine ******")
    return concept_map_burst, burst_definitions

class Burst:
    """
    Burst analysis for video concept mapping.

    This class implements burst detection and relationship mapping between
    concepts in video transcripts using Kleinberg's algorithm.

    Attributes
    ----------
    text : str
        Input text to analyze
    words : list
        Words to detect bursts for
    conll : list
        CoNLL-U formatted text
    video_id : str
        Video identifier
    threshold : float
        Burst detection threshold
    top_n : int or None
        Number of top bursts to consider
    S : float
        Base of exponential distribution
    GAMMA : float
        Cost coefficient between states
    LEVEL : int
        Burst level threshold
    ALLEN_WEIGHTS : dict
        Weights for Allen relations
    USE_INVERSES : bool
        Whether to use inverse relations
    MAX_GAP : int
        Maximum gap between bursts
    NORM_FORMULA : str
        Formula for normalization
    occurrences : pandas.DataFrame
        Word occurrence positions
    first_occurence : dict
        First occurrence position of each word

    Methods
    -------
    launch_burst_analysis()
        Run complete burst analysis pipeline
    df_to_data(sorted_edgelist, burst_res, use_conll)  
        Convert analysis results to concept maps
    _merge_contained_definitions(definitions)
        Merge overlapping concept definitions
    """

    def __init__(self, text, words, video_id, conll, syn_map=False, threshold=0, 
                 top_n=None, s=1.05, gamma=0.0001, level=1, allen_weights=None,
                 use_inverses=False, max_gap=4, norm_formula="modified"):
        """
        Initialize burst analyzer.

        Parameters
        ----------
        text : str
            Text to analyze
        words : list
            Words to detect bursts for
        video_id : str
            Video identifier
        conll : str
            CoNLL-U formatted text
        syn_map : dict or bool, optional
            Synonym mapping dictionary
        threshold : float, optional
            Burst detection threshold
        top_n : int, optional
            Number of top bursts to consider
        s : float, optional
            Base of exponential distribution
        gamma : float, optional  
            Cost coefficient between states
        level : int, optional
            Burst level threshold
        allen_weights : dict, optional
            Custom weights for Allen relations
        use_inverses : bool, optional
            Whether to use inverse relations
        max_gap : int, optional
            Maximum gap between bursts
        norm_formula : str, optional
            Formula for normalization
        """
        self.text = text
        self.words = words

        self.conll = parse(conll)
        self.video_id = video_id
        self.threshold = threshold
        self.top_n = top_n
        self.data = {}


        #Kleinberg's parameters
        self.S = s
        self.GAMMA = gamma
        self.LEVEL = level

        # #self.occurences
        # #Dataframe contentente le colonne "Lemma", "idFrase", "idParolaStart"
        occurrences_index = []
        self.first_occurence = {}

        # PHASE 0
        
        max_word_lenght = 0

        for w in self.words:
            l = len(w.split(" "))
            if l > max_word_lenght:
                max_word_lenght = l

        upper_words = [x.upper() for x in self.words]
        lemmatizer = WordNetLemmatizer()


        for sent in self.conll:
            sent_index = int(sent.metadata["sent_id"])-1
            conll_words = self.conll[sent_index].filter(upos=lambda x: x != "PUNCT")
            #from pprint import pprint
            #pprint(self.conll)
            counter = 0
            skip = 0

            for i_, word in enumerate(conll_words):
                #print(word, word["id"], conll_words[i_+1],conll_words[i_+1]["id"], conll_words[i_+2],conll_words[i_+2]["id"])
                if isinstance(word["id"], tuple): skip += 2
                elif skip > 0: skip -= 1; continue
                counter += 1
                #word_index = int(word["id"]) # TODO fix
                word_index = counter
                words = word["lemma"]
                words_form = word["form"]
                nltk_lemmatized = lemmatizer.lemmatize(word["form"])

                for i in range(1, max_word_lenght+1):

                    occ_words = ""
                    # cerco occorrenza della parola nella forma base, lemmatizata con la conll e lematizzata con nltk
                    if words.upper() in upper_words:
                        occ_words = words.lower()
                    elif words_form.upper() in upper_words:
                        occ_words = words_form.lower()
                    elif nltk_lemmatized.upper() in upper_words:
                        occ_words = nltk_lemmatized

                    if occ_words != "":
                        if occ_words not in self.first_occurence:
                            self.first_occurence[occ_words] = sent_index

                        d = [occ_words, sent_index, word_index]
                        occurrences_index.append(d)

                    if i + i_ < len(conll_words):
                        words += " " + conll_words[i_ + i]["lemma"]
                        words_form += " " + conll_words[i_ + i]["form"]
                        nltk_lemmatized += " " + lemmatizer.lemmatize(conll_words[i_ + i]["form"])
                    else:
                        break

        
        if syn_map == False:
            self.occurrences = pd.DataFrame(data=occurrences_index, columns=["Lemma", "idFrase", "idParolaStart"])
        else:
            occur = pd.DataFrame(data=occurrences_index, columns=["Lemma", "idFrase", "idParolaStart"])
            new_occur = []
            for o in occur.itertuples(): 
                new_occur.append([syn_map[o.Lemma], o.idFrase, o.idParolaStart])
            self.occurrences = pd.DataFrame(new_occur, columns=['Lemma', 'idFrase', 'idParolaStart'])


        # weights for Allen and type of normalization formula
        if allen_weights is None:
            self.ALLEN_WEIGHTS = {'equals': 2, 'before': 5, 'after': 0, 'meets': 3, 'met-by': 0,
                             'overlaps': 7, 'overlapped-by': 1, 'during': 7, 'includes': 7,
                             'starts': 4, 'started-by': 2, 'finishes': 2, 'finished-by': 8}
        else:
            self.ALLEN_WEIGHTS = allen_weights


        self.USE_INVERSES = use_inverses
        self.MAX_GAP = max_gap
        self.NORM_FORMULA = norm_formula

        # decide if preserve relations when giving direction to the burst matrix
        self.PRESERVE_RELATIONS = True

    def _merge_contained_definitions(self, definitions):
        """
        Merge overlapping concept definitions.

        Parameters
        ----------
        definitions : dict
            Dictionary of concept definitions.

        Returns
        -------
        list
            Merged definitions with overlaps combined.
        """
        def parse_time(stringed_time:str):
            """
            Converts time from string to int
            """
            #            h                    :              mm            :             ss          .            dddddd
            return int(stringed_time[0])*3600 + int(stringed_time[2:4])*60 + int(stringed_time[5:7]) + float("0"+stringed_time[7:])

        to_remove_indexes = []
        for i,j,elem1,elem2 in double_iterator(definitions,enumerated=True):
            if not i in to_remove_indexes \
            and not j in to_remove_indexes \
            and elem1["concept"] == elem2["concept"] \
            and elem1["description_type"] == elem2["description_type"] \
            and parse_time(elem1["start"]) < parse_time(elem2["end"]) \
            and parse_time(elem2["start"]) <= parse_time(elem1["end"]):
                elem1["end"] = elem2["end"]
                elem1["end_sent_id"] = elem2["end_sent_id"]
                to_remove_indexes.append(j)

        return delete(definitions,to_remove_indexes).tolist()
    
    @staticmethod
    def to_edgelist(df):
        """
        Converts a DataFrame to a sorted list of weighted edges.

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame containing adjacency matrix.

        Returns
        -------
        list of tuple
            List of tuples (source, target, weight) sorted by weight descending.

        Examples
        --------
        Example edge list format:
            [(source1, target1, weight1), 
             (source2, target2, weight2),
             ...]
        """
        edges = []
        for i in df.index.tolist():
            for c in df.columns.tolist():
                edges.append((i, c, df.loc[i][c]))

        edges_sorted = sorted(edges, key=lambda edges: edges[2], reverse=True)
        return edges_sorted


    def launch_burst_analysis(self):
        """
        Run complete burst analysis pipeline.

        Executes four main phases:
        1. Burst extraction using Kleinberg's algorithm
        2. Relation detection between bursts
        3. Weight normalization
        4. Directionality assignment

        Returns
        -------
        tuple
            (concept_map, merged_definitions) containing analysis results

        Raises
        ------
        ValueError
            If parameters produce no results
        """
        print("***** EKEEL - Video Annotation: burst_class.py::launch_burst_analysis() ******")
        try:
            # FIRST PHASE: extract bursts
            #print("Extracting bursts...\n")

            #print("text")
            #print(self.text)
            #print("words")
            #print(self.words)
            #print("occurrences")
            #print(self.occurrences[0:50])

            burst_extr = BurstExtractor(text=self.text, wordlist=self.words)
            burst_extr.find_offsets(words=self.words, occ_index_file=self.occurrences)
            burst_extr.generate_bursts(s=self.S, gamma=self.GAMMA)
            burst_extr.filter_bursts(level=self.LEVEL, save_monolevel_keywords=True, replace_original_results=True)
            burst_extr.break_bursts(burst_length=30, num_occurrences=3, replace_original_results=True)
            burst_res = burst_extr.bursts

            if burst_res.empty:
                raise ValueError("The chosen parameters do not produce results")

            # obtain json with first, last, ongoing, unique tags
            # bursts_json = burst_proc.get_json_with_bursts(burst_res, self.occurrences)



            # SECOND PHASE: detect relations between bursts and assign weights to them
            #print("Detecting Allen's relations and assign weights to burst pairs...\n")
            weight_assigner = WeightAssigner(bursts=burst_res,
                                             relations_weights=self.ALLEN_WEIGHTS)
            weight_assigner.detect_relations(max_gap=self.MAX_GAP, alpha=0.05, find_also_inverse=self.USE_INVERSES)
            # output data for the gantt interface and ML projects
            burst_pairs_df = weight_assigner.burst_pairs

            bursts_weights = weight_assigner.bursts_weights


            # THIRD PHASE: normalize the bursts' weights
            #print("Normalizing the matrix with weights of burst pairs...\n")
            weight_norm = WeightsNormalizer(bursts=burst_res,
                                            burst_pairs=burst_pairs_df,
                                            burst_weight_matrix=bursts_weights)
            weight_norm.normalize(formula=self.NORM_FORMULA, occ_index_file=self.occurrences)

            burst_norm = weight_norm.burst_norm.round(decimals=6)


            # FINAL STEP: give directionality to bursts
            #print("Giving directionality to the concept matrix built with bursts...\n")

            directed_burst = burst_proc.give_direction_using_first_burst(undirected_matrix=burst_norm,
                                                                         bursts_results=burst_res,
                                                                         indexes=self.occurrences,
                                                                         level=self.LEVEL, preserve_relations=self.PRESERVE_RELATIONS)

            # add rows and columns in the matrices for possible discarded terms
            #print("\nAdding rows and columns for missing concepts in the burst matrix...\n")
            missing_terms = [term for term in self.words
                             if term not in directed_burst.index]

            for term in missing_terms:
                directed_burst.loc[term] = 0
                directed_burst[term] = 0

            #print("Shape of final directed burst matrix:", directed_burst.shape)

            # get an edgelist with the extracted prerequisite relations
            #print("Getting an edgelist with the extracted prerequisite relations...\n")
            sorted_edgelist = pd.DataFrame(self.to_edgelist(directed_burst),
                                           columns=["prerequisite", "target", "weight"])

            concept_map, definitions = self.df_to_data(sorted_edgelist, burst_res, use_conll=True)
            return concept_map, self._merge_contained_definitions(definitions)


        except ValueError as e:
            print("error:", sys.exc_info())
            #self.updateStatus("failed")
            raise e


    def df_to_data(self, sorted_edgelist: pd.DataFrame, burst_res: pd.DataFrame, use_conll: bool = False) -> tuple[list, list]:
        """
        Convert analysis results to concept maps.

        Parameters
        ----------
        sorted_edgelist : pandas.DataFrame
            Sorted edges with prerequisites and targets
        burst_res : pandas.DataFrame  
            Burst detection results
        use_conll : bool, optional
            Whether to use CoNLL tokenization

        Returns
        -------
        tuple
            (concept_map, definitions) containing relationship data
        """
        print("***** EKEEL - Video Annotation: burst_class.py::df_to_data() ******")
        concept_map = []
        definitions = []

        video = VideoAnalyzer("https://www.youtube.com/watch?v="+self.video_id,{"transcript_data"})
        sem_text= SemanticText(self.text, video.data["language"])
        
        if not use_conll:
            sentences = sem_text.tokenize()
        else:
            sentences = [sent.metadata["text"] for sent in self.conll]

        timed_sentences = get_timed_sentences(video.data["transcript_data"]["text"], sentences)

        if self.top_n is not None:
            sorted_edgelist = sorted_edgelist.head(self.top_n)

        for rel in sorted_edgelist.itertuples():
            if self.threshold < rel.weight:

                if self.first_occurence[rel.prerequisite] > self.first_occurence[rel.target]:
                    sent_id = self.first_occurence[rel.prerequisite]
                else:
                    sent_id = self.first_occurence[rel.target]

                a = {"prerequisite": rel.prerequisite,
                     "target": rel.target,
                     "creator": "Burst_Analysis",
                     "weight": "Strong",
                     "time": str(datetime.timedelta(seconds=timed_sentences[sent_id]["start"])),
                     "sent_id": sent_id,
                     "xywh": "None",
                     "word_id": "None",
                     "weight_burst":rel.weight
                     }
                if a not in concept_map:
                    concept_map.append(a)

        concept_longest_burst = {}

        for d in burst_res.itertuples():
            burst_len = d.end - d.start
            if d.keyword not in concept_longest_burst:
                concept_longest_burst[d.keyword] = burst_len

            elif burst_len > concept_longest_burst[d.keyword]:
                concept_longest_burst[d.keyword] = burst_len

        for d in burst_res.itertuples():
            if d.end - d.start > 1:

                if concept_longest_burst[d.keyword] == d.end - d.start:
                    descr_type = "Definition"
                else:
                    descr_type = "In Depth"

                definitions.append({
                    "concept": d.keyword,
                    "start_sent_id": d.start,
                    "end_sent_id": d.end,
                    "start": str(datetime.timedelta(seconds=timed_sentences[d.start]["start"])),
                    "end": str(datetime.timedelta(seconds=timed_sentences[d.end]["end"])),
                    "description_type": descr_type,
                    "creator": "Burst_Analysis"
                })

        #_,jsonld = create_burst_graph(self.video_id,definitions, concept_map)

        return concept_map, definitions


def compute_agreement_burst(concept_map1, concept_map2):
    """
    Compute the agreement between two concept maps using burst analysis.

    Parameters
    ----------
    concept_map1 : list of dict
        The first concept map, where each dict represents a relationship with 'prerequisite' and 'target' keys.
    concept_map2 : list of dict
        The second concept map, where each dict represents a relationship with 'prerequisite' and 'target' keys.

    Returns
    -------
    dict
        A dictionary containing the analysis type and the computed agreement score.

    Examples
    --------
    Example of the returned dictionary format:
        {
            "analysis_type": "agreement",
            "agreement": 0.85
        }
    """
    print("***** EKEEL - Video Annotation: burst_class.py::compute_agreement_burst() ******")

    words = []
    user1 = "gold"
    user2 = "burst"

    for rel in concept_map1:
        if rel["prerequisite"] not in words:
            words.append(rel["prerequisite"])

        if rel["target"] not in words:
            words.append(rel["target"])

    for rel in concept_map2:
        if rel["prerequisite"] not in words:
            words.append(rel["prerequisite"])

        if rel["target"] not in words:
            words.append(rel["target"])

    all_combs = agreement.createAllComb(words)

    # Calcolo agreement kappa no-inv all paths
    term_pairs = {user1: [], user2: []}
    term_pairs_tuple = {user1: [], user2: []}
    term_pairs[user1], all_combs, term_pairs_tuple[user1] = agreement.createUserRel(concept_map1, all_combs)
    term_pairs[user2], all_combs, term_pairs_tuple[user2] = agreement.createUserRel(concept_map2, all_combs)

    coppieannotate, conteggio = agreement.creaCoppieAnnot(user1, user2, term_pairs, all_combs, term_pairs_tuple)


    results = {"analysis_type": "agreement",
               "agreement":round(agreement.computeK(conteggio, all_combs), 3)}

    return results



def create_burst_graph(video_id,definitions,concept_map):
    """
    Create a burst graph for a given video, definitions, and concept map.

    Parameters
    ----------
    video_id : str
        The ID of the video.
    definitions : list of dict
        List of definitions, where each dict contains details such as concept, start, end, start_sent_id, end_sent_id, creator, and description_type.
    concept_map : list of dict
        List of concept relationships, where each dict contains details such as prerequisite, target, weight, time, sent_id, and word_id.

    Returns
    -------
    tuple
        A tuple containing the RDF graph and the JSON-LD representation of the graph.

    Examples
    --------
    Example of the returned tuple format:
        (Graph, jsonld)
    """
    print("***** EKEEL - Video Annotation: burst_class.py::create_burst_graph(): Inizio ******")

    creator = URIRef("Burst_Analysis")
    
    g = Graph()

    g.bind("oa", oa)
    g.bind("dctypes", dctypes)
    g.bind("edu", edu)
    g.bind("SKOS", SKOS)
    g.bind("dcterms", dcterms)


    video = URIRef("video_" + str(video_id))
    #video = URIRef(edurell + "video_" + str(video_id))
    g.add((video, RDF.type, dctypes.MovingImage))

    conll = URIRef("conll_" + str(video_id))
    #conll = URIRef(edurell + "conll_" + str(video_id))
    g.add((conll, RDF.type, dctypes.Text))


    # linking video conll
    ann_linking_conll = URIRef("ann0")
    g.add((ann_linking_conll, RDF.type, oa.Annotation))
    g.add((ann_linking_conll, oa.motivatedBy, edu.linkingConll))
    g.add((ann_linking_conll, oa.hasBody, conll))
    g.add((ann_linking_conll, oa.hasTarget, video))

    date = Literal(datetime.datetime.fromtimestamp(time.time()))

    #creo il nuovo nodo dei concetti
    #localVocabulary = URIRef("localVocabulary")
    #g.add((localVocabulary, RDF.type, SKOS.Collection))


    # add triples for every annotation
    for i, annotation in enumerate(definitions):
        ann = URIRef("ann" + str(i + 1))

        g.add((ann, RDF.type, oa.Annotation))

        g.add((ann, dcterms.creator, creator))

        g.add((ann, dcterms.created, date))
        g.add((ann, oa.motivatedBy, oa.describing))
        if annotation["description_type"] == "In Depth":
            g.add((ann, SKOS.note, Literal("conceptExpansion")))
        if annotation["description_type"] == "Definition":
            g.add((ann, SKOS.note, Literal("concept"+annotation["description_type"]))) 

        concept = URIRef("concept_" + annotation["concept"].replace(" ", "_"))

        
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
        

    num_definitions = len(definitions) + 1

    for i, annotation in enumerate(concept_map):
        ann = URIRef("ann" + str(num_definitions + i))

        target_concept = URIRef("concept_" +  annotation["target"].replace(" ", "_"))
        prereq_concept = URIRef("concept_" +  annotation["prerequisite"].replace(" ", "_"))

        #g.add((target_concept, RDF.type, SKOS.Concept))
        #g.add((prereq_concept, RDF.type, SKOS.Concept))

        g.add((ann, RDF.type, oa.Annotation))

        g.add((ann, dcterms.creator, creator))

        g.add((ann, dcterms.created, date))
        g.add((ann, oa.motivatedBy, edu.linkingPrerequisite))

        g.add((ann, oa.hasBody, prereq_concept))
        g.add((ann, SKOS.note, Literal(annotation["weight"].lower() + "Prerequisite")))

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

    context = ["http://www.w3.org/ns/anno.jsonld", {
               "@base": "https://edurell.dibris.unige.it/annotator/auto/"+video_id+"/",
      			"@version": 1.1,
      			"edu": "https://teldh.github.io/edurell#"
             } ]

    jsonld = json.loads(g.serialize(format='json-ld'))
    jsonld = pyld.jsonld.compact(jsonld, context)


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
    
    # sort by "id": "ann#" value
    jsonld["@graph"] = sorted(jsonld["@graph"],key=lambda x: int(x["id"][3:]) if str(x["id"][3:]).isnumeric() else 4242)
    return g, jsonld


def create_local_vocabulary(video_id,conceptVocabulary):
    """
    Create a local vocabulary graph for a given video and concept vocabulary.

    Parameters
    ----------
    video_id : str
        The ID of the video.
    conceptVocabulary : dict
        Dictionary of concepts and their synonyms.

    Returns
    -------
    dict
        A dictionary representing the local vocabulary in JSON-LD format.

    Examples
    --------
    Example of the returned dictionary format:
        {
            "id": "localVocabulary",
            "type": "skos:Collection",
            "skos:member": [
                {
                    "@id": "concept_concept1",
                    "@type": "skos:Concept",
                    "skos:prefLabel": {"@value": "concept1", "@language": "en"},
                    "skos:altLabel": [{"@value": "synonym1", "@language": "en"}, ...]
                },
                ...
            ]
        }
    """
    context = ["http://www.w3.org/ns/anno.jsonld", {
               "@base": "https://edurell.dibris.unige.it/annotator/auto/"+video_id+"/",
      			"@version": 1.1,
      			"edu": "https://teldh.github.io/edurell#"
             } ]
    language = get_video_data(video_id)["language"]
    graph = Graph()

    for concept in conceptVocabulary.keys():        
        uri_concept = URIRef("concept_" + concept.replace(" ", "_"))
        graph.add((uri_concept, RDF['type'], SKOS.Concept))
        graph.add((uri_concept, SKOS.prefLabel, Literal(concept, lang=language)))
        for synonym in conceptVocabulary[concept]:
            graph.add((uri_concept, SKOS.altLabel, Literal(synonym, lang=language)))

    jsonld = json.loads(graph.serialize(format='json-ld'))
    jsonld = pyld.jsonld.compact(jsonld, context)
    print(jsonld)
    local_vocabulary = {"id": "localVocabulary", "type": "skos:Collection"}
    if "@graph" in jsonld.keys():
        local_vocabulary["skos:member"] = jsonld["@graph"]
    return local_vocabulary

def convert_to_skos_concepts(concepts_name,conceptVocabulary,language):
    graph = Graph()
    for concept in concepts_name:        
        uri_concept = URIRef("concept_" + concept.replace(" ", "_"))
        graph.add((uri_concept, RDF['type'], SKOS.Concept))
        graph.add((uri_concept, SKOS.prefLabel, Literal(concept, lang=language)))
        for synonym in conceptVocabulary[concept]:
            graph.add((uri_concept, SKOS.altLabel, Literal(synonym, lang=language)))
    
    jsonld = json.loads(graph.serialize(format='json-ld'))
    #jsonld = pyld.jsonld.compact(jsonld, context)
    return jsonld["@graph"]


if __name__ == "__main__":
    #from pprint import pprint
    #definitions = [{'concept': 'machine', 'start_sent_id': 0, 'end_sent_id': 7, 'start': '0:00:00.060000', 'end': '0:00:31.319000', 'description_type': 'In Depth', 'creator': 'Burst Analysis'}, 
    #               {'concept': 'machine', 'start_sent_id': 64, 'end_sent_id': 74, 'start': '0:05:37.310000', 'end': '0:07:06.509000', 'description_type': 'Definition', 'creator': 'Burst Analysis'}, 
    #               {'concept': 'machine learning', 'start_sent_id': 0, 'end_sent_id': 7, 'start': '0:00:00.060000', 'end': '0:00:31.319000', 'description_type': 'In Depth', 'creator': 'Burst Analysis'}, 
    #               {'concept': 'machine learning', 'start_sent_id': 64, 'end_sent_id': 74, 'start': '0:05:37.310000', 'end': '0:07:06.509000', 'description_type': 'Definition', 'creator': 'Burst Analysis'}, 
    #               {'concept': 'learning', 'start_sent_id': 0, 'end_sent_id': 3, 'start': '0:00:00.060000', 'end': '0:00:14.879000', 'description_type': 'In Depth', 'creator': 'Burst Analysis'}, 
    #               {'concept': 'learning', 'start_sent_id': 38, 'end_sent_id': 42, 'start': '0:03:29.250000', 'end': '0:04:25.850000', 'description_type': 'In Depth', 'creator': 'Burst Analysis'}, 
    #               {'concept': 'learning', 'start_sent_id': 45, 'end_sent_id': 50, 'start': '0:04:19.350000', 'end': '0:04:59.690000', 'description_type': 'In Depth', 'creator': 'Burst Analysis'}, 
    #               {'concept': 'learning', 'start_sent_id': 64, 'end_sent_id': 74, 'start': '0:05:37.310000', 'end': '0:07:06.509000', 'description_type': 'Definition', 'creator': 'Burst Analysis'}, 
    #               {'concept': 'checker', 'start_sent_id': 8, 'end_sent_id': 13, 'start': '0:00:24.609000', 'end': '0:01:13.349000', 'description_type': 'Definition', 'creator': 'Burst Analysis'}]
    #pprint(_merge_contained_definitions(definitions))
    pass