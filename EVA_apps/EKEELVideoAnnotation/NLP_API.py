import requests
import time
import json
from pandas import DataFrame
from words import SemanticText


class ItaliaNLAPI():

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ItaliaNLAPI, cls).__new__(cls)
            cls._server_address = "http://api.italianlp.it"
            cls._max_term_len = 5
            # TODO ask "f" (fine) option for the start terms seems not to work
            cls._term_extraction_configs = { "name-misc-name": 
                                                {   'pos_start_term':   ['c:S','c:A'],              # begin with a fine common name (diritto, legge) or an adjective (interdisciplinare, aggregato)
                                                    'pos_internal_term':['c:E','c:A','f:S','c:B'],  # continue with a preposition (del, da, su, verso) and other names
                                                    'pos_end_term':     ['c:S','c:A'],              # end with a fine common name 
                                                    'max_length_term':  3 
                                                }
                                           }

        return cls._instance

    def upload_document(self, text:str, language:str, async_call:bool=True):
        r = requests.post(self._server_address + '/documents/',
                          data={'text': text,  # si carica il documento nel server
                                'lang': language.upper(),
                                'async': async_call})  # indica se la chiamata alle api viene fatta in modo sincrono o asincrono

        doc_id = r.json()['id']  # questo è l'id del documento nel server

        return doc_id
    
    def wait_for_named_entity_tag(self,doc_id):
        api_res = {'postagging_executed': False, 'sentences': {'next': False, 'data': []}}
        while not api_res['postagging_executed'] or api_res['sentences']['next']:
            r = requests.get(self._server_address + '/documents/action/named_entity/%s' % (doc_id))
            api_res = r.json()
    

    def wait_for_pos_tagging(self,doc_id):
        page = 1
        # inizializzazione dummy della risposta del server per poter scrivere la condizione del while
        api_res = {'postagging_executed': False, 'sentences': {'next': False, 'data': []}}
        while not api_res['postagging_executed'] or api_res['sentences']['next']:
            r = requests.get(self._server_address + '/documents/details/%s?page=%s' % (doc_id, page))
            api_res = r.json()

            if not api_res['postagging_executed']:
                print('Waiting for pos tagging...')
                time.sleep(5)
                continue
            else:
                from pprint import pprint
                j = json.dumps(api_res, indent=4)
                with open("output.json","w") as f:
                    print(j, file=f)
                #pprint(api_res)

            #if api_res['sentences']['next']:
            #    page += 1

    
    def execute_term_extraction(self, doc_id, configuration=None,n_try=10) -> DataFrame:
        if configuration is None:
            configuration = self._term_extraction_configs['name-misc-name']
        
        url = self._server_address + '/documents/term_extraction'
        term_extraction_id = requests.post(url=url,
                                 json={'doc_ids': [doc_id],
                                       'configuration': configuration}).json()['id']
        for _ in range(n_try):
            res = requests.get(url=url,params={'id': term_extraction_id}).json()
            if res['status'] == "OK":
                if len(res["terms"]) == 0:
                    raise Exception("With this config ItaliaNLP.term_extraction() has not found anything")
                else:
                    break
            time.sleep(5)
        else:
            raise Exception(f"ItalianNLP API hasn't sent the requested data in {n_try*5} seconds")
        
        terms = DataFrame(res['terms'])
        terms['word_count'] = terms['term'].apply(lambda x: len(x.split()))
        return terms.sort_values(by='word_count').drop(columns=['word_count'])

if __name__ == '__main__':
    ItaliaNLAPI().execute_term_extraction(1750)