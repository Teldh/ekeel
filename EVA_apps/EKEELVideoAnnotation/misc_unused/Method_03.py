# -*- coding: utf-8 -*-
#------------------------------------------------------------------
# Class for evaluating prerequisite relationship using the reference
# distance
#
# Authors: ...
#------------------------------------------------------------------
import wikipedia
import math
import requests
from time import sleep
import sys
import json
import pandas as pd

def page_finder(words, page_words):
    """ For every concept takes the out links and save them in a dictionary"""
    
    for concept, title in words.items():
        if title:
            try:
                poss = wikipedia.page(title=title, auto_suggest=False)
                page_words[concept] = poss
                page_words[concept + "_links"] = poss.links
            except wikipedia.exceptions.DisambiguationError as e:
                page_words[concept] = None
                page_words[concept + "_links"] = None
            except wikipedia.exceptions.PageError as e:
                page_words[concept] = None
                page_words[concept + "_links"] = None
            except requests.exceptions.RequestException as e:
                # troppe richieste insieme a wikipedia, mi fermo e riprovo
                print(e)
                sleep(5)
                continue
        else:
            page_words[concept] = None
            page_words[concept + "_links"] = None
        
def count_concept(words, links, page_words):
    """ Append every link to links array"""
    
    for concept in words:
        for list_link in words:
            if (page_words[str(list_link) + "_links"]):
                if (concept.capitalize() in page_words[list_link + "_links"]):
                    links.append(1)
                else:
                    links.append(0)
            else:
                links.append(0)
 
def counter_df(links, count_df, length, words):
    """ Append in count df the links presented in every concept page. so every cell of count_df
    rapresent the numbers of links in a page """
    for n in range(length):
        count_df.append(sum(links[int(n)*length:length*(int(n)+1)]))    
    
def refD(a, b, links, length, count_df, words): #calcola il reference distance value
    
    indexA = list(words.keys()).index(a)
    indexB = list(words.keys()).index(b)
    denA = denB = 0
    numA = numB = 0
    
    for i, n in enumerate(range(length)):
        if(links[(length*i) + indexA]):
            denA += weight(i, count_df, words)
            if(links[length*i + indexB]):
                numA =+ weight(i, count_df, words)
                
        if(links[(length*i + indexB)]):
            denB += weight(i, count_df, words)
            if(links[length*i + indexA]):
                numB =+ weight(i, count_df, words)
    
    if (denA == 0 and denB == 0):
        return 0
    elif denA == 0:
        return (-numB/denB)
    elif denB == 0:
        return (numA/denA)
    else:
        return (numA/denA) - (numB/denB)
           
def weight(i, count_df, words):
    return math.log(len(words)/count_df[i])





def method_3(words, threshold, to_save=False):
    try:

        concept_map = []

        length = len(words)
        links = []
        count_df = []
        page_words = {}

        refD_csv = []
        res_df = pd.DataFrame(columns=["prerequisite", "target", "refD"])

        page_finder(words, page_words) # words is a dictionary in which each word is linked to the corresponding wiki page.
        count_concept(words, links, page_words) # guarda se una parola è nei link di un altra pagina, se si mette un 1 nell'array links, altrimenti mette 0
        counter_df(links, count_df, length, words) # popola l'array count_df in cui ogni cella corrisponde al numero di volte in cui una parola appare nei link delle altre parole e viene utilizzato per calcolare il refD
        for concept in words:
            for word in [word for word in words if word != concept]:
                valueRefD = refD(concept, word, links, length, count_df, words)

                refD_csv.append({"prerequisite":word, "target": concept, "refD": valueRefD})
                res_df = res_df.append({"prerequisite":word, "target": concept, "refD": valueRefD}, ignore_index=True)

                if valueRefD > threshold:
                    concept_map.append({"prerequisite":word, "target": concept})

        if to_save:
            with open('results/refD.json', 'w') as fp:
                json.dump(refD_csv, fp)

            res_df.to_csv("results/refD.csv", sep=";", encoding="utf-8")



    except:

        print("error:", sys.exc_info())
        raise

    return concept_map