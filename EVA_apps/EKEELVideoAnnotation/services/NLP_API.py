"""
This module provides interfaces for interacting with various NLP APIs, including the Italian NLP API and the CoNLL API.

Classes
-------
ItaliaNLAPI
    Interface for interacting with the Italian NLP API.
ConllAPISingleton
    Singleton class for interacting with the CoNLL API.

Attributes
----------
None

Methods
-------
None
"""

import requests
import time
from pandas import DataFrame
from text_processor.locales import Locale, FORMAT_FULL


class ItaliaNLAPI:
    """
    Interface for interacting with the Italian NLP API.

    Attributes
    ----------
    _instance : ItaliaNLAPI
        Singleton instance of the class.
    _server_address : str
        Address of the Italian NLP API server.
    _max_term_len : int
        Maximum length of terms.
    _term_extraction_configs : dict
        Configuration for term extraction.

    Methods
    -------
    upload_document(text, language, async_call=True)
        Uploads a document to the server.
    wait_for_named_entity_tag(doc_id)
        Waits for named entity tagging to complete.
    wait_for_pos_tagging(doc_id)
        Waits for POS tagging to complete.
    execute_term_extraction(doc_id, configuration=None, apply_contrast=True, n_try=60) -> DataFrame
        Executes term extraction on the document.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ItaliaNLAPI, cls).__new__(cls)
            cls._server_address = "http://api.italianlp.it"
            cls._max_term_len = 5
            cls._term_extraction_configs = {
                "name-misc-name": {
                    'pos_start_term': ['c:S', 'c:A'],
                    'pos_internal_term': ['c:E', 'c:A', 'f:S', 'c:B'],
                    'pos_end_term': ['c:S', 'c:A'],
                    'max_length_term': 3
                },
                "alzetta-conf": {
                    'pos_start_term': ['c:S'],
                    'pos_internal_term': ['c:A', 'c:E', 'c:S', 'c:EA', 'c:SP'],
                    'pos_end_term': ['c:A', 'c:S', 'c:SP'],
                    'statistical_threshold_single': 30,
                    'statistical_threshold_multi': 10000,
                    'statistical_frequency_threshold': 1,
                    'max_length_term': 5,
                    'apply_contrast': True
                },
                "alzetta-conf-no-contrast": {
                    'pos_start_term': ['c:S'],
                    'pos_internal_term': ['c:A', 'c:E', 'c:S', 'c:EA', 'c:SP'],
                    'pos_end_term': ['c:A', 'c:S', 'c:SP'],
                    'statistical_threshold_single': 30,
                    'statistical_threshold_multi': 10000,
                    'statistical_frequency_threshold': 1,
                    'max_length_term': 5,
                    'apply_contrast': False
                }
            }
        return cls._instance

    def upload_document(self, text: str, language: str, async_call: bool = True):
        """
        Uploads a document to the server.

        Parameters
        ----------
        text : str
            Text of the document to upload.
        language : str
            Language of the document.
        async_call : bool, optional
            Whether to make the API call asynchronously, by default True.

        Returns
        -------
        str
            ID of the uploaded document.
        """
        r = requests.post(self._server_address + '/documents/',
                          data={'text': text,
                                'lang': language.upper(),
                                'async': async_call})

        doc_id = r.json()['id']
        return doc_id
    
    def wait_for_named_entity_tag(self, doc_id):
        """
        Waits for named entity tagging to complete.

        Parameters
        ----------
        doc_id : str
            ID of the document.
        """
        api_res = {'postagging_executed': False, 'sentences': {'next': False, 'data': []}}
        while not api_res['postagging_executed'] or api_res['sentences']['next']:
            r = requests.get(self._server_address + '/documents/action/named_entity/%s' % (doc_id))
            api_res = r.json()
    

    def wait_for_pos_tagging(self, doc_id):
        """
        Waits for POS tagging to complete.

        Parameters
        ----------
        doc_id : str
            ID of the document.
        """
        page = 1
        api_res = {'postagging_executed': False}
        while not api_res['postagging_executed']:
            r = requests.get(self._server_address + '/documents/details/%s?page=%s' % (doc_id, page))
            api_res = r.json()

            if api_res['postagging_executed']:
                sentences = api_res["sentences"]["data"]

    def execute_term_extraction(self, doc_id, configuration=None, apply_contrast=True, n_try=60) -> DataFrame:
        """
        Executes term extraction on the document.

        Parameters
        ----------
        doc_id : str
            ID of the document.
        configuration : dict, optional
            Configuration for term extraction, by default None.
        apply_contrast : bool, optional
            Whether to apply contrast in term extraction, by default True.
        n_try : int, optional
            Number of attempts to check for term extraction completion, by default 60.

        Returns
        -------
        DataFrame
            DataFrame containing extracted terms.
        """
        if configuration is None:
            configuration = self._term_extraction_configs['alzetta-conf'+"-no-contrast"*(not apply_contrast)]
        
        url = self._server_address + '/documents/term_extraction'
        term_extraction_id = requests.post(url=url,
                                 json={'doc_ids': [doc_id],
                                       'configuration': configuration}).json()['id']
        for _ in range(n_try):
            res = requests.get(url=url,params={'id': term_extraction_id}).json()
            if res['status'] == "OK":
                if len(res["terms"]) == 0:
                    print("With this config ItaliaNLP.term_extraction() has not found anything")
                break
            elif res["status"] == "IN_PROGRESS":
                print(f"Been waiting term extraction for {(_+1)*10} seconds...")
            time.sleep(10)
        else:
            raise Exception(f"ItalianNLP API hasn't sent the requested data in {n_try*5} seconds")
        
        terms = DataFrame(res['terms'])
        if terms.empty:
            terms = DataFrame(columns=["term", "domain_relevance", "frequency"])
        terms['word_count'] = terms['term'].apply(lambda x: len(x.split()))
        return terms.sort_values(by='word_count').drop(columns=['word_count'])

T2K = ItaliaNLAPI()


class ConllAPISingleton:
    """
    Singleton class for interacting with the CoNLL API.

    Attributes
    ----------
    _instance : ConllAPISingleton
        Singleton instance of the class.
    _models : dict[str, str]
        Dictionary mapping languages to their best performing models.

    Methods
    -------
    __new__(cls, *args, **kwargs)
        Creates a new instance of the class if one does not already exist.
    """
    _instance = None
    _models:'dict[str,str]'

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ConllAPISingleton, cls).__new__(cls)

            # Get all the models
            conll_models = sorted(list(requests.post('http://lindat.mff.cuni.cz/services/udpipe/api/models').json()['models'].keys()))

            langs = sorted(list(Locale().get_supported_languages(FORMAT_FULL)))
            target_langs_models = {lang:[] for lang in langs}

            # Selects only those that are based on supported languages
            for model_name in conll_models:
                model_name_lang = model_name.split("-")[0]
                if model_name_lang < langs[0]:
                    pass
                elif any(model_name_lang == lang for lang in langs):
                    for lang in langs:
                        if lang == model_name_lang:
                            target_langs_models[lang].append(model_name)
                elif model_name_lang > langs[-1]:
                    break
            
            # Filters by best performing model and most recent version
            for lang, models_names in target_langs_models.items():
                for model_name in models_names:
                    _,train_kind,_,version,_ = model_name.split('-')
                    major_version, minor_version = map(int, version.split('.'))
                    if train_kind in ["ewt", "partut"] and \
                            (major_version > 2 or (major_version == 2 and minor_version >= 12)):
                        target_langs_models[lang] = model_name
                        break
            
            # Maps to pt1 for compliance
            for lang in langs:
                target_langs_models[Locale().get_pt1_from_full(lang)] = target_langs_models[lang]
                target_langs_models.pop(lang)
            cls._models = target_langs_models
        return cls._instance

CONLL = ConllAPISingleton() 

if __name__ == '__main__':
    ItaliaNLAPI().execute_term_extraction(1750)