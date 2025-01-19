# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# Class for evaluating prerequisite relationship using
# hyponyms, hypernyms and meronyms
#
# Authors: ...
# Modified by Luca Mirenda
# ------------------------------------------------------------------

import nltk;
from nltk.corpus import wordnet as wn;
import sys


class Method_1():
    """
    Class for evaluating prerequisite relationship using hyponyms, hypernyms and meronyms
    Attributes:
        - words: list of strings
        - pre_req: dict with all prerequisites
    """

    def __init__(self, words):
        """
            :param words: array of concepts
        """
        self.words = words
        self.pre_req = dict.fromkeys(words)
        for word in self.pre_req:
            self.pre_req[word] = []


    def hyponyms(self, concept):
        """ get a concept and takes all meanings from wordnet. Then gets all the hyponyms of
            that word and check if it's inside the list words
             :param concept: string
             :return
        """
        meanings = wn.synsets(concept)
        for word in meanings:
            for types in word.hyponyms():
                for lemma in types.lemmas():
                    self.search_inv(concept, lemma.name().lower())

    def hypernyms(self, concept):
        """ get a concept and takes all meanings from wordnet. Then gets all the hypernyms of
            that word and check if it's inside the list words
            :param concept: string
        """

        # iperonimi fino alla root
        meanings = wn.synsets(concept)
        for word in meanings:
            for paths in (word.hypernym_paths()):
                for level in paths:
                    for lemma in level.lemmas():
                        self.search(concept, lemma.name().lower())

    def meronyms(self, concept):
        """ get a concept and takes all meanings from wordnet. Then gets all the different meronyms of
            that word and check if it's inside the list words
            :param concept:string
        """
        meanings = wn.synsets(concept)
        for word in meanings:
            for meronym in word.part_meronyms():
                for lemma in meronym.lemmas():
                    self.search_inv(concept, lemma.name().lower())
            for meronym in word.substance_meronyms():
                for lemma in meronym.lemmas():
                    self.search_inv(concept, lemma.name().lower())
            for meronym in word.member_holonyms():
                for lemma in meronym.lemmas():
                    self.search_inv(concept, lemma.name().lower())

    def search(self, concept, lemma):
        """ add lemma as prerequisite of concept
             :param concept
             :param lemma
        """
        if (lemma in self.words):
            self.pre_req[concept].append(lemma)

    def search_inv(self, concept, lemma):
        """ add concept as prerequisite of lemma
             :param concept
             :param lemma
        """
        if (lemma in self.words):
            self.pre_req[lemma].append(concept)




    def launch(self):
        """Launch Method 1 and update database"""
        concept_map = []
        try:
            self.words = [word.lower() for word in self.words]

            for i, word in enumerate(self.words):
                self.words.remove(word)
                self.hyponyms(word)
                self.hypernyms(word)
                self.meronyms(word)
                self.words.insert(i, word)


            for concept in self.words:
                for lemma in [lemma for lemma in self.words if concept != lemma]:
                    if lemma in self.pre_req[concept]:
                        concept_map.append({"prerequisite": lemma, "target": concept})



        except:
            print("error:", sys.exc_info())
            raise


        return concept_map