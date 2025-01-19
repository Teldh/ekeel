# -*- coding: utf-8 -*-

import wikipedia
import nltk
import string
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re, math
from collections import Counter
from time import sleep
import requests
from pprint import pprint

pages = {'1g': '1G',
     '3g': '3G',
     '4g': '4G',
     'access internet service provider': 'Internet service provider',
     'access point': 'Wireless access point',
     'active server page': 'Active Server Pages',
     'addressing system': 'Address space',
     'antivirus software': 'Antivirus software',
     'application layer': 'Application layer',
     'auditing software': 'Software audit review',
     'bit pattern': 'Bit',
     'body': 'HTML element',
     'bridge': 'Bridging (networking)',
     'browser': 'Web browser',
     'bus': 'Bus network',
     'carrier sense , multiple access with collision avoidance': 'Multiple Access '
                                                                 'with Collision '
                                                                 'Avoidance',
     'carrier sense , multiple access with collision detection': 'Carrier-sense '
                                                                 'multiple access '
                                                                 'with collision '
                                                                 'detection',
     'certificate': 'Public key certificate',
     'certificate authority': 'Certificate authority',
     'client': 'Client (computing)',
     'client side': 'Client-side',
     'client-side': 'Client-side',
     'client/server model': 'Client–server model',
     'cloud computing': 'Cloud computing',
     'cluster compute': 'Computer cluster',
     'collision avoidance': 'Carrier-sense multiple access with collision '
                            'avoidance',
     'csma': 'Carrier-sense multiple access with collision '
                            'avoidance',
     'collision detection': 'Carrier-sense multiple access with collision '
                            'detection',
     'computer': 'Computer',
     'computer system': 'Computer',
     'content delivery network': 'Content delivery network',
     'denial of service': 'Denial-of-service attack',
     'digital signature': 'Digital signature',
     'distributed system': 'Distributed computing',
     'domain': 'Network domain',
     'domain name': 'Domain name',
     'domain name system': 'Domain Name System',
     'dns': 'Domain Name System',
     'email': 'Email',
     'encryption': 'Encryption',
     'end system': 'End system',
     'end user': 'End user',
     'ethernet network': 'Ethernet',
     'extensible markup language': 'XML',
     'file server': 'File transfer',
     'file transfer protocol': 'File Transfer Protocol',
     'firewall': 'Firewall (computing)',
     'forwarding table': 'Forwarding information base',
     'gateway': 'Gateway (telecommunications)',
     'grid compute': 'Grid computing',
     'head': 'HTML element',
     'hidden terminal problem': 'Hidden node problem',
     'hop count': 'Hop (networking)',
     'hot spot': 'Hotspot (Wi-Fi)',
     'hub': 'Hub (network science)',
     'hypertext': 'Hypertext',
     'hypertext document': 'Hypertext',
     'hypertext markup language': 'HTML',
     'hypertext transfer protocol': 'Hypertext Transfer Protocol',
     'hypertext transfer protocol server': 'Hypertext Transfer Protocol',
     'instant messaging': 'Instant messaging',
     'internet': 'Internet',
     'internet infrastructure': 'Critical Internet infrastructure',
     'internet mail access protocol': 'Internet Message Access Protocol',
     'internet protocol': 'Internet Protocol',
     'ip': 'Internet Protocol',
     'internet protocol address': 'IP address',
     'internet protocol network': 'IP address',
     'internet service provider': 'Internet service provider',
     'isp': 'Internet service provider',
     'internet software': 'Internet',
     'internet2': 'Internet2',
     'interprocess communication': 'Inter-process communication',
     'intranet': 'Intranet',
     'javaserver page': 'Jakarta Server Pages',
     'link layer': 'Link layer',
     'local area network': 'Local area network',
     'lan': 'Local area network',
     'magnetic disk': 'Magnetic storage',
     'mail server': 'Message transfer agent',
     'malicious software': 'Malware',
     'mass storage': 'Mass storage',
     'metropolitan area network': 'Metropolitan area network',
     'mnemonic address': 'Network address',
     'mnemonic domain name': 'Domain name',
     'name server': 'Name server',
     'network': 'Computer network',
     'network layer': 'Network layer',
     'network news transfer protocol': 'Network News Transfer Protocol',
     'network software': 'Computer network',
     'open network': 'Open-access network',
     'peer-to-peer model': 'Peer-to-peer',
     'personal area network': 'Personal area network',
     'phishing': 'Phishing',
     'phone network': 'Cellular network',
     'php': 'PHP',
     'port number': 'Port (computer networking)',
     'post office protocol version 3': 'Post Office Protocol',
     'print server': 'Print server',
     'private-key': 'Symmetric-key algorithm',
     'protocol': 'Communication protocol',
     'proxy server': 'Proxy server',
     'public-key': 'Public key certificate',
     'public-key encryption': 'Public-key cryptography',
     'registered domain': 'Domain name',
     'remote mail server': 'Simple Mail Transfer Protocol',
     'remote server': 'Server (computing)',
     'repeater': 'Repeater',
     'router': 'Router (computing)',
     'search engine': 'Search engine',
     'second generation': '2G',
     'secure shell': 'Secure Shell',
     'secure socket layer': 'Transport Layer Security',
     'server': 'Server (computing)',
     'server side': 'Server-side',
     'server-side': 'Server-side',
     'servlet': 'Jakarta Servlet',
     'servlets': 'Jakarta Servlet',
     'simple mail transfer protocol': 'Simple Mail Transfer Protocol',
     'software': 'Software',
     'spyware': 'Spyware',
     'star': 'Star network',
     'subdomains': 'Subdomain',
     'switch': 'Network switch',
     'tag': 'HTML element',
     'tier-1 internet service provider': 'Tier 1 network',
     'tier-2 internet service provider': 'Tier 2 network',
     'tier-3 internet service provider': 'Tier 2 network',
     'top-level domains': 'Top-level domain',
     'traditional telephone': 'Telephone',
     'transmission control protocol': 'Transmission Control Protocol',
     'tcp': 'Transmission Control Protocol',
     'transmission control protocol/internet protocol network': 'Internet protocol '
                                                                'suite',
     'transport layer': 'Transport layer',
     'trojan horse': 'Trojan horse (computing)',
     'uniform resource locator': 'URL',
     'user datagram protocol': 'User Datagram Protocol',
     'udp': 'User Datagram Protocol',
     'virus': 'Computer virus',
     'voice over internet protocol': 'Voice over IP',
     'webserver': 'Web server',
     'webservers': 'Web server',
     'wide area network': 'Wide area network',
     'wan': 'Wide area network',
     'wifi network': 'Wi-Fi',
     'wireless network': 'Wireless network',
     'world wide web': 'World Wide Web',
     'worm': 'Computer worm'}

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

    excludePuncuation.add(doubleSingleQuote)
    excludePuncuation.add(doubleDash)
    excludePuncuation.add(doubleTick)

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

def page_finder(concept, rawContentDict):
    
    flag = False
    best = 0
    right_page = None
    #print(concept)
    try:
        poss = wikipedia.page(concept)#,auto_suggest=False
        return poss.title
    except wikipedia.exceptions.DisambiguationError as e:
        print("\ndisambinguazione ", concept)
        for i, page in enumerate(e.options):
            try:
                poss = wikipedia.page(page, auto_suggest=False)

                rawContentDict["text2"] = poss.summary
                text = [rawContentDict["text1"], rawContentDict["text2"]]
                tfidf = TfidfVectorizer(tokenizer=processData, stop_words="english")
                tfs = tfidf.fit_transform(rawContentDict.values())
                current = calc_and_print_CosineSimilarity_for_all(tfs, text)
                print(poss.title, current)
                if current > best:
                    best = current
                    right_page = poss
                    if current > 0.2:
                        break

            except wikipedia.exceptions.DisambiguationError as e:
                pass
            except wikipedia.exceptions.PageError as e:
                pass
        print("\n", right_page, "\n")
        if right_page is not None:
            return right_page.title

    except wikipedia.exceptions.PageError as e:
        flag = True
    



def initialize_page(text, words, file=False):

    rawContentDict = {"text1": text}

    titles = {}

    if file:
        with open('book_maps/pagine_wikipedia.txt') as f:
            lines = f.readlines()

            for index, line in enumerate(lines):
                page_id = line.strip()
                page = wikipedia.page(pageid=page_id)
                print(words[index], page.title)
                titles[words[index]] = page.title


        pprint(titles)
    else:
        for concept in words:
            if concept in pages:
                page = wikipedia.page(title=pages[concept], auto_suggest=False)
                print("**")
                print(concept, page.title)
                titles[concept] = page.title
            else:
                try:
                    title = page_finder(concept, rawContentDict)
                    if title is not None:
                        titles[concept] = title
                        print(concept, title)

                except requests.exceptions.RequestException as e:
                    #troppe richieste insieme a wikipedia, mi fermo e riprovo
                    print(e)
                    sleep(5)
                    continue

    return titles



        
