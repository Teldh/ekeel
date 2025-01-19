import requests, re
from conllu import parse
import string

from database.mongo import insert_conll_MongoDB, get_conll
from services.NLP_API import CONLL

def conll_gen(video_id:str,string_text:str, language:str):
    """
    Generate CoNLL-U format parsing for input text.

    Parameters
    ----------
    video_id : str
        Identifier for the video
    string_text : str
        Input text to be parsed
    language : str
        Language code for the text

    Returns
    -------
    list
        Parsed CoNLL-U sentences
    """
    # checks whether the conll is already on server
    conll = get_conll(video_id)
    
    if conll is not None:
        return parse(conll)
    
    # requests the conll from an api
    # aggiunto ita
    #files = {
    #    'data': text,
    #    'model': (None, 'english-ewt-ud-2.4-190531'),
    #    'tokenizer': (None, ''),
    #    'tagger': (None, ''),
    #    'parser': (None, ''),
    #}
    files = {
        'data': string_text,
        'model': (None, CONLL._models[language]),
        'tokenizer': (None, ''),
        'tagger': (None, ''),
        'parser': (None, ''),
    }
    r = requests.post('http://lindat.mff.cuni.cz/services/udpipe/api/process', files=files)
    re = r.json()

    # json da salvare
    conll = re['result']
    insert_conll_MongoDB({'video_id':video_id, 'conll':conll})
    return parse(conll)
    

# get text from a conll in the db
def get_text(video_id:str, return_conll:bool=False):
    """
    Retrieve text from stored CoNLL-U format.

    Parameters
    ----------
    video_id : str
        Identifier for the video
    return_conll : bool, default=False
        If True, returns both text and CoNLL-U format

    Returns
    -------
    str or tuple
        Text string if return_conll=False
        Tuple of (text, conll) if return_conll=True
    None
        If no CoNLL data found for video_id
    """
    conll = get_conll(video_id)
    
    if conll is None:
        return None
    
    parsed = parse(conll)
    text = " ".join([sentence.metadata['text'] for sentence in parsed])
    if return_conll:
        return text, conll
    return text

def html_interactable_transcript_legacy(subtitles:list, conll_sentences:list, language:str):
    """
    Create an interactive HTML transcript with word-level annotations.

    Parameters
    ----------
    subtitles : list
        List of subtitle dictionaries with text and timing
    conll_sentences : list
        Parsed CoNLL-U sentences
    language : str
        Language code for the text

    Returns
    -------
    tuple
        (lemmatized_subtitles, all_lemmas) where:
        - lemmatized_subtitles: list of dicts with HTML-formatted text
        - all_lemmas: list of unique lemmas found in text
    """
    from text_processor.words import SemanticText
    #lemmatizer = WordNetLemmatizer()
    sem_text = SemanticText("",language)

    sent_id = 0
    word_id = 0
    word_counter = 0

    all_lemmas = []
    lemmatized_subtitles = []

    for sub in subtitles:
        sent = {"text": ""}
        text:str = sub["text"]
        text = text.replace("\n", " ").replace("’", " ’").replace("'", " '")
        in_phrase_word_indx = 0


        # # aggiungo uno spazio vuoto prima e dopo la punteggiatura
        # text = re.sub('([.,!?():])', r' \1 ', text)
        # text = re.sub('\s{2,}', ' ', text)
        text = text.replace("/", " / ")#.replace("-", " - ")
        text = text.replace("'", " '").replace("’", " ’").replace("”", " ” ").replace("“", " “ ")
        if language == "it":
            text = text.replace("l '","l' ")
        #text_words = text.split(" ")
        text_words = re.split(' |-', text)
        #print(text_words)
        for w in text_words:
            sentence_finished = False
            if w != '':

                if w not in [".",":","?","!",",",";","/","“","'",'"',"”"]:

                    text_word = w.lower().translate(str.maketrans('', '', string.punctuation))\
                        .replace('”', '').replace("“", "").replace('…', '')

                    # there is a bug where sent_id value is over the len of conll_senteces
                    # i add this if to solve it
                    if sent_id < len(conll_sentences):
                        conll_words = conll_sentences[sent_id].filter(upos=lambda x: x != "PUNCT")

                    for i, c in enumerate(conll_words):
                        if "-" in c["form"]:
                            conll_words.insert(i, c.copy())
                            conll_words[i]["form"] = conll_words[i]["form"].split("-")[0]
                            conll_words[i+1]["form"] = conll_words[i+1]["form"].split("-")[1]

                    for i in range(word_counter, len(conll_words)):

                        conll_word = str(conll_words[i]["form"]).lower().translate(str.maketrans('', '', string.punctuation))
                        #print( conll_word, text_word)

                        if text_word == conll_word:
                            word_id = conll_words[i]["id"]
                            word_counter += 1

                            if conll_words[i]["id"] == conll_words[-1]["id"]:
                                sentence_finished = True
                            break

                if w in ["!", "?", "."]:
                    s = sent_id
                else:
                    s = sent_id + 1

                #print(s)
                toLemmatize = w.lower()
                if toLemmatize[-1] in ["?", ".", "!", ";", ","]:
                    toLemmatize = toLemmatize[:-1]
                sem_text.set_text(toLemmatize)
                lemma = sem_text.lemmatize()[0]
                #lemma = lemmatizer.lemmatize(toLemmatize)
                #print(toLemmatize, lemma)
                #print(sub)
                
                sent["text"] += f'<span lemma="{lemma}" sent_id="{str(s)}" word_id="{str(word_id)}" start_time="{sub["start"]}" end_time="{sub["end"]}" >' + w + '</span> '


                if lemma not in all_lemmas:
                    all_lemmas.append(lemma)

                if sentence_finished:
                    sent_id += 1
                    word_id = 0
                    word_counter = 0
                in_phrase_word_indx += 1

        lemmatized_subtitles.append(sent)

    return lemmatized_subtitles, all_lemmas
    
def html_interactable_transcript_word_level(sentences:list):
    """
    Create word-level interactive HTML transcript with detailed linguistic annotations.

    Parameters
    ----------
    sentences : list
        List of sentence dictionaries containing word information

    Returns
    -------
    list
        List of dictionaries containing HTML-formatted sentences with
        linguistic annotations (lemma, POS, gender, number) and timing
        information for each word

    Notes
    -----
    Special handling implemented for:\n
    - Articulated prepositions with apostrophe\n
    - Verbs with cyclic pronouns\n
    - Words with punctuation\n
    - Website URLs
    """
    html_lemmatized_sents = []
    for sent_id, sentence in enumerate(sentences):
        html_sent = []
        for word_id, word in enumerate(sentence["words"]):
            word_text = word["word"]
            html_sent += [f'<span lemma="{word["lemma"]}"' +
                                f' sent_id="{str(sent_id)}"' +
                                f' word_id="{str(word_id)}"' +
                                f' start_time="{word["start"]}"' +
                                f' end_time="{word["end"]}"' +
                                f' cpos="{word["cpos"]}"' +
                                f' pos="{word["pos"]}"' +
                                f' gen="{word["gen"]}"' +
                                f' num="{word["num"]}" >' +
                                f'{word_text}' +
                            '</span>', " "]
            # if articulated preposition with apostrophe eg. "dell'" 
            # or verb with after a cyclic pronoun eg. "specchiar-si" 
            # or word that has a punctuation mark after
            # or websites (saved as "www.google.com" and words ["www",".google",".com"])
            # don't add space between
            if  word["word"].endswith("'") or \
                (word["cpos"] == "PUNCT" and word["word"] != ",") or \
                word["cpos"] == "NUM" or \
                (word_id + 1 < len(sentence["words"]) and ( sentence["words"][word_id+1]["cpos"] == "X" or \
                                                            sentence["words"][word_id+1]["pos"] in ["FC","FF","FS"] or \
                                                            sentence["words"][word_id+1]["word"].startswith(".") or \
                                                            sentence["words"][word_id+1]["word"].startswith("'") or \
                                                            sentence["words"][word_id+1]["cpos"] == "PUNCT" or \
                                                            (word["cpos"] == "V"  and sentence["words"][word_id+1]["pos"] == "PC"))):
               html_sent.pop()
        html_lemmatized_sents.append({"text": "".join(html_sent)})
    return html_lemmatized_sents

if __name__ == '__main__':
    from media.segmentation import VideoAnalyzer
    from text_processor.words import SemanticText
    vid = VideoAnalyzer("https://www.youtube.com/watch?v=MMzdKTtUIFM")
    connl = conll_gen("MMzdKTtUIFM", SemanticText(" ".join(timed_sentence["text"] for timed_sentence in vid.data["transcript_data"]["text"] if not "[" in timed_sentence['text']), "en"))
    print(html_interactable_transcript_word_level(vid.data["transcript_data"]["text"]))
    #print(conll_gen("L94FfnqrJUk",SemanticText("Hello my name is Ekeel","en")))