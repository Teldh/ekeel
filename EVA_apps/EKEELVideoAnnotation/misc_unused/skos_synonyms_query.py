import rdflib

'''
Trying some queries on skos graph
'''
def try_query(synonym_graph) :

    # Get concept uri from query
    query1 = """
        PREFIX edu: <http://edurell.com/Ann/>
        SELECT ?c
            WHERE {
                ?c skos:prefLabel ?label .
            }
    """
    # !!! https://derwen.ai/docs/kgl/ex4_0/

    # Get only literal from query
    query2 = """
        PREFIX edu: <http://edurell.com/Ann/>
        SELECT ?stripped_label
            WHERE {
                ?c skos:prefLabel ?label .
                FILTER (lang(?label) = 'en')
                BIND (STR(?label)  AS ?stripped_label) 
            }
    """

    # Get synonyms from query
    query3 = """
        PREFIX edu: <http://edurell.com/Ann/>
        SELECT ?alt_label
            WHERE {
                ?c skos:prefLabel ?p_label .
                ?c skos:altLabel ?alt_label . 
                FILTER (?p_label = "pubis"@en)
            }
    """

    # Get synonyms from query with paramethers
    query4 = """
        PREFIX edu: <http://edurell.com/Ann/>
        SELECT ?alt_label
            WHERE {
                ?c skos:prefLabel ?pr_label .
                ?c skos:altLabel ?alt_label . 
                FILTER (?pr_label = ?name)
            }
    """
    
    print("-------------\n")
    qres = synonym_graph.query(query1)

    for row in qres:
        print(row["c"].n3())

    print("-------------\n")
    qres = synonym_graph.query(query2)

    for row in qres:
        print(row["stripped_label"].n3())

    print("-------------\n")
    qres = synonym_graph.query(query3)

    for row in qres:
        print(row["alt_label"].n3())

    print("-------------\n")
    label_name = rdflib.Literal('orbit', lang='en')
    qres = synonym_graph.query(query4, initBindings={'name': label_name})

    for row in qres:
        print(row["alt_label"].n3())

    print("-------------\n")
    return 0