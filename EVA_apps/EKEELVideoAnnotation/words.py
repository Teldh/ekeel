import numpy as np
import phrasemachine
import spacy
import re
from nltk.corpus import words
from nltk import WordNetLemmatizer
from typing import List,Tuple
from bisect import insort_left
from sklearn.feature_extraction.text import CountVectorizer
from sentence_transformers import SentenceTransformer
from difflib import ndiff
import re
from numpy import empty,prod,sum,all
from numpy.linalg import norm
#from transformers import pipeline
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity
from fuzzywuzzy.fuzz import partial_ratio, ratio
from nltk.tokenize import sent_tokenize
import nltk
from rake_nltk import Rake
from pandas import DataFrame
import os
os.environ["TOKENIZERS_PARALLELISM"] = "true"


from locales import Locale 
import db_mongo
from NLP_API import ItaliaNLAPI
from conll import conll_gen

#try:
#    nltk.data.find('corpora/wordnet')
#except LookupError:
#    nltk.download("wordnet")

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download("stopwords")

try:
    nltk.data.find('corpora/words')
except LookupError:
    nltk.download("words")


try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download("punkt")

for language in Locale().get_supported_languages():
    if not { 'en':'en_core_web_lg','it':'it_core_news_lg'}[language] in spacy.util.get_installed_models(): 
        spacy.cli.download({ 'en':'en_core_web_lg','it':'it_core_news_lg'}[language])





class NLPSingleton():
    '''
    Multilanguage NLP Singleton
    
    Spacy is kept in memory because is used quite often, while the SentenceTransformer is called once so is left to the garbage collector
    '''
    _instance = None
    _spacy:spacy
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NLPSingleton, cls).__new__(cls)
            cls._spacy = { 'en':spacy.load('en_core_web_lg'),'it':spacy.load('it_core_news_lg')}
        return cls._instance
            
    def lemmatize(self, text:str, lang:str):
        return NLPSingleton()._spacy[lang](text)            
    
    @staticmethod
    def encode_text(text:str):
        return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2').encode(text,convert_to_tensor=True)
    
    
    def destroy(self):
        for lang in self._spacy.keys():
            self._spacy[lang] = None
        NLPSingleton._instance = None
     
        
class SemanticText():
    _text:str
    _tokenized_text:'str or None'
    _language:str

    def __init__(self,text:str,language:str) -> None:
        assert text is not None and language is not None, 'must set both text and language'
        self._text = text
        self._tokenized_text = None
        self._language = language
        self._nlp = NLPSingleton()

    def set_text(self,text:str,language:str=None):
        '''
        If language is None, it's assumed the same 
        '''
        self._text = text
        if language is not None:
            self._language = language
        self._tokenized_text = None
        return self
    
    def get_text(self):
        return self._text

    def get_language(self):
        return self._language
    
    def lemmatize_abbreviations(self):
        '''
        Used for english
        '''
        if self._language == Locale.get_pt1_from_full('English'):
            self._text = self._text.replace("'ve", " have").replace("'re", " are").replace("'s", " is").replace("'ll", " will")
    
    def extract_keywords_from_title(self):
        #str_text = re.sub(self.get_title_opening(),' ',self._text.lower())
        return None #[keyword[0] for keyword in self._nlp_processors.rake_models[self._language].run(str_text, maxWords=3, minFrequency=1)] 

    def lemmatize(self):
        assert self._text is not None
        tokens = self._nlp.lemmatize(self._text, self._language)
        #print("'",tokens,"'")
        return [token.lemma_ for token in tokens]

    def tokenize(self):
        if self._tokenized_text is None:
            self._tokenized_text = sent_tokenize(self._text,Locale.get_full_from_pt1(self._language))
        return self._tokenized_text
    
    def get_embeddings(self):
        self.tokenize()
        return NLPSingleton().encode_text(self._tokenized_text)
    
    def get_semantic_structure_info(self):
        doc = self._nlp.lemmatize(self._text, self._language)
        term_infos = {"text": self._text, "lemmatization_data": {"tokens": []}}
        for i, token in enumerate(doc):
            term_word = {"word": token.text,
                         "gen": token.morph.get("Gender")[0] if len(token.morph.get("Gender")) else "",
                         "num": token.morph.get("Number")[0] if len(token.morph.get("Number")) else "",
                         "lemma": token.lemma_
                        }
            term_infos["lemmatization_data"]["tokens"].append(term_word)
            if token.dep_ == "ROOT":
                term_infos["lemmatization_data"]["head_indx"] = i
        return term_infos


class WhisperToPosTagged():
    _lang:str
    
    def __init__(self,language:str) -> None:
        self._lang = language
    
    def _group_short_sentences(self, timed_sentences:list, min_segment_len:int=4, min_segment_duration:float=3):
        for i, sentence in reversed(list(enumerate(timed_sentences))): 
            # if i=4 and sent3 = "Ebbene," sent4 = "nulla si puo' dire perche' tutto e' stato detto." => merge into "Ebbene, nulla si puo' dire perche' tutto e' stato detto."
            # if sent3 = "quindi otteniamo cio' che ci aspettiamo," and sent4 = "cioe' niente." => merge into sent3 = "quindi otteniamo cio' che ci aspettiamo, cioe' niente." and pop sent4
            if i > 0 and not timed_sentences[i-1]["text"].endswith(".") and \
              (len(sentence["text"].strip().split()) < min_segment_len or 
               len(timed_sentences[i-1]["text"].strip().split()) < min_segment_len or 
               sentence["end"] - sentence["start"] < min_segment_duration or 
               timed_sentences[i-1]["text"].endswith("'") or 
               sentence["text"].startswith("'")):
                prev_segment = timed_sentences[i-1]
                prev_segment["text"] += " " + sentence["text"] 
                for word in sentence["words"]:
                    prev_segment["words"].append(word)
                prev_segment["end"] = sentence["end"]
                timed_sentences.pop(i)
        return timed_sentences 
        
    def _apply_italian_fixes(self,timed_sentences:list):
        '''
        Applies italian specific fixes to the text in order to be correctly analized by ItaliaNLP and matched back
        Furthemore groups short sentences.
        '''

        out_sentences = []    
        accent_replacements = {
                                  "e'": "è", "E'": "È",
                                  "o'": "ò", "O'": "Ò",
                                  "a'": "à", "A'": "À",
                                  "i'": "ì", "I'": "Ì",
                                  "u'": "ù", "U'": "Ù", "po'": "pò"
                              }
        number_regex = r'(-?\d+(?:\.\d*)?)'
        big_numer_regex = r'(-?)(\d+)(.\d\d\d)+'
        degrees_regex = number_regex[:-1] + r'°)'
        temperature_regex = degrees_regex[:-1] + r'[C|c|F|f|K|k])'

        for i, segment in enumerate(timed_sentences):
            segment = {"text": segment["text"].lstrip(),
                       "words": segment["words"],
                       "start": segment["start"], 
                       "end": segment["end"]}

            to_remove_words = []

            for j, word in enumerate(segment["words"]):
                word["word"] = word["word"].lstrip()

                word.pop("tokens",None)

                # Match "fatto," that must be split into tokens "fatto" and "," 
                if len(word["word"]) > 1 and word["word"][-1] in [",",".","?","!"]:
                    new_word = word.copy()
                    new_word["word"] = word["word"][-1]
                    segment["words"].insert(j+1, new_word)
                    word["word"] = word["word"][:-1]

                if word["word"][0] == "," and any(re.findall(r',\d+',word["word"])):
                    new_word = word.copy()
                    new_word["word"] = word["word"][1:]
                    word["word"] = word["word"][0]
                    segment["words"].insert(j+1, new_word)
                    segment["text"] = segment["text"].replace(",",", ")

                # Realign apostrophe and replace accented words
                if word["word"].startswith("'"):
                    segment["words"][j-1]["word"] += "'"
                    if len(segment["words"][j-1]["word"]) == 2:
                        for pattern, replacement in accent_replacements.items():
                            segment["words"][j-1]["word"] = re.sub(pattern, replacement, segment["words"][j-1]["word"])
                            segment["text"] = re.sub(pattern, replacement, segment["text"])
                    word["word"] = word["word"][1:]

                # Match math symbol terminology "x'" that should be "x primo" and "E'" that should be "È"
                elif any(re.findall(r"(?<![a-zA-Z])[a-zA-Z]'", word["word"])):
                    match_ = re.findall(r"(?<![a-zA-Z])[a-zA-Z]'", word["word"])[0]
                    if match_ in accent_replacements.keys():
                        replacement = accent_replacements[word["word"]]
                        segment["text"] = segment["text"].replace(word["word"],replacement)
                        word["word"] = replacement
                    # TODO there can be a case like "l'altezza di l'(primo) nel..." in text that can break it
                    # but make it work would require to rework the structures and map words as indices of the text string
                    elif any(re.findall(f"{match_}[ .,:?!]",segment["text"])):
                        word["word"] = word["word"].split("'")[0]
                        new_word = word.copy()
                        new_word["word"] = "primo"
                        segment["words"].insert(j+1,new_word)
                        segment["text"] = segment["text"].replace(match_,match_[:-1]+" primo")
                    # fixes some random " l 'apostrofo mal messo" -> " l'apostrofo mal messo"
                    elif any(re.findall(r"[a-zA-Z]+ '", segment["text"])):
                        match_ = re.findall(r"[a-zA-Z]+ '", segment["text"])[0]
                        segment["text"] = segment["text"].replace(match_, match_[:-2]+"'")

                # "di raggio R." separated symbol R -> "di raggio R ." for T2K correct pos tag
                # TODO check with another video that Whisper AI correctly separates the two words in words list 
                elif any(re.findall(r"\s[a-zA-Z][?,.!;:]", segment["text"])):
                    segment["text"] = re.sub(r"\s([a-zA-Z])([?,.!;:])",r" \1 \2", segment["text"])

                # Match "po'" but ignores "anch'" or "dell'" 
                elif any(re.findall(r"[a-zA-Z]+'", word["word"])) and word["word"].endswith("'") and len(word["word"]) >= 3:
                    match_ = re.findall(r"[a-zA-Z]+'", word["word"])[0]
                    if match_ in accent_replacements.keys():
                        replacement = accent_replacements[word["word"]]
                        word["word"] = replacement

                # Case "termo" "-idrometrico" -> merged into "termo-idrometrico" for T2K compatibility
                # can also be "pay-as-you-go" found split into "pay", "-as", "-you", "-go"
                elif word["word"].startswith("-"):
                    for head_word in segment["words"][j-1::-1]:
                        if not head_word["word"].startswith("-"):
                            break
                    head_word["word"] = head_word["word"] + word["word"]
                    head_word["end"] = word["end"]
                    to_remove_words.append(j)

                # Sometime happened the shift of the apostrophe ["accetta l", "'ipotesi forte"] 
                # Should not happen due to prior merge
                #if segment["text"].startswith("'") and not "'" in segment["words"][0] and i > 0:
                #    segment["text"] = segment["text"][1:]
                #    timed_sentences[i-1]["text"] += "'"
                #    timed_sentences[i-1]["words"][-1]["word"] += "'"

                # Case "25°C" -> "25°" "celsius"
                if any(re.findall(temperature_regex,word["word"])):
                    new_word = word.copy()
                    new_word["word"] = word["word"][-1]
                    #segment["text"] = segment["text"].replace(word["word"][-1]," "+scale)
                    segment["words"].insert(j+1, new_word)
                    word["word"] = word["word"][:-1]

                # Case "22°" -> "22" "°"
                if any(re.findall(degrees_regex, word["word"])):
                    new_word = word.copy()
                    new_word["word"] = "°" 
                    #segment["text"] = segment["text"].replace("°"," ° ")
                    segment["words"].insert(j+1, new_word)
                    word["word"] = word["word"][:-1]

                elif any(re.findall(r"\s\.[0-9]+", word["word"])):
                    new_word = word.copy()
                    new_word["word"] = word["word"][1:]
                    segment["words"].insert(j+1, new_word)
                    word["word"] = "."

                if any(re.findall(big_numer_regex, segment["text"])):
                    match_ = "".join(re.findall(big_numer_regex, segment["text"])[0])
                    segment["text"] = segment["text"].replace(match_, match_.replace("-"," - ").replace("."," . "))

                # Sometimes words list don't perfectly match the text: "'attrito della ruota", words: ["attrito","della", "ruota'"]
                # But "pò" in words and "po'" in text match, TODO Fix with T2K 
                if word["word"] not in segment["text"] and not (word["word"] == "pò" and "po'" in segment["text"]) :
                    longest_substring = ''
                    text = segment["text"]
                    word_ = word["word"]
                    for ch_l in range(len(word_)):
                        for ch_r in range(ch_l + 1, len(word_) + 1):
                            if word_[ch_l:ch_r] in text and len(word_[ch_l:ch_r]) > len(longest_substring):
                                longest_substring = word_[ch_l:ch_r]
                    # Replace the word with the longest substring
                    word["word"] = longest_substring

                # Random points in words
                if len(word["word"]) > 1 and word["word"].endswith("."):
                    new_word = word.copy()
                    new_word["word"] = "."
                    word["word"] = word["word"][:-1]
                    segment["words"].insert(j+1, new_word)


                # Case "22%" -> "22" "%"
                elif any(re.findall(number_regex+'%', word["word"])):
                    new_word = word.copy()
                    word["word"] = word["word"][:-1]
                    new_word["word"] = "%"
                    segment["words"].insert(j+1, new_word)

                if any(re.findall(number_regex+'%', segment["text"])):
                    segment["text"] = re.sub(r"%([?,.!;:])",r"% \1", segment["text"])
                    segment["text"] = re.sub(r"([0-9])%",r"\1 %", segment["text"])


                # Match with "dell'SiO2" -> split into tokens "dell'" and "SiO2"
                if len(word["word"].split("'")) > 1 and len(word["word"].split("'")[1]) > 0:
                    before_apos, after_apos = word["word"].split("'")
                    new_word = word.copy()
                    new_word["word"] = after_apos
                    segment["words"].insert(j+1, new_word)
                    word["word"] = before_apos+"'"

            for indx in reversed(to_remove_words):
                del segment["words"][indx]

            segment["text"] = segment["text"].replace("  ", " ")
            out_sentences.append(segment)

        return out_sentences
    
    def _apply_english_fixes(self,timed_sentences:list):
        for sent_id, sentence in enumerate(timed_sentences):
            sentence = {"text":sentence["text"].strip(),
                        "start":sentence["start"],
                        "end":sentence["end"],
                        "words":sentence["words"]}
            timed_sentences[sent_id] = sentence 
            for word_id, word in enumerate(sentence["words"]):
                word.pop("tokens",None)
                word["word"] = word["word"].strip()
                if any([word["word"].endswith(punct) for punct in [",",".","!","?"]]) and len(word["word"]) > 1:
                    new_word = word.copy()
                    new_word["word"] = new_word["word"][-1]
                    sentence["words"].insert(word_id+1, new_word)
                    word["word"] = word["word"][:-1]
        return timed_sentences
                
                
                
    def _restore_italian_fixes(timed_transcript:list):
        for sentence in timed_transcript:
            sentence["text"] = re.sub(r'\s+%', '%', sentence["text"])                           # replace " %" with "%"
            sentence["text"] = re.sub(r'%\s([?,.!;:])', r'%\1', sentence["text"])               # replace "% ," with "%,"
            sentence["text"] = re.sub(r"\s([a-zA-Z])\s([?,.!;:])",r" \1\2", sentence["text"])   # replace " A ." with " A."
            match_ = re.findall(r'(\s-\s)?(\d+)(\s.\s\d{3})+',sentence["text"])                 # find any big number spaced " - 24 . 000" (meno 24 mila)
            if any(match_):
                sentence["text"] = sentence["text"].replace("".join(match_[0]), "".join(match_[0]).replace(" ",""))
        return timed_transcript

    def request_tagged_transcript(self, video_id:str, timed_transcript:list):
        timed_transcript = self._group_short_sentences(timed_transcript)
        if self._lang == "it":
            timed_transcript = self._apply_italian_fixes(timed_transcript)
            string_transcript = " ".join(timed_sentence["text"] for timed_sentence in timed_transcript if not "[" in timed_sentence['text'])
            timed_transcript = self._restore_italian_fixes(timed_transcript)

            api_obj = ItaliaNLAPI()
            doc_id = api_obj.upload_document(string_transcript, language=language, async_call=False)

            tagged_sentences = api_obj.wait_for_pos_tagging(doc_id)

            tagged_transcript = {"full_text":"", "words":[]}
            for sentence in tagged_sentences:
                tagged_transcript["full_text"] += sentence["sentence"]+" "
                for word in sentence["words"]:
                    # append the word from NLPTranscript but remove "-" from for example "inviar-", "li"
                    word = {"word":     word["word"] if len(word["word"]) == 1 or (len(word["word"]) > 1 and not word["word"].endswith("-")) else word["word"][:-1], 
                            "lemma":    word["lemma"], 
                            "pos":      word["pos"], 
                            "gen":      word["gen"], 
                            "cpos":     word["cpos"],
                            "num":      word["num"]}
                    tagged_transcript["words"].append(word)

            words_cursor = 0
            tagged_transcript_words = tagged_transcript["words"]
            is_first_part_of_word = True
            is_misaligned = False
            for sentence in timed_transcript:
                for word_indx, word in enumerate(sentence["words"]):
                    if word["word"] == tagged_transcript_words[words_cursor]["word"] or \
                      (word["word"] == "po'" and tagged_transcript_words[words_cursor]["word"] == "p\u00f2"):
                        transcript_word = tagged_transcript_words[words_cursor]
                        word["gen"] = transcript_word["gen"] if transcript_word["gen"] is not None else ""
                        word["lemma"] = transcript_word["lemma"]
                        word["pos"] = transcript_word["pos"]
                        word["cpos"] = transcript_word["cpos"]
                        word["num"] = transcript_word["num"] if transcript_word["num"] is not None else ""

                    # Can be for example in Whisper transcript "inviarli" a single word but ItaliaNLP gives "inviar", "li"
                    elif tagged_transcript_words[words_cursor]["word"] in word["word"]:
                        if is_first_part_of_word:
                            new_word = word.copy()
                        transcript_word = tagged_transcript_words[words_cursor]
                        word["word"] = transcript_word["word"]
                        word["gen"] = transcript_word["gen"] if transcript_word["gen"] is not None else ""
                        word["lemma"] = transcript_word["lemma"]
                        word["pos"] = transcript_word["pos"]
                        word["cpos"] = transcript_word["cpos"]
                        word["num"] = transcript_word["num"] if transcript_word["num"] is not None else ""
                        if is_first_part_of_word:
                            word["end"] = 0.8*(word["end"]-word["start"]) + word["start"]
                        else:
                            word["start"] = sentence["words"][word_indx-1]["end"]
                        if is_first_part_of_word:
                            sentence["words"].insert(word_indx+1, new_word) 
                            is_first_part_of_word = False
                        else:
                            is_first_part_of_word = True

                    # match is partial so it's wrong, print a message on backend but continue (TODO but may break)
                    elif word["word"] in tagged_transcript_words[words_cursor]["word"] and \
                      ((len(sentence["words"]) > word_indx+1 and sentence["words"][word_indx+1]["word"] in tagged_transcript_words[words_cursor]["word"]) or \
                      is_misaligned) :
                        tagged_word = tagged_transcript_words[words_cursor]
                        word["gen"] = tagged_word["gen"]
                        word["lemma"] = tagged_word["lemma"]
                        word["pos"] = tagged_word["pos"]
                        word["cpos"] = tagged_word["cpos"] 
                        word["num"] = tagged_word["gen"]
                        is_misaligned = not tagged_word["word"].endswith(word["word"])
                        print(f"Error in matching tagged and timed transcript, for video: {self.data['video_id']}")
                        print(f"word \"{word['word']}\" is not \"{tagged_transcript_words[words_cursor]['word']}\"")
                        if is_misaligned:
                            words_cursor -= 1
                        else:
                            print("Realigned successfully!")
                    words_cursor += 1
        elif self._lang == "en":
            conll = conll_gen(video_id,SemanticText(" ".join(timed_sentence["text"] for timed_sentence in timed_transcript if not "[" in timed_sentence['text']), self._lang), self._lang)
            conll_words = []
            for sentence in conll:
                for token in sentence:
                        conll_words.append({ "id":token["id"],
                                             "word":token["form"],
                                             "lemma":token["lemma"],
                                             "cpos":token["upos"],
                                             "pos":token["xpos"],
                                             "num":token["feats"].get("Number","").replace("Sing","s").replace("Plur","p") if token["feats"] else "",
                                             "gen":"" # token["feats"].get("Gen","") # There is no gen in udpipe
                                             })
            timed_transcript = self._apply_english_fixes(timed_transcript)
            word_indx = 0
            skip_next = False
            for sent_id, sentence in enumerate(timed_transcript):
                for word_id, word in enumerate(sentence["words"]):
                    conll_word = conll_words[word_indx]
                    if ("id" in conll_word.keys() and type(conll_word["id"]) != int) or (conll_word["word"] in word["word"] and conll_word["word"] != word["word"]):
                        if ("id" in conll_word.keys() and type(conll_word["id"]) != int):
                            word_indx += 1
                        conll_word = conll_words[word_indx]
                        conll_word.pop("id",None)
                        sentence["words"][word_id] = conll_word
                        conll_word["start"] = word["start"]
                        conll_word["end"] = word["start"] + .8*(word["end"]-word["start"])
                        conll_word["probability"] = word["probability"]
                        
                        word_indx += 1
                        conll_word = conll_words[word_indx]
                        conll_word.pop("id",None)
                        sentence["words"].insert(word_id+1,conll_word)
                        conll_word["start"] = word["start"] + .8*(word["end"]-word["start"])
                        conll_word["end"] = word["end"]
                        conll_word["probability"] = word["probability"]
                        skip_next = True
                    elif skip_next:
                        word_indx -= 1
                        skip_next = False
                        
                    elif word["word"] == conll_word["word"]:
                        sentence["words"][word_id] = conll_word
                        conll_word["start"] = word["start"]
                        conll_word["end"] = word["end"]
                        conll_word["probability"] = word["probability"]
                    else:
                        raise Exception("Error parsing! required fix")
                    conll_word.pop("id",None)
                    word_indx += 1
            doc_id = None
        return doc_id, timed_transcript



class TextCleaner:

    _instance=None
    
    def __new__(cls):
        if cls._instance is None:
            cls.pattern = re.compile('[^a-zA-Z\d &-]')
            cls._instance = super(TextCleaner, cls).__new__(cls)
        return cls._instance
    
    def clean_text(self,text:str):
        return ' '.join(self.pattern.sub(' ',text).split()).lower()



from enum import Enum, auto

class ComparisonMethods(Enum):
    TXT_SIM_RATIO=auto()
    TXT_MISS_RATIO=auto()
    MEANINGFUL_WORDS_COUNT=auto()
    CHARS_COMMON_DISTRIB=auto()
    FUZZY_PARTIAL_RATIO=auto()
    LEMMAS_CONTAINED_RATIO=auto()
    

class TextSimilarityClassifier:
    """
    Text diffences classifier\n
    Using various methods can check if some text is part of other text\n
    or if two texts are similar
    """

    def __init__(self,comp_methods:List[int] | str | None = None,
                 max_removed_chars_over_total_diff:float=0.1,
                 min_common_chars_ratio:float=0.8,
                 max_removed_chars_over_txt:float=0.3,
                 max_added_chars_over_total:float= 0.2,
                 fuzzy_ratio_thresh:float=0.9,
                 cosine_sim_chars_distrib_thresh:float=0.95,
                 extra_lemmas_ratio_thresh:float=0.1,
                 time_tol = 5,
                 language:str="en" ) -> None:
        self._CV = CountVectorizer()
        self._txt_cleaner:TextCleaner = TextCleaner()
        if comp_methods is None:
            self._comp_methods = {method for method in list(ComparisonMethods)[:2]}
        elif comp_methods == "all":
            self._comp_methods = {method for method in list(ComparisonMethods)}
        else:
            self.set_comparison_methods(comp_methods)
        self.removed_chars_diff_ratio_thresh = max_removed_chars_over_total_diff
        self.added_chars_diff_ratio_thresh = max_added_chars_over_total
        self.common_chars_txt_ratio_thresh = min_common_chars_ratio
        self.removed_chars_txt_ratio_thresh = max_removed_chars_over_txt
        self.time_tol = time_tol
        self.cosine_sim_thresh = cosine_sim_chars_distrib_thresh
        self.fuzz_ratio_thresh = fuzzy_ratio_thresh
        self.extra_lemmas_ratio_thresh = extra_lemmas_ratio_thresh
        self.language = language
        #self._noise_classifier = pipeline('text-classification', model='textattack/bert-base-uncased-imdb')


    def is_partially_in(self,TFT1:"VideoSlide",TFT2:"VideoSlide") -> bool:
        '''
        Finds if text1 is partial text of text2
        texts are cleaned of all non alphanumeric characters.

        Then are compared in terms of one or more predefined methods: 
            - diffs percentage of all the merged texts with respect to 3 thresholds:\n
                removed chars from txt1 with respect to txt2 over the total diff\n
                common chars of both texts\n
                added chars in txt1 to reach txt2 over the total diff\n
            - most rich and meaningful text\n
            - removed chars percentage over the string

        
        Order is based on performance maximization
            
        ### No checks are performed on input

        -------

        Returns
        -------
        True if text1 is part of the text2

        '''
        #comp_methods = self._comp_methods
        checks:list[bool] = [bool(TFT1) and bool(TFT2)]
        text1 = TFT1.get_full_text()
        text2 = TFT2.get_full_text()
        checks.append(bool(text1) and bool(text2))
        
        comp_methods = self._comp_methods
        removed_chars_count = None
        cleaner = self._txt_cleaner
        text1_cleaned = cleaner.clean_text(text1)
        text2_cleaned = cleaner.clean_text(text2)
        checks.append(len(text1_cleaned) < len(text2_cleaned))
        
        if not all(checks):
            return False
        
        if ComparisonMethods.FUZZY_PARTIAL_RATIO in comp_methods:
            fuzz_ratio = partial_ratio(text1_cleaned, text2_cleaned)/100
            checks.append(fuzz_ratio > self.fuzz_ratio_thresh)

        if not all(checks):
            return False
    
        if ComparisonMethods.TXT_SIM_RATIO in comp_methods:
            counter = Counter([change[0] for change in ndiff(text1_cleaned,text2_cleaned)])
            removed_chars_count = 0 if not '-' in counter.keys() else counter['-']
            common_chars_count = 0 if not ' ' in counter.keys() else counter[' ']
            added_chars_count = 0 if not '+' in counter.keys() else counter['+']
            diffs_len = removed_chars_count+common_chars_count+added_chars_count
            text1_len = len(text1_cleaned)
            checks.append(  diffs_len > 0 and 
                            text1_len > 0 and 
                            removed_chars_count/diffs_len < self.removed_chars_diff_ratio_thresh and 
                            common_chars_count/text1_len > self.common_chars_txt_ratio_thresh  and
                            added_chars_count/diffs_len < self.added_chars_diff_ratio_thresh)
        
        if not all(checks):
            return False
                
        if ComparisonMethods.MEANINGFUL_WORDS_COUNT in comp_methods:
            all_words = self._words
            txt1_split = text1_cleaned.split(); txt2_split = text2_cleaned.split()
            len_txt1_split = len(txt1_split); len_txt2_split = len(txt2_split) 
            checks.append(( 0 < len_txt1_split <= len_txt2_split 
                                and ( len([word for word in txt1_split if word in all_words]) / len(txt1_split) 
                                        <= 
                                      len([word for word in txt2_split if word in all_words]) / len(txt2_split)) ) 
                            or len_txt1_split <= len_txt2_split )
        
        if not all(checks):
            return False
        
        if ComparisonMethods.TXT_MISS_RATIO in comp_methods:
            if removed_chars_count is None:
                text1_cleaned = cleaner.clean_text(text1); text2_cleaned = cleaner.clean_text(text2)
                counter = Counter([change[0] for change in ndiff(text1_cleaned,text2_cleaned)])
                removed_chars_count = 0 if not '-' in counter.keys() else counter['-']
                added_chars_count = 0 if not '+' in counter.keys() else counter['+']
                text1_len = len(text1_cleaned)
            checks.append(  text1_len > 0 and 
                            removed_chars_count/len(text1_cleaned) < self.removed_chars_txt_ratio_thresh)
        
        if not all(checks):
            return False
        
        if ComparisonMethods.CHARS_COMMON_DISTRIB in comp_methods:
            counts1 = Counter(text1_cleaned); counts2 = Counter(text2_cleaned)
            counts1.pop(" ",0); counts2.pop(" ",0)
            for key in set(counts1.keys()).union(set(counts2.keys())):
                if key not in counts1:
                    counts1[key] = 0
                if key not in counts2:
                    counts2[key] = 0

            cosine_sim = cosine_similarity([np.array(list(counts1[key] for key in sorted(counts1)))], 
                                           [np.array(list(counts2[key] for key in sorted(counts2)))])[0][0]
            
            checks.append(cosine_sim > self.cosine_sim_thresh or (ComparisonMethods.FUZZY_PARTIAL_RATIO in comp_methods and fuzz_ratio > 0.95))
        
        if not all(checks):
            return False
        
        if ComparisonMethods.LEMMAS_CONTAINED_RATIO in comp_methods:
            lang = self.language
            lemmas1:list = NLPSingleton().lemmatize(text1_cleaned,lang)
            lemmas2:list = NLPSingleton().lemmatize(text2_cleaned,lang)
            lemmas_diff = [lemma for lemma in lemmas2 if not lemma in lemmas1 or lemmas1.remove(lemma)]
            checks.append(len(lemmas_diff)/len(lemmas1) <= self.extra_lemmas_ratio_thresh)
        
        return all(checks)


    def are_cosine_similar(self,text1:str,text2:str,confidence:float=0.9) -> bool:
        '''
        Determine if two texts are cosine similar.

        This is evaluated in terms of words mapped to a unique number\n
        ### May collapse when performed on texts with num words = 1 vs 2 or 2 vs 1

        -----------

        Parameters:
        ----------
            - text1 (str): The first text to compare.
            - text2 (str): The second text to compare.
            - confidence (float, optional): The minimum confidence level required to consider
                the texts similar. Defaults to 0.9

        Returns:
        --------
            bool: True if the texts are cosine similar with a confidence level above
                `confidence`, False otherwise.  

        '''
        cleaner = self._txt_cleaner
        text1_clean_split, text2_clean_split = cleaner.clean_text(text1).split(), cleaner.clean_text(text2).split()
        len_split1, len_split2 = len(text1_clean_split), len(text2_clean_split)
        max_len = max(len_split1,len_split2)
        if max_len > 0 and min(len_split1, len_split2) == 0:
            return False
        words_set = set(text1_clean_split+text2_clean_split)
        values = list(range(1,len(words_set)+1))
        words_dict = dict(zip(words_set,values))
        text1_vectorized = list(map(lambda key: words_dict[key], text1_clean_split))
        text2_vectorized = list(map(lambda key: words_dict[key], text2_clean_split))
        texts_vectorized = empty((2,max_len),dtype=int)
        texts_vectorized[0,:len_split1] = text1_vectorized; texts_vectorized[0,len_split1:] = 0
        texts_vectorized[1,:len_split2] = text2_vectorized; texts_vectorized[1,len_split2:] = 0
        return sum(prod(texts_vectorized,axis=0))/prod(norm(texts_vectorized,axis=1)) > confidence


    def is_exactly_in_txt_version(self,text1:str,text2:str,chars_tol_percentage:float=0.9):
        '''
        Checks whether there's the same string text1 in text2, within a reasonable margin of error\n
        Based on perfect match from left to right so if text1 has char in second position different\n
        from what is in text2, the match is insignificant\n\n

        TODO can be improved with match in reversed string but might get expensive
        '''
        cleaner = self._txt_cleaner
        clean_text1 = cleaner.clean_text(text1)
        res = re.search(clean_text1,cleaner.clean_text(text2))
        return res is not None and len(res.group(0))/len(clean_text1) > chars_tol_percentage

    def subtract_common_text(self,text1:str,text2:str):
        '''
        Performs text1 - text2 where they are in common
        
        Can be improved by using ndiff alg but for now keep it simple
        '''
        return self._txt_cleaner.clean_text(text1.replace(text2,'').lstrip())

    def set_comparison_methods(self,methods:List[int]):
        self._comp_methods = set(methods)


class VideoSlide:
    """
    Representation of a Slide in a video
    A slide made of:
        - _full_text: full string built for comparison purposes (not to be changed)
        - _framed_sentences: list of portions of a full_text composed field and their absolute location on the screen 
        - start_end_frames: list of tuples of num start and num end frames of this text
        
    """
    _full_text: str
    _framed_sentences: List[Tuple[Tuple[int,int],Tuple[int,int,int,int]]]
    _bounding_box: Tuple[int,int,int,int]
    start_end_frames: List[Tuple[(int,int)]]
    txt_sim_class = TextSimilarityClassifier()

    def __init__(self,framed_sentences:List[Tuple[str,Tuple[int,int,int,int]]],startend_frames:List[Tuple[(int,int)]]) -> None:
        self.start_end_frames = [startend_frames]
        full_text = ''
        converted_framed_sentence:List[Tuple[Tuple[int,int],Tuple[int,int,int,int]]] = []
        curr_start = 0
        min_bb = [0,0,0,0]
        for sentence,bb in framed_sentences:
            full_text += sentence
            len_sent = len(sentence)
            converted_framed_sentence.append(((curr_start,curr_start+len_sent),bb))
            curr_start += len_sent
            min_bb[0] = np.minimum(min_bb[0], bb[0])
            min_bb[1] = np.minimum(min_bb[1], bb[1])
            min_bb[2] = np.maximum(min_bb[2], bb[2])
            min_bb[3] = np.maximum(min_bb[3], bb[3])
            
        self._bounding_box = np.array(min_bb)
        self._framed_sentences = converted_framed_sentence
        self._full_text = full_text
 
    def copy(self):
        tft_copy = VideoSlide(framed_sentences=None,start_end_frames=self.start_end_frames)
        tft_copy._framed_sentences=self._framed_sentences
        tft_copy._full_text = self._full_text
        return tft_copy
    
    def merge_frames(self, other_slide:"VideoSlide") -> None:
        '''
        extend this element's start_end frames with the other list in a sorted way
        '''
        this_startend_frames = self.start_end_frames
        for other_start_end_elem in other_slide.start_end_frames:
            if not other_start_end_elem in this_startend_frames:
                insort_left(self.start_end_frames,other_start_end_elem)

    def get_full_text(self):
        return self._full_text
    
    def get_split_text(self):
        '''
        returns the full text splitted by new lines without removing them
        '''
        return self._full_text.split("(?<=\n)")

    def get_framed_sentences(self):
        '''
        converts the full text string into split segments of text with their respective bounding boxes
        '''
        full_text = self._full_text
        return [((full_text[start_char_pos:end_char_pos]),bb) for (start_char_pos,end_char_pos),bb in self._framed_sentences]

    def merge_adjacent_startend_frames(self,max_dist:int=15) -> 'VideoSlide':
        '''
        Merges this object adjacent (within a max_dist) frame times
        '''
        start_end_frames = self.start_end_frames
        merged_start_end_frames = []
        curr_start,curr_end = start_end_frames[0]
        for new_start,new_end in start_end_frames:
            if new_start-curr_end <= max_dist:
                curr_end = max(curr_end,new_end)
            else:
                merged_start_end_frames.append((curr_start,curr_end))
                curr_start = new_start
                curr_end = new_end
        merged_start_end_frames.append((curr_start,curr_end))
        self.start_end_frames = merged_start_end_frames
        return self
    
    def __iter__(self):
        yield "text", self._full_text
        yield "full_bounding_box", self._bounding_box.tolist()
        yield "sent_indxs_and_bb", self._framed_sentences
    
    def __eq__(self, other: "VideoSlide") -> bool:
        
        if not self.txt_sim_class.are_cosine_similar(self._full_text, other._full_text, confidence=0.8):
            return False

        this_bbs = self._bounding_box
        other_bbs = other._bounding_box
        return (this_bbs - 10 <= other_bbs).all() and (other_bbs <= this_bbs + 10).all()

    def __lt__(self, other:'VideoSlide'):
        return self.start_end_frames[0][0] < other.start_end_frames[0][0]
    
    def __repr__(self) -> str:
        return 'TFT(txt={0}, window_time={1}, bbs={2})'.format(
            repr(self._full_text),repr(self.start_end_frames),repr(self._bounding_box))
  

def lemmatize(lemmas):
    concepts_lemmatized = []

    lemmatizer = WordNetLemmatizer()

    for concept in lemmas:
        lemmatized = ""

        for word in concept.split(" "):
            lemmatized += lemmatizer.lemmatize(word.lower()) + " "

        lemmatized = lemmatized.rstrip()

        if lemmatized not in concepts_lemmatized:
            concepts_lemmatized.append(lemmatized)

    return concepts_lemmatized


def get_real_keywords(video_id, annotator_id=None):
    graphs = db_mongo.get_graphs_info(video_id)
    if graphs is None:
        video_doc = db_mongo.get_video_data(video_id)
        return video_doc['title'], [term["term"] for term in video_doc['transcript_data']["terms"]]

    indx_annotator = 0
    if annotator_id is not None:
        annotators = graphs['annotators']
        for i,annot in enumerate(annotators):
            if annot['id']==annotator_id:
                indx_annotator = i
                break
    annotator_id = graphs["annotators"][indx_annotator]['id']
    #print("Annotator: ", graphs["annotators"][0]["name"])
    concept_map_annotator = db_mongo.get_concept_map(annotator_id, video_id)
    definitions = db_mongo.get_definitions(annotator_id, video_id)
    keywords = []

    for d in definitions:
        if d["concept"] not in keywords:
            keywords.append(d["concept"])

    for rel in concept_map_annotator:
        if rel["prerequisite"] not in keywords:
            keywords.append(rel["prerequisite"])
        if rel["target"] not in keywords:
            keywords.append(rel["target"])

    return graphs["title"], keywords
    

def get_timed_sentences(subtitles, sentences: List['str']):
    '''For each sentence, add its start and end time obtained from the subtitles'''
    # Compute the number of words for each sentence and for each sub
    num_words_sentence = []
    num_words_sub = []

    for s in sentences:
        num_words_sentence.append(len(s.split()))
    for s in subtitles:
        num_words_sub.append(len(s["text"].split()))

    # Get start and end time of the punctuated sentences from the subtitles
    timed_sentences = [{"text": sentences[0], "start": subtitles[0]["start"]}]

    i = 0
    j = 0

    while i < len(num_words_sentence) and j < len(num_words_sub):
        if num_words_sentence[i] > num_words_sub[j]:
            num_words_sentence[i] = num_words_sentence[i] - num_words_sub[j]
            j += 1  # qui manca controllo su j, ma non serve

        elif num_words_sentence[i] < num_words_sub[j]:
            timed_sentences[i]["end"] = subtitles[j]["end"]
            num_words_sub[j] = num_words_sub[j] - num_words_sentence[i]
            i += 1
            if i < len(num_words_sentence) and j < len(num_words_sub):
                timed_sentences.append({"text": sentences[i], "start": subtitles[j]["start"]})
        else:
            timed_sentences[i]["end"] = subtitles[j]["end"]
            num_words_sentence[i] = 0
            num_words_sub[j] = 0
            i += 1
            j += 1
            if i < len(num_words_sentence) and j < len(num_words_sub):
                timed_sentences.append({"text": sentences[i], "start": subtitles[j]["start"]})

    timed_sentences[len(timed_sentences)-1]["end"] = subtitles[len(subtitles)-1]["end"]

    """
    for i in range(0, len(timed_sentences)):

        start_to_fix = []

        j = i
        tot_length = timed_sentences[j]["start"]

        while j+1 < len(timed_sentences) and timed_sentences[j]["start"] == timed_sentences[j+1]["start"]:
            start_to_fix.append(j)
            if j+1 not in start_to_fix:
                start_to_fix.append(j+1)
                tot_length += len(timed_sentences[j]["text"])
            j+=1

        for k in range(1,len(start_to_fix)):
            time_to_add = len(timed_sentences[k-1]["text"])/tot_length
            timed_sentences[k - 1]["end"] -= time_to_add
            timed_sentences[k]["start"] = timed_sentences[k - 1]["end"]
    """
    return timed_sentences

def extract_keywords_LEGACY(text:str,maxWords=3,minFrequency=1):
    r = Rake(max_length=maxWords)
    r.extract_keywords_from_text(text)
    ranks_and_keywords = r.get_ranked_phrases_with_scores()
    concepts_stored = set()
    nlp = NLPSingleton()
    words_lemmas = {}
    for i, (score,term) in enumerate(ranks_and_keywords):
        lemma = " ".join([token.lemma_ for token in nlp.lemmatize(term,"en")])
        if not lemma in words_lemmas.keys():
            words_lemmas[lemma] = True
        else:
            ranks_and_keywords[i] = (score,lemma)

    counts = dict(Counter(list(map(lambda x: x[1], ranks_and_keywords))))
    out_concepts = [{"term":key, "frequency":value, "domain_relevance":100} for key, value in counts.items() if value > minFrequency]
    for concept in out_concepts:
        concepts_stored.add(concept["term"])
    for (score, key) in ranks_and_keywords[:15]:
        if key not in concepts_stored:
            out_concepts.append({"term":key, "frequency":counts[key], "domain_relevance":100})
            concepts_stored.add(key)
            
    return DataFrame(out_concepts)

if __name__ == '__main__':
    from segmentation import VideoAnalyzer
    VideoAnalyzer("https://www.youtube.com/watch?v=MMzdKTtUIFM").analyze_transcript()
    #WhisperToPosTagged("en").request_tagged_transcript("MMzdKTtUIFM",data["transcript_data"]["text"])
    pass