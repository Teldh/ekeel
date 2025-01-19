import pandas as pd

"""
Includes utility functions that are used to process burst results and obtain data for other applications.
"""


def find_average_len(burst_results) -> dict:
    """
    Finds the average length of bursts of a concept.

    Parameters
    ----------
    burst_results : pandas.DataFrame
        DataFrame with columns [keyword, level, start, end].

    Returns
    -------
    dict
        Dictionary with concepts associated to the average length of their bursts.

    Examples
    --------
    Example of the returned dictionary format:
        {
            "concept1": 5.0,
            "concept2": 3.5,
            ...
        }
    """
    avg = {}

    for t in burst_results["keyword"].unique().tolist():

        sub_df = burst_results.where(burst_results['keyword'] == t).dropna()
        tot_len = 0

        for i, r in sub_df.iterrows():
            tot_len += (sub_df.loc[i]["end"] - sub_df.loc[i]["start"]) + 1

        avg[t] = tot_len / sub_df.shape[0]

    return avg


def find_first_longest(burst_results, avg) -> dict:
    """
    Finds the first burst having a length that is higher than the average length of all bursts of that concept.

    Parameters
    ----------
    burst_results : pandas.DataFrame
        DataFrame with columns [keyword, level, start, end].
    avg : dict
        Dictionary with concepts associated to the average length of their bursts.

    Returns
    -------
    dict
        Dictionary with concepts associated with the id of the first longest burst.

    Examples
    --------
    Example of the returned dictionary format:
        {
            "concept1": 0,
            "concept2": 3,
            ...
        }
    """
    print("***** EKEEL - Video Annotation: burst_results_processor.py::find_first_longest(): ******")

    """
    Finds the first burst having a length that is higher than the average length of all bursts of that concept.

    :param bursts_results (pandas.DataFrame): df with these columns [keyword,level,start,end]
    :param avg (dict): average length of bursts of a concept

    :return: first_longest (dict): dictionary with concepts associated with the id of the first longest burst
    """
    first_longest = {}

    for t in burst_results["keyword"].unique().tolist():

        sub_df = burst_results.where(burst_results['keyword'] == t).dropna()

        for i, r in sub_df.iterrows():
            if sub_df.shape[0] == 1:
                first_longest[t] = i
            else:
                curr_len = sub_df.loc[i]["end"] - sub_df.loc[i]["start"] + 1
                if curr_len > avg[t]:
                    first_longest[t] = i
                    break

        if t not in first_longest:
            first_longest[t] = sub_df[burst_results["end"] - burst_results["start"] + 1 == avg[t]].iloc[0].name

    return first_longest


def get_json_with_bursts(burst_results, sents_idx):
    """
    Gets a list of bursts with first/last/ongoing/unique tags that can be used for the Gantt interface.

    Parameters
    ----------
    burst_results : pandas.DataFrame
        DataFrame with columns [keyword, level, start, end].
    sents_idx : pandas.DataFrame
        DataFrame containing the indexes of sentences where every concept occurs. It must have the following columns:
        "Lemma", "idFrase", "idParolaStart".

    Returns
    -------
    list of dict
        List of bursts with their details including start sentence, end sentence, concept, ID, frequency of term, and status.

    Examples
    --------
    Example of the returned list format:
        [
            {"startSent": 0, "endSent": 9, "concept": "computer", "ID": 1, "freqOfTerm": 7, "status": "FIRST"},
            {"startSent": 10, "endSent": 19, "concept": "network", "ID": 2, "freqOfTerm": 5, "status": "ONGOING"},
            ...
        ]
    """
    bursts_json = []

    #sents_idx = pd.read_csv(occ_index_file, encoding="utf-8", index_col=None, sep="\t",
    #                      usecols=["Lemma", "idFrase", "idParolaStart"])


    # format: {"startSent": 0, "endSent": 9, "concept": "computer", "ID": 1, "freqOfTerm": 7, "status": "FIRST"}
    for i, row in burst_results.iterrows():
        curr_dict = {}
        curr_dict["startSent"] = int(row["start"])
        curr_dict["endSent"] = int(row["end"])
        curr_dict["concept"] = row["keyword"]
        curr_dict["ID"] = int(i)

        curr_dict["freqOfTerm"] = sents_idx[(sents_idx["idFrase"] >= int(row["start"])) &
                                            (sents_idx["idFrase"] <= int(row["end"])) &
                                            (sents_idx["Lemma"] == row["keyword"])].shape[0]

        if len(burst_results[burst_results["keyword"] == row["keyword"]]["start"]) == 1:
            curr_dict["status"] = "UNIQUE"
        elif row["start"] == burst_results[burst_results["keyword"] == row["keyword"]]["start"].min():
            curr_dict["status"] = "FIRST"
        elif row["end"] == burst_results[burst_results["keyword"] == row["keyword"]]["end"].max():
            curr_dict["status"] = "LAST"
        else:
            curr_dict["status"] = "ONGOING"



        bursts_json.append(curr_dict)

    print("***** EKEEL - Video Annotation: burst_results_processor.py::get_json_with_bursts(): Fine ******")


    return bursts_json


def give_direction_using_first_burst(undirected_matrix: pd.DataFrame,
                                     bursts_results: pd.DataFrame,
                                     indexes,
                                     level=1, preserve_relations=False) -> pd.DataFrame:
    """
    Give direction to an undirected matrix using the first burst of each concept.

    Parameters
    ----------
    undirected_matrix : pandas.DataFrame
        DataFrame representing the undirected adjacency matrix.
    bursts_results : pandas.DataFrame
        DataFrame with columns [keyword, level, start, end].
    indexes : pandas.DataFrame
        DataFrame containing the indexes of sentences where every concept occurs. It must have the following columns:
        "Lemma", "idFrase", "idParolaStart".
    level : int, optional
        The level of bursts to consider (default is 1).
    preserve_relations : bool, optional
        If False, the weight in the "wrong" direction is killed and the weight in the right direction remains the same (potentially zero).
        If True, before the weight in the "wrong" direction is killed, the weight in the "right" direction is checked: if this is zero,
        it will be replaced with the weight of the wrong direction (and then the wrong is killed).

    Returns
    -------
    pandas.DataFrame
        DataFrame representing the directed adjacency matrix.

    Examples
    --------
    Example of the returned DataFrame format:
        source  target  weight
        concept1 concept2 0.5
        concept2 concept3 0.7
        ...
    """
    filtered_bursts = bursts_results.where(bursts_results['level'] == level).dropna()
    #indexes = pd.read_csv(occ_index_file, encoding="utf-8", index_col=0, sep="\t",
    #                      usecols=["Lemma", "idFrase", "idParolaStart"])

    directed_df = undirected_matrix.copy()

    for t1 in directed_df.index.tolist():

        other_terms = directed_df.index.tolist()
        other_terms.remove(t1)

        for t2 in other_terms:

            start_first_burst_t1 = filtered_bursts[filtered_bursts["keyword"] == t1].iloc[0]["start"]
            start_first_burst_t2 = filtered_bursts[filtered_bursts["keyword"] == t2].iloc[0]["start"]

            if start_first_burst_t1 < start_first_burst_t2:
                # t1 is a prereq of t2
                if preserve_relations and directed_df.at[t1, t2] == 0:
                    directed_df.at[t1, t2] = directed_df.at[t2, t1]
                directed_df.at[t2, t1] = 0
            elif start_first_burst_t2 < start_first_burst_t1:
                # t2 is a prereq of t1
                if preserve_relations and directed_df.at[t2, t1] == 0:
                    directed_df.at[t2, t1] = directed_df.at[t1, t2]
                directed_df.at[t1, t2] = 0
            elif start_first_burst_t2 == start_first_burst_t1:
                # they are in the same sentence: need to check the tokens
                #t1_pos_in_sent = indexes[indexes["idFrase"] == start_first_burst_t1].loc[t1]["idParolaStart"].min()
                #t2_pos_in_sent = indexes[indexes["idFrase"] == start_first_burst_t1].loc[t2]["idParolaStart"].min()

                t1_pos_in_sent = indexes[indexes["idFrase"] == start_first_burst_t1].loc[indexes["Lemma"] == t1]["idParolaStart"].min()
                t2_pos_in_sent = indexes[indexes["idFrase"] == start_first_burst_t1].loc[indexes["Lemma"] == t2]["idParolaStart"].min()

                if t1_pos_in_sent < t2_pos_in_sent:
                    # t1 is a prereq of t2
                    if preserve_relations and directed_df.at[t1, t2] == 0:
                        directed_df.at[t1, t2] = directed_df.at[t2, t1]
                    directed_df.at[t2, t1] = 0
                elif t2_pos_in_sent < t1_pos_in_sent:
                    # t2 is a prereq of t1
                    if preserve_relations and directed_df.at[t2, t1] == 0:
                        directed_df.at[t2, t1] = directed_df.at[t1, t2]
                    directed_df.at[t1, t2] = 0
                else:
                    # the two concepts are an embedding concept and its nested concept:
                    # use length to decide direction (the one with less words is the prerequisite)
                    if len(t1.split()) < len(t2.split()):
                        directed_df.at[t2, t1] = 0
                    elif len(t2.split()) < len(t1.split()):
                        directed_df.at[t1, t2] = 0
                    # else:
                    #     print("Impossible to give direction to this pair (not even by "
                    #           "looking at the first sentence of their first burst):", t1, "\t", t2)
            else:
                print("Impossible to give direction to:", t1, "\t<->\t", t2)

    directed_df = directed_df.round(decimals=3)

    return directed_df


