#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#------------------------------------------------------------------
# Class for evaluating prerequisite relationship using wikipedia
#
#
# Author: Andre
#------------------------------------------------------------------
import gensim
import wikipediaapi
from gensim import corpora
import wikipedia
import nltk
import string
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re, math
from collections import Counter
import json

import sys
from time import sleep
import requests

import pandas as pd

wiki_wiki = wikipediaapi.Wikipedia('en')





WORD = re.compile(r'\w+')

def tokenizeContent(contentsRaw):
    tokenized = nltk.tokenize.word_tokenize(contentsRaw)
    return tokenized

def removeStopWordsFromTokenized(contentsTokenized):
    stop_word_set = set(nltk.corpus.stopwords.words('english'))
    filteredContents = [word for word in contentsTokenized if word not in stop_word_set]
    return filteredContents

def performPorterStemmingOnContents(contentsTokenized):
    porterStemmer = nltk.stem.PorterStemmer()
    filteredContents = [porterStemmer.stem(word) for word in contentsTokenized]
    return filteredContents

def removePunctuationFromTokenized(contentsTokenized):
    excludePuncuation = set(string.punctuation)
    
    # manually add additional punctuation to remove
    doubleSingleQuote = '\'\''
    doubleDash = '--'
    doubleTick = '``'
    doubleEqual = '=='
    tripleEqual = '==='

    excludePuncuation.add(doubleSingleQuote)
    excludePuncuation.add(doubleDash)
    excludePuncuation.add(doubleTick)
    excludePuncuation.add(doubleEqual)
    excludePuncuation.add(tripleEqual)

    filteredContents = [word for word in contentsTokenized if word not in excludePuncuation]
    return filteredContents

def convertItemsToLower(contentsRaw):
    filteredContents = [term.lower() for term in contentsRaw]
    return filteredContents

def processData(rawContents):
    cleaned = tokenizeContent(rawContents)
    cleaned = removeStopWordsFromTokenized(cleaned)
    cleaned = performPorterStemmingOnContents(cleaned)    
    cleaned = removePunctuationFromTokenized(cleaned)
    cleaned = convertItemsToLower(cleaned)
    return cleaned

def calc_and_print_CosineSimilarity_for_all(tfs, text):
    numValue = cosine_similarity(tfs[0], tfs[1])
    #print(numValue, end='\t')
    return (numValue[0][0])
    #(cosine_similarity(tfs[i], tfs[n]))[0][0]
    
    
def get_cosine(vec1, vec2):
     intersection = set(vec1.keys()) & set(vec2.keys())
     numerator = sum([vec1[x] * vec2[x] for x in intersection])

     sum1 = sum([vec1[x]**2 for x in vec1.keys()])
     sum2 = sum([vec2[x]**2 for x in vec2.keys()])
     denominator = math.sqrt(sum1) * math.sqrt(sum2)

     if not denominator:
        return 0.0
     else:
        return float(numerator) / denominator

def text_to_vector(text):
     words = WORD.findall(text)
     return Counter(words)

def page_finder(words, page_words, wiki_backlinks):
    
    for concept, title in words.items():
        print(concept, title)
        if title:
            try:
                poss = wikipedia.page(title=title, auto_suggest=False)
                page_words[concept] = poss
            except wikipedia.exceptions.DisambiguationError as e:
                print("disamb")
                pass
            except wikipedia.exceptions.PageError as e:
                print("err")
                pass
            except requests.exceptions.RequestException as e:
                #troppe richieste insieme a wikipedia, mi fermo e riprovo
                sleep(5)
                print(e)
                continue
    print("fatto")
    for c in list(page_words.keys()):
        title = page_words[c].title

        try:
            page = wiki_wiki.page(title)
            if page.exists():
                num_bl = len(page.backlinks)
                wiki_backlinks[c] = num_bl
            else:
                wiki_backlinks[c] = 0
            print(title, wiki_backlinks[c])
        except requests.exceptions.RequestException as e:
            # troppe richieste insieme a wikipedia, mi fermo e riprovo
            sleep(5)
            continue

def usage_definition(a, b, page_words):
    # Method 'Usage in Definition'
    b_def = page_words[b].summary.upper()
    if (a.upper() in b_def):                      # If 'a' appears in 'b' definition# Then 'a' is a prerequisite of 'b'
        return 1
    else:
        return 0


def topic_model(page_words):                                                                                             # Method for calculating 'Range of Topic Coverage'
    clean_doc = []                                                                                                  # List of all wikipedia concepts pages
    for concept in page_words.values():
        clean_doc.append(processData(concept.content))                                                              # Cleaning all wikipedia pages in the list from stopwords etc...
    
    dictionary = corpora.Dictionary(clean_doc)                      
    doc_term_matrix = [dictionary.doc2bow(doc) for doc in clean_doc] 
    
    Lda = gensim.models.ldamodel.LdaModel
    ldamodel = Lda(doc_term_matrix, num_topics = 5, id2word = dictionary, passes = 50, minimum_probability = 0.0)
    result = [ldamodel, doc_term_matrix]
    return result
    
def out_links(b, a, page_words):
    """Method to check outlinks in a page"""
    return (len(page_words[a].links) - len(page_words[b].links))

'''def in_links (a, b, page_words):
        a_page = wiki_wiki.page(page_words[a].title)
        b_page = wiki_wiki.page(page_words[b].title)
        if (a_page.exists() and b_page.exists()):
            return (len(a_page.backlinks) - len(b_page.backlinks))
        else:
            return 0'''

def in_links(a, b, page_backlinks):
    return page_backlinks[a] - page_backlinks[b]

def entropy (a, b, ldamodel, page_words, doc_term_matrix):
    tca = tcb = 0
    for Fim in ldamodel[doc_term_matrix[list(page_words.keys()).index(a)]]:
        tca -= Fim[1] * math.log(Fim[1])
    for Fim in ldamodel[doc_term_matrix[list(page_words.keys()).index(b)]]:
        tcb -= Fim[1] * math.log(Fim[1])
    return tca - tcb
    
def cosinesim(a, b, page_words):
    rawContentDict = {}
    rawContentDict["text1"] = page_words[a].content   
    rawContentDict["text2"] = page_words[b].content
    
    text = [rawContentDict["text1"], rawContentDict["text2"]]
    tfidf = TfidfVectorizer(tokenizer=processData, stop_words='english')
    tfs = tfidf.fit_transform(rawContentDict.values())
    return calc_and_print_CosineSimilarity_for_all(tfs, text)
    
def normalize(dictionary):
    if dictionary:
        maxi = max(list(dictionary.values()))
        mini = min(list(dictionary.values()))
        dictionary.update((k, (v - mini)/(maxi - mini)) for k,v in dictionary.items())
    




        
def method_4(words, to_save=False):
    try:

        missingRel = []
        page_words = {}
        lernDict = {}
        cosinDict = {}
        wiki_backlinks = {}

        page_finder(words, page_words, wiki_backlinks)

        print("pagine trovate")
        result = topic_model(page_words)
        ldamodel = result[0]
        doc_term_matrix = result[1]

        concept_map = []
        content_dict = []
        v_dict=[]
        sum_learn = 0
        sum_content = 0
        content_sims = []
        learn_diffs = []
        count = 0
        res_df = pd.DataFrame(columns=["prerequisite", "target", "learnLevel", "contentSim", "usage"])

        for a in list(page_words.keys()):
            for b in [x for x in list(page_words.keys()) if x != a]:
                if(usage_definition(a, b, page_words)):
                    concept_map.append({"prerequisite":a, "target":b})
                    v_dict.append({"prerequisite": a, "target": b, "learnLevel": None, "contentSim":None, "usage": 1})

                else:
                    #inLinksDiff = in_links(a, b, page_words)
                    inLinksDiff = in_links(a, b, wiki_backlinks)
                    outLinksDiff = out_links(a, b, page_words)
                    topicCovDiff = entropy(a, b, ldamodel, page_words, doc_term_matrix)
                    contentSim = cosinesim(a, b, page_words)
                    if(outLinksDiff == 0):
                        learnLevelDiff = topicCovDiff
                    else:
                        learnLevelDiff =  inLinksDiff/outLinksDiff + topicCovDiff
                    valuet = {a + "__" + b : learnLevelDiff}
                    lernDict.update(valuet)
                    valuet = {a + "__" + b : contentSim}
                    cosinDict.update(valuet)
                    missingRel.append(a + "__" + b)

                    v_dict.append({"prerequisite": a, "target": b, "learnLevel": learnLevelDiff, "contentSim":contentSim, "usage": None})
                    res_df = res_df.append({"prerequisite": a, "target": b, "learnLevel": learnLevelDiff, "contentSim":contentSim}, ignore_index=True)

                    # content_sims.append(contentSim)
                    # learn_diffs.append(learnLevelDiff)

        normalize(cosinDict)
        normalize(lernDict)

        content_sims = list(cosinDict.values())
        learn_diffs = list(lernDict.values())

        content_sims.sort()
        learn_diffs.sort()

        if to_save:
            with open('results/method4.json', 'w') as fp:
                json.dump(v_dict, fp)

            res_df.to_csv("results/m4.csv", sep=";", encoding="utf-8")

        threshold_content = content_sims[int(len(content_sims)*60/100)]
        threshold_learn = learn_diffs[int(len(learn_diffs)*60/100)]

        for r in v_dict:
            if r["learnLevel"] is not None:
                if r["learnLevel"] > threshold_learn and r["contentSim"] > threshold_content:
                    concept_map.append({"prerequisite": r["prerequisite"], "target": r["target"]})




    except:
        print("error:", sys.exc_info())
        raise
    

    return concept_map