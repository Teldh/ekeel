import pandas as pd
from burst.extractor import BurstExtractor

class WeightsNormalizer:
    """
    Creates objects that compute the Normalized Relation Weight (NRW) for a given burst matrix.

    Attributes
    ----------
    bursts : pandas.DataFrame
        DataFrame containing a burst for each row.
    burst_pairs : pandas.DataFrame
        DataFrame containing pairs of related bursts.
    burst_weight_matrix : pandas.DataFrame
        DataFrame constructed from the weight-matrix generated from BurstAssigner.
    burst_norm : pandas.DataFrame
        DataFrame with size: num_concepts x num_concepts, initialized with zeros.

    Methods
    -------
    normalize(formula='original')
        Normalize the burst weight matrix using the specified formula.
    _total_length(concept)
        Compute the total length of bursts for a given concept.
    _word_frequency(concept)
        Compute the frequency of a concept in the text.

    Examples
    --------
    weight_norm = WeightsNormalizer(burst_results=filtered_bursts,
                                    burst_pairs=burst_pairs,
                                    burst_weight_matrix=burst_weight_matrix)
    weight_norm.normalize(formula='original')
    normalized_weights = weight_norm.burst_norm.dataframe
    normalized_weights = normalized_weights.round(decimals=3)
    """

    def __init__(self, bursts: pd.DataFrame, burst_pairs: pd.DataFrame, burst_weight_matrix: pd.DataFrame):
        """
        Initialize the WeightsNormalizer object.

        Parameters
        ----------
        bursts : pandas.DataFrame
            DataFrame containing a burst for each row.
        burst_pairs : pandas.DataFrame
            DataFrame containing pairs of related bursts.
        burst_weight_matrix : pandas.DataFrame
            DataFrame constructed from the weight-matrix generated from BurstAssigner.
        """

        self._bursts = bursts.copy()
        self._burst_pairs = burst_pairs.copy()
        self._burst_weight_matrix = burst_weight_matrix.copy()

        # prepare a dataset with size: num_concepts x num_concepts
        self._burst_norm = pd.DataFrame(0.0,
                                        index=self._bursts['keyword'].unique(),
                                        columns=self._bursts['keyword'].unique())

        # TODO SE2020: potenzialmente da eliminare in PRET sempre per le stesse ragioni (serve per trovare le frequenze nel testo se non vengono forniti in input dati relativi all'analisi linguistica come quelli contenuti nel conll)
        self._text_filename = ""

    def normalize(self, formula='original', occ_index_file: str=None):
        """
        Normalize the burst weight matrix using the specified formula.

        Parameters
        ----------
        formula : str, optional
            Type of normalizing formula. Possible values: 'original', 'modified', 'marzo2019_1', 'marzo2019_2'.
            Default is 'original'.
        occ_index_file : str, optional
            Path to the file containing the occurrence index with the following columns:
            "Lemma", "idFrase", "idParolaStart".
            If no value is passed, frequencies will be computed using NLTK text processing tools.

        Returns
        -------
        None

        Examples
        --------
        weight_norm = WeightsNormalizer(burst_results=filtered_bursts,
                                        burst_pairs=burst_pairs,
                                        burst_weight_matrix=burst_weight_matrix)
        weight_norm.normalize(formula='original')
        normalized_weights = weight_norm.burst_norm.dataframe
        normalized_weights = normalized_weights.round(decimals=3)
        """
        if formula not in ['original', 'modified', 'marzo2019_1', 'marzo2019_2']:
            raise ValueError("Error: the argument 'formula' must be either 'original' or 'modified'.")

        # reset dataframe to zeros if any value has been modified during a first call of the function
        if self._burst_norm.ne(0.0).any().any():
            for col in self._burst_norm.columns:
                self._burst_norm[col] = 0.0

        # precompute the word frequencies in their bursts
        for burst_id in self._bursts.index:
            start = self._bursts.at[burst_id, 'start']
            end = self._bursts.at[burst_id, 'end']
            freq = self._word_frequency(self._bursts.at[burst_id, 'keyword'], start, end,
                                        occ_index_file)
            # add the freq in a column of the same dataframe
            self._bursts.at[burst_id, 'word freq'] = freq

        # precompute the total length of bursts of each word
        tot_burst_len = {}
        for word in self._bursts['keyword'].unique():
            tot_burst_len[word] = self._total_length(word)

        # main body of the method: compare bursts and assign a normalized weight

        # for each word X
        for word_X in self._bursts['keyword'].unique():

            # retrieve the list of indexes in the bursts df assigned to the bursts of word X
            bursts_X_indexes = self._bursts.where(self._bursts['keyword'] == word_X).dropna().index.tolist()

            # for each burst of word X
            for burst_X_i in bursts_X_indexes:
                # don't consider the current burst if the entire row is zero
                if (self._burst_weight_matrix.loc[burst_X_i] == 0).all():
                    pass

                other_words = self._bursts['keyword'].unique().tolist()
                other_words.remove(word_X)

                # for each word different from word X
                for word_Y in other_words:
                    # retrieve the list of indexes in the df assigned to the bursts of word Y
                    bursts_Y_indexes = self._bursts.where(self._bursts['keyword'] == word_Y).dropna().index.tolist()

                    # for each burst of this second word Y
                    for burst_Y_j in bursts_Y_indexes:
                        # don't consider the current burst if the entire column is zero
                        if (self._burst_weight_matrix[burst_Y_j] == 0).all():
                            pass

                        # if the two bursts are related:
                        if self._burst_weight_matrix.at[burst_X_i, burst_Y_j] > 0:
                            # retrieve the weight and freqs
                            relation_weight_BX = self._burst_weight_matrix.at[burst_X_i, burst_Y_j]
                            freq_BX = self._bursts.at[burst_X_i, 'word freq']
                            freq_BY = self._bursts.at[burst_Y_j, 'word freq']

                            # compute NRW using the chosen formula
                            if formula == 'original':
                                NRW = (relation_weight_BX * (freq_BX / tot_burst_len[word_X]) *
                                       (freq_BY / tot_burst_len[word_Y]))
                                """
                                # per dare più peso a i pesi rispetto a lunghezze e frequenze
                                NRW = relation_weight_BX * ( (freq_BX / tot_burst_len[word_X]) +
                                       (freq_BY / tot_burst_len[word_Y])) 
                                       
                                # per esaltare le parole meno frequenti
                                NRW = relation_weight_BX * ( (tot_burst_len[word_X] / freq_BX) +
                                       (tot_burst_len[word_Y] / freq_BY)) 
                                """
                            elif formula == 'modified':
                                # find total number of bursts of these words
                                # TODO: (OPTIM) move it outside the loop
                                num_bursts_X = self._bursts.where(self._bursts['keyword'] == word_X).dropna().shape[0]
                                num_bursts_Y = self._bursts.where(self._bursts['keyword'] == word_Y).dropna().shape[0]
                                NRW = relation_weight_BX * ((freq_BX * num_bursts_X) / tot_burst_len[word_X]) * (
                                            (freq_BY * num_bursts_Y) / tot_burst_len[word_Y])

                            elif formula == 'marzo2019_1':
                                # freq(Y, Bj) / length of the single burst of Y under examination (i.e. BYj)
                                BYj_len = self._single_burst_length(burst_Y_j)
                                NRW = relation_weight_BX * (freq_BX / tot_burst_len[word_X]) * (freq_BY / BYj_len)

                            elif formula == 'marzo2019_2':
                                # similar to the previous but also for BXi
                                BXi_len = self._single_burst_length(burst_X_i)
                                BYj_len = self._single_burst_length(burst_Y_j)
                                NRW = relation_weight_BX * (freq_BX / BXi_len) * (freq_BY / BYj_len)


                            # update the final matrix
                            # (i.e. sum the NRW between the current burst of word X
                            # and its related burst of word Y to the already stored weight between word X and word Y)
                            self._burst_norm.at[word_X, word_Y] += NRW

    def _total_length(self, keyword):
        """
        Normalize the burst weight matrix using the specified formula.

        Parameters
        ----------
        formula : str, optional
            Type of normalizing formula. Possible values: 'original', 'modified', 'marzo2019_1', 'marzo2019_2'.
            Default is 'original'.
        occ_index_file : str, optional
            Path to the file containing the occurrence index with the following columns:
            "Lemma", "idFrase", "idParolaStart".
            If no value is passed, frequencies will be computed using NLTK text processing tools.

        Returns
        -------
        None

        Examples
        --------
        weight_norm = WeightsNormalizer(burst_results=filtered_bursts,
                                        burst_pairs=burst_pairs,
                                        burst_weight_matrix=burst_weight_matrix)
        weight_norm.normalize(formula='original')
        normalized_weights = weight_norm.burst_norm.dataframe
        normalized_weights = normalized_weights.round(decimals=3)
        """
        tot_len = 0

        sub_df = self._bursts.where(self._bursts['keyword'] == keyword).dropna()

        for i, r in sub_df.iterrows():
            tot_len += (sub_df.loc[i]["end"] - sub_df.loc[i]["start"]) + 1

        #tot_len = (self._burst_results.where(self._burst_results['keyword'] == keyword).sum()['end'] -
        #           self._burst_results.where(self._burst_results['keyword'] == keyword).sum()['start'])

        return tot_len

    def _single_burst_length(self, burst_id):
        """
        Compute the length of a single burst.

        Parameters
        ----------
        burst_id : int
            The ID of the burst.

        Returns
        -------
        int
            The length of the burst.
        """

        sub_df = self._bursts.loc[burst_id]
        length = sub_df['end'] - sub_df['start'] + 1

        return length

    def _total_length_related(self, x, y):
        """
        Finds the total length of bursts of y that have a relation with some burst of x.

        Parameters
        ----------
        x : str
            The keyword for the first concept.
        y : str
            The keyword for the second concept.

        Returns
        -------
        int
            The total length of related bursts.
        """

        sub_df = self._burst_pairs[(self._burst_pairs["x"] == x) & (self._burst_pairs["y"] == y)]
        # delete duplicate bursts of Y
        sub_df = sub_df.drop_duplicates(['By_start', 'By_end'])
        length = sub_df['By_end'].sum() - sub_df['By_start'].sum() + sub_df.shape[0]

        return length

    #def _word_frequency(self, keyword, start, end, occ_index_file: str=None):
    def _word_frequency(self, keyword, start, end, sents_idx):
        """
        Finds the frequency of a keyword in the portion of text between the limits of a burst.

        Parameters
        ----------
        keyword : str
            The keyword for which to compute the frequency.
        start : int
            The start index of the burst.
        end : int
            The end index of the burst.
        sents_idx : pandas.DataFrame
            DataFrame containing the indexes of sentences where every concept occurs. It must have the following columns:
            "Lemma", "idFrase", "idParolaStart".

        Returns
        -------
        int
            The frequency of the keyword in the specified portion of text.
        """

        freq = 0

        #if occ_index_file is not None:
        if sents_idx is not None:
            # use the occurrences provided in the index file to compute frequencies
            '''sents_idx = pd.read_csv(occ_index_file,
                                    index_col=0,
                                    usecols=["Lemma", "idFrase", "idParolaStart"],
                                    encoding="utf-8", sep="\t")'''
            # TODO: improve readability using .loc[[keyword]] that always returns a dataframe and thus avoid problems with .shape[0]
            #if type(sents_idx.loc[keyword]) == pd.Series:
            if type(sents_idx.loc[sents_idx['Lemma'] == keyword]) == pd.Series:
                # there is only one occurrence
                freq = 1
            else:
                occs_in_burst = sents_idx.loc[sents_idx['Lemma'] == keyword][(sents_idx.loc[sents_idx['Lemma'] == keyword].idFrase >= start) &
                                                   (sents_idx.loc[sents_idx['Lemma'] == keyword].idFrase <= end)]
                freq = occs_in_burst.shape[0]
        '''else:
            # occurrences are not provided: use NLTK to compute frequencies
            # TODO SE2020: questa parte non dovrebbe servire in PRET
            with open(self._text_filename, 'r', encoding='utf-8') as text:
                splitted_text = nltk.sent_tokenize(str(text.read()))

                for sent in splitted_text[start:end + 1]:
                    freq += sent.upper().count(keyword.upper())'''

        return freq


    @property
    def burst_results(self):
        """Getter"""
        return self._bursts

    @property
    def burst_weight_matrix(self):
        """Getter"""
        return self._burst_weight_matrix

    @property
    def burst_norm(self):
        """Getter of the final dataframe with normalized weights"""
        return self._burst_norm


class WeightAssigner:
    """
    A class to detect relations between bursts and assign weights to these relations based on Allen's algebra.

    Attributes
    ----------
    bursts : pandas.DataFrame
        DataFrame containing the bursts. Every row represents a burst (with a unique ID as index).
        The DataFrame must have the columns: ['keyword', 'start', 'end'].
    relations_weights : dict
        Dictionary that associates a weight to every relation in Allen's algebra.
        The key-set must contain all the relations' names (inverse relations included):
        'equals', 'before', 'after', 'meets', 'met-by', 'overlaps', 'overlapped-by',
        'during', 'includes', 'starts', 'started-by', 'finishes', 'finished-by'.
        If no dict is passed, the predefined weights will be used.
    text_filename : str, optional
        The name of the file containing the book/chapter in plain text.
    burst_matrix : pandas.DataFrame
        DataFrame consisting of a square matrix of burst weights (i.e., dimension = num_bursts x num_bursts).
        Rows and columns have as labels the IDs of the bursts.
    burst_pairs : pandas.DataFrame
        DataFrame storing all the detected pairs of Allen-related bursts, in a suitable format for machine learning projects and Gantt interface.
        Columns are: ['x', 'y', 'Bx_id', 'By_id', 'Bx_start', 'Bx_end', 'By_start', 'By_end', 'Rel'].

    Methods
    -------
    detect_relations()
        Detect relations between bursts and assign weights to these relations.
    _initialize_dataframes()
        Initialize the dataframes for burst matrix and burst pairs.
    _prop_tol_gap()
        Propagate tolerance gap for burst relations.
    _store_weights()
        Store weights for burst relations.
    _equals()
        Detect 'equals' relation between bursts.
    _finishes()
        Detect 'finishes' relation between bursts.
    _before()
        Detect 'before' relation between bursts.
    _after()
        Detect 'after' relation between bursts.
    _meets()
        Detect 'meets' relation between bursts.
    _met_by()
        Detect 'met-by' relation between bursts.
    _overlaps()
        Detect 'overlaps' relation between bursts.
    _overlapped_by()
        Detect 'overlapped-by' relation between bursts.
    _during()
        Detect 'during' relation between bursts.
    _includes()
        Detect 'includes' relation between bursts.
    _starts()
        Detect 'starts' relation between bursts.
    _started_by()
        Detect 'started-by' relation between bursts.

    Examples
    --------
    weight_assigner = WeightAssigner(bursts=filtered_bursts,
                                     relations_weights=rel_w,
                                     text_filename="chapter4.txt")
    weight_assigner.detect_relations()
    burst_pairs = weight_assigner.burst_pairs
    bursts_weights = weight_assigner.bursts_weights.dataframe
    """

    # predefined weights (they also include inverse relations)
    RELATIONS_WEIGHTS = {'equals': 5, 'before': 2, 'after': 0, 'meets': 3, 'met-by': 0,
                         'overlaps': 8, 'overlapped-by': 1, 'during': 7, 'includes': 7,
                         'starts': 6, 'started-by': 2, 'finishes': 2, 'finished-by': 8}

    def __init__(self, bursts: pd.DataFrame, relations_weights: dict = None):
        """
        Initializes the object from a dataframe storing the concepts' bursts in a
        text (this can be extracted by a BurstExtractor) and a dictionary containing
        the weights for Allen's algebra's relations.

        Parameters
        ----------
        bursts : pandas.DataFrame
            A dataframe possibly generated by a BurstExtractor.
        relations_weights : dict, optional
            A dictionary containing weights associated to every possible relation.
            If no dictionary is passed, the predefined weights will be used.

        Returns
        -------
        None
        """

        self._bursts = bursts
        self._relations_weights = relations_weights or self.RELATIONS_WEIGHTS

        # initialize the two final data structures
        self._initialize_dataframes()

    @classmethod
    def from_burst_extractor(cls, fitted_burst_extractor: BurstExtractor,
                             relations_weights: dict = None, level: int = 1):
        """
        Initializes the object from a BurstExtractor object.
    
        Parameters
        ----------
        fitted_burst_extractor : BurstExtractor
            A BurstExtractor object with already computed bursts.
        relations_weights : dict, optional
            A dictionary containing weights associated to every possible relation.
            If no dictionary is passed, the predefined weights will be used.
        level : int, optional
            The level of bursts to consider (default is 1).
    
        Returns
        -------
        WeightAssigner
            An instance of the WeightAssigner class.
        """

        bursts = fitted_burst_extractor.filter_bursts(level)

        return cls(bursts, relations_weights)

    def _initialize_dataframes(self) -> None:
        """
        Initialize the final data structures as empty dataframes or reset them to empty.

        Returns
        -------
        None
        """

        # initialize the final square matrix of weights
        self._burst_matrix = pd.DataFrame(0.0,
                                          index=self._bursts.index.tolist(),
                                          columns=self._bursts.index.tolist())

        # initialize the dataset for the machine learning project and for gantt interface
        self._burst_pairs = pd.DataFrame(columns=['x', 'y',
                                                  'Bx_id', 'By_id',
                                                  'Bx_start', 'Bx_end',
                                                  'By_start', 'By_end',
                                                  'Rel'])

    def detect_relations(self, max_gap=10, alpha=0.05, find_also_inverse=False):
        """
        Detects which relations exist between bursts, computes the weight according
        to the relations_weights schema, and stores it in the final data structure.

        Parameters
        ----------
        max_gap : int, optional
            A maximum number of sentences between two bursts after which no relation will be assigned (default is 10).
            It is used to reduce the number of 'before' and 'after' relations.
        alpha : float, optional
            Proportionality coefficient (default is 0.05). It is multiplied by the total length of the two bursts.
        find_also_inverse : bool, optional
            If False (default), only direct relations are detected. If True, the procedure will also
            detect and assign weights to inverse relations of Allen's algebra.

        Returns
        -------
        None

        Examples
        --------
        weight_assigner = WeightAssigner(bursts=filtered_bursts,
                                         relations_weights=rel_w)
        weight_assigner.detect_relations(max_gap=10, alpha=0.05, find_also_inverse=True)
        burst_pairs = weight_assigner.burst_pairs
        bursts_weights = weight_assigner.bursts_weights.dataframe
        """

        # reset the two final dataframes
        self._initialize_dataframes()

        # loop over all the rows in the dataframe (i.e. over all the bursts)
        for index1, row in self._bursts.iterrows():
            word1 = row['keyword']
            start1 = int(row['start'])
            end1 = int(row['end'])

            # among all the bursts, subsect only bursts that are not 'too before' or 'too after'
            # (considering a max admissible gap)
            # subsection = bursts.loc[(bursts['start']<(end1+max_gap)) & (bursts['end']>(start1-max_gap))]

            # consider only the bursts of words different from the current word
            subsection = self._bursts.where(self._bursts['keyword'] != word1).dropna()

            # loop over all the candidate bursts
            for index2, row2 in subsection.iterrows():

                word2 = row2['keyword']
                start2 = int(row2['start'])
                end2 = int(row2['end'])

                # compute the specific tolerance gap
                tol_gap = self._prop_tol_gap(start1, end1, start2, end2, alpha)

                # check if there is a relationship and assign the weight

                ### direct relations

                # equals
                if self._equals(start1, end1, start2, end2, tol_gap):
                    self._store_weight('equals', word1, word2, start1, end1,
                                       start2, end2, index1, index2)

                # finishes
                if self._finishes(start1, end1, start2, end2, tol_gap):
                    self._store_weight('finishes', word1, word2, start1, end1,
                                       start2, end2, index1, index2)

                # starts
                if self._starts(start1, end1, start2, end2, tol_gap):
                    self._store_weight('starts', word1, word2, start1, end1,
                                       start2, end2, index1, index2)

                # includes
                if self._includes(start1, end1, start2, end2, tol_gap):
                    self._store_weight('includes', word1, word2, start1, end1,
                                       start2, end2, index1, index2)

                # meets
                if self._meets(start1, end1, start2, end2, tol_gap):
                    self._store_weight('meets', word1, word2, start1, end1,
                                       start2, end2, index1, index2)

                # overlaps
                if self._overlaps(start1, end1, start2, end2, tol_gap):
                    self._store_weight('overlaps', word1, word2, start1, end1,
                                       start2, end2, index1, index2)

                # before
                if self._before(end1, start2, tol_gap, max_gap):
                    self._store_weight('before', word1, word2, start1, end1,
                                       start2, end2, index1, index2)

                ### inverse relations

                if find_also_inverse:

                    # met-by
                    if self._met_by(start1, start2, end2, tol_gap):
                        self._store_weight('met-by', word1, word2, start1, end1,
                                           start2, end2, index1, index2)

                    # overlapped-by
                    if self._overlapped_by(start1, end1, start2, end2, tol_gap):
                        self._store_weight('overlapped-by', word1, word2, start1, end1,
                                           start2, end2, index1, index2)

                    # during
                    if self._during(start1, end1, start2, end2, tol_gap):
                        self._store_weight('during', word1, word2, start1, end1,
                                           start2, end2, index1, index2)

                    # started-by
                    if self._started_by(start1, end1, start2, end2, tol_gap):
                        self._store_weight('started-by', word1, word2, start1, end1,
                                           start2, end2, index1, index2)

                    # finished-by
                    if self._finished_by(start1, end1, start2, end2, tol_gap):
                        self._store_weight('finished-by', word1, word2, start1, end1,
                                           start2, end2, index1, index2)

                    # after
                    if self._after(start1, end2, tol_gap, max_gap):
                        self._store_weight('after', word1, word2, start1, end1,
                                           start2, end2, index1, index2)


    # HELPER METHODS FOR detect_relations: _prop_tol_gap; _store_weight

    def _prop_tol_gap(self, start1, end1, start2, end2, alpha=0.05) -> float:
        """
        Returns a gap that is proportional to the lengths of two bursts.

        Parameters
        ----------
        start1 : int
            The start index of the first burst.
        end1 : int
            The end index of the first burst.
        start2 : int
            The start index of the second burst.
        end2 : int
            The end index of the second burst.
        alpha : float, optional
            Proportionality coefficient (default is 0.05). It is multiplied by the total length of the two bursts.

        Returns
        -------
        float
            The proportional tolerance gap.
        """

        # add 1 because the last sentence is included in the burst
        length1 = (end1 - start1) + 1
        length2 = (end2 - start2) + 1

        # compute the specific tol_gap for these two bursts
        tol_gap = (length1 + length2) * alpha

        return tol_gap

    def _store_weight(self, relation: str, word1: str, word2: str, start1: int, end1: int,
                      start2: int, end2: int, index1: int, index2: int):
        """
        Store the weight of a detected relation between bursts.

        Parameters
        ----------
        relation : str
            The type of relation detected.
        word1 : str
            The keyword of the first burst.
        word2 : str
            The keyword of the second burst.
        start1 : int
            The start index of the first burst.
        end1 : int
            The end index of the first burst.
        start2 : int
            The start index of the second burst.
        end2 : int
            The end index of the second burst.
        index1 : int
            The index of the first burst in the dataframe.
        index2 : int
            The index of the second burst in the dataframe.

        Returns
        -------
        None
        """

        # append the relationship at the end of the dataframe of burst pairs
        idx = self._burst_pairs.shape[0]
        self._burst_pairs.loc[idx] = [word1, word2,
                                      index1, index2,
                                      start1, end1, start2, end2, relation]

        # keep the weight in the final data structure only if it's greater than the currently stored weight
        if self._relations_weights[relation] > self._burst_matrix.at[index1, index2]:
            # add weight in the matrix
            self._burst_matrix.at[index1, index2] = self._relations_weights[relation]

    # HELPER METHODS FOR DEFINING RULES

    def _equals(self, start1, end1, start2, end2, tol_gap) -> bool:
        """"""
        return ((abs(start1 - start2) < tol_gap) &
                (abs(end1 - end2) < tol_gap))

    def _finishes(self, start1, end1, start2, end2, tol_gap) -> bool:
        """"""
        return ((abs(start1 - start2) > tol_gap) &
                (abs(end1 - end2) < tol_gap) &
                (start1 > start2) &
                (start1 < end2))

    def _starts(self, start1, end1, start2, end2, tol_gap) -> bool:
        """"""
        return ((abs(start1 - start2) < tol_gap) &
                (abs(end1 - end2) > tol_gap) &
                (end1 > start2) & (end1 < end2))

    def _during(self, start1, end1, start2, end2, tol_gap) -> bool:
        """"""
        return ((start1 > start2) &
                (end1 < end2) &
                (abs(start1 - start2) > tol_gap) &
                (abs(end1 - end2) > tol_gap))

    def _meets(self, start1, end1, start2, end2, tol_gap) -> bool:
        """"""
        return ((start1 < start2) &
                (end1 < end2) &
                (abs(end1 - start2) < tol_gap))

    def _overlaps(self, start1, end1, start2, end2, tol_gap) -> bool:
        """"""
        return ((start1 < start2) &
                (end1 > start2) &
                (abs(end1 - start2) > tol_gap) &
                (end1 < end2) &
                (abs(end2 - end1) > tol_gap) &
                (abs(start2 - start1) > tol_gap))

    def _before(self, end1, start2, tol_gap, max_gap) -> bool:
        """"""
        return ((start2 > (end1 + tol_gap)) &
                ((start2 - end1) <= max_gap))

    def _met_by(self, start1, start2, end2, tol_gap) -> bool:
        """"""
        return ((start1 > start2) &
                (start1 > end2) &  # FIXME: anche se le inverse non sono state quasi mai usate, provare ad eliminare questa regola (non si verifica in alcuni casi)
                (abs(start1 - end2) < tol_gap))

    def _overlapped_by(self, start1, end1, start2, end2, tol_gap) -> bool:
        """"""
        return ((start1 > start2) &
                (start1 < end2) &
                (abs(start1 - end2) > tol_gap) &
                (abs(start1 - start2) > tol_gap) &
                (end1 > end2) &
                (abs(end1 - end2) > tol_gap))

    def _includes(self, start1, end1, start2, end2, tol_gap) -> bool:
        """"""
        return ((start1 < start2) &
                (end1 > end2) &
                (abs(start1 - start2) > tol_gap) &
                (abs(end1 - end2) > tol_gap))

    def _started_by(self, start1, end1, start2, end2, tol_gap) -> bool:
        """"""
        return ((end1 > end2) &
                (start1 < end2) &
                (abs(start1 - start2) < tol_gap) &
                (abs(end1 - end2) > tol_gap))

    def _finished_by(self, start1, end1, start2, end2, tol_gap) -> bool:
        """"""
        return ((start1 < start2) &
                (end1 > start2) &
                (abs(start1 - start2) > tol_gap) &
                (abs(end1 - end2) < tol_gap))

    def _after(self, start1, end2, tol_gap, max_gap) -> bool:
        """"""
        return ((start1 > (end2 + tol_gap)) &
                ((start1 - end2) <= max_gap))

    @property
    def bursts(self):
        """Getter of the input dataframe containing the bursts."""
        return self._bursts

    @property
    def relations_weights(self):
        """Getter of the dictionary containing the weights for all relations in Allen's algebra"""
        return self._relations_weights

    @property
    def bursts_weights(self):
        """Getter of the final dataframe containing the weights between all bursts."""
        return self._burst_matrix

    @property
    def burst_pairs(self):
        """Getter of the final dataframe containing pairs of related bursts in the format needed for machine learning project."""
        return self._burst_pairs

    def __repr__(self):
        return "WeightAssigner(bursts={}, relations_weights={})".format(
            repr(self._bursts), repr(self._relations_weights))

    def __str__(self):
        return "WeightAssigner object. Input bursts (only first 5 rows):\n{}\n,\nrelations_weights:{}".format(
            repr(self._bursts.head()), repr(self._relations_weights))

