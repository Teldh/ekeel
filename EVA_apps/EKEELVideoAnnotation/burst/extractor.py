"""
Burst detection module for text analysis.

This module implements Kleinberg's burst detection algorithm to identify
bursts of term occurrences in text.
"""

import numpy as np
import pandas as pd
import nltk
from collections import defaultdict
from burst.kleinberg import kleinberg


class BurstExtractor:
    """
    Burst detection implementation using Kleinberg's algorithm.

    Detects bursts of term occurrences in text by analyzing their temporal
    distribution using an automaton model.

    Attributes
    ----------
    _rawtext : str
        The input text to analyze
    _terminology : list
        List of terms to detect bursts for
    _offsets : dict
        Dictionary mapping terms to their occurrence positions
    _bursts : pandas.DataFrame
        Detected bursts with columns [keyword, level, start, end]
    _s : float
        Base of exponential distribution
    _gamma : float
        Cost coefficient between states

    Methods
    -------
    find_offsets(words, occ_index_file)
        Find term occurrences in text
    generate_bursts(s, gamma)
        Detect bursts using Kleinberg's algorithm
    filter_bursts(level)
        Filter bursts by hierarchy level
    break_bursts(burst_length, num_occurrences)
        Break long bursts into smaller ones
    get_words_with_bursts(level)
        Get terms that have bursts at given level
    get_excluded_words(level)
        Get terms with no bursts at given level
    """

    def __init__(self, text, wordlist):
        """
        Initialize burst detector.

        Parameters
        ----------
        text : str
            Text to analyze
        wordlist : list
            Terms to detect bursts for
        """
        # open and load the text into a variable
        self._rawtext = text

        self._terminology = wordlist

        # initialize parameters of Kleinberg
        self._s = None
        self._gamma = None
        # initialize the final structures
        self._offsets = defaultdict(list)
        self._bursts = pd.DataFrame(columns=['keyword', 'level', 'start', 'end'],
                                    dtype='int64')

    def find_offsets(self, words=None, occ_index_file: str=None) -> dict:
        """
        Find term occurrences in text.

        Parameters
        ----------
        words : list, optional
            Terms to find offsets for
        occ_index_file : str, optional
            Pre-computed offsets file

        Returns
        -------
        dict
            Term to offset position mapping
        """
        if occ_index_file is not None:
            ### use offsets that are available in occ index file
            self._offsets = {}

            for o in occ_index_file.itertuples():
                if o.Lemma not in self._offsets:
                    self._offsets[o.Lemma] = []

                if o.idFrase not in self._offsets[o.Lemma]:
                    self._offsets[o.Lemma].append(o.idFrase)

        else:
            ### find the offsets using NLTK
            # (non dovrebbe mai servire)

            # reset and populate the offsets dict
            self._offsets = defaultdict(list)

            sentences = nltk.sent_tokenize(self._rawtext)
            # search each word in each sentence
            for word in self._terminology:
                for index, sent in enumerate(sentences):
                    if word.upper() in sent.upper():
                        # add the index of the sentence in the list of offsets of that word
                        self._offsets[word].append(index)
        return self._offsets

    def generate_bursts(self, s=2, gamma=1) -> pd.DataFrame:
        """
        Detect bursts using Kleinberg's algorithm.

        Parameters
        ----------
        s : float, optional
            Base of exponential distribution (>1)
        gamma : float, optional
            Cost coefficient between states (>0)

        Returns
        -------
        pandas.DataFrame
            Detected bursts with columns [keyword, level, start, end]
        """
        if not self._offsets:
            return None
            choice = input("""You must first detect the offsets (by calling the method 'find_offset').
                            Do you want to find offsets now (without an index file) 
                            and then automatically detect the bursts? Press y/n\n""")
            if choice in ['y', 'Y']:
                print('The offsets will be detected and then the process will compute bursts.\n')
                self._offsets = self.find_offsets()
            else:
                print("Neither offsets or bursts will be computed.\n")
                return None

        # reset self._burst
        self._bursts = pd.DataFrame(columns=['keyword', 'level', 'start', 'end'],
                                    dtype='int64')

        for keyword in self._offsets:
            # compute bursts
            curr_bursts = kleinberg(self._offsets[keyword], s, gamma)
            # insert the name of the word in the array
            curr_bursts = np.insert(curr_bursts, 0, values=keyword, axis=1)
            # convert it to a df and append it to the complete df of bursts
            curr_bursts_df = pd.DataFrame(curr_bursts,
                                          columns=['keyword', 'level', 'start', 'end'])
            self._bursts = pd.concat([self._bursts, curr_bursts_df], ignore_index=True)

        return self._bursts

    def filter_bursts(self, level=1, save_monolevel_keywords=False, 
                     replace_original_results=False) -> pd.DataFrame:
        """
        Filter bursts by hierarchy level.

        Parameters
        ----------
        level : int, optional
            Burst hierarchy level to filter by
        save_monolevel_keywords : bool, optional
            Keep terms with single burst
        replace_original_results : bool, optional
            Update internal burst data

        Returns
        -------
        pandas.DataFrame
            Filtered bursts
        """
        if self._bursts.shape[0] == 0:
            raise ValueError("Bursts non yet extracted: "
                             "call the method 'generate_bursts' first!")

        # avoid index errors
        if level < 0:
            raise ValueError("The level must have a positive value.")
        if level > self._bursts['level'].max():
            print("""The desired level exceeds the maximum level present in the results:
                    the latter will be used.""")
            level = self._bursts['level'].max()

        b = self._bursts.copy()

        if save_monolevel_keywords:
            # don't filter the terms with only a burst, even if this is less that the desired
            for t in b["keyword"].unique().tolist():
                if b[b["keyword"] == t].shape[0] == 1:
                    i = b.index[b['keyword'] == t][0]
                    b.at[i, "level"] = 1

        filtered = b.where(b['level'] == level).dropna()

        if replace_original_results:
            self._bursts = filtered.copy()
        else:
            return filtered

    def break_bursts(self, burst_length=30, num_occurrences=3, 
                    replace_original_results=False, verbose=False):
        """
        Break long bursts into smaller ones.

        Parameters
        ----------
        burst_length : int, optional
            Minimum length to break burst
        num_occurrences : int, optional
            Maximum occurrences to consider
        replace_original_results : bool, optional
            Update internal burst data
        verbose : bool, optional
            Print detailed information

        Returns
        -------
        pandas.DataFrame or None
            Modified burst data if not replacing
        """
        if verbose:
            print("The following burst have been deleted and replaced with smaller bursts:\n")

        b = self._bursts.copy()

        for i, row in self._bursts.iterrows():
            curr_len = (row["end"] - row["start"]) + 1
            if curr_len >= burst_length and len(self._offsets[row["keyword"]]) <= num_occurrences:

                b.drop(i, inplace=True)
                last_idx = b.index[-1]
                b.loc[last_idx + 1] = {"keyword": row["keyword"], "level": row["level"],
                                       "start": row["start"], "end": row["start"]}
                b.loc[last_idx + 1] = {"keyword": row["keyword"], "level": row["level"],
                                       "start": row["end"], "end": row["end"]}

                if verbose:
                    print(row["keyword"], "\toffsets:", self._offsets[row["keyword"]],
                          "\tstart:", int(row["start"]), "\tend:", int(row["end"]), "\n")

        if replace_original_results:
            self._bursts = b.copy()
        else:
            return b

    def get_words_with_bursts(self, level=1) -> set:
        """
        Get terms that have bursts at given level.

        Parameters
        ----------
        level : int, optional
            Burst hierarchy level

        Returns
        -------
        set
            Terms with bursts at specified level
        """
        filtered_burst = self.filter_bursts(level)

        return set(filtered_burst['keyword'].unique())

    def get_excluded_words(self, level=1) -> set:
        """
        Get terms with no bursts at given level.

        Parameters
        ----------
        level : int, optional
            Burst hierarchy level

        Returns
        -------
        set
            Terms without bursts at specified level
        """
        filtered_burst = self.filter_bursts(level)

        return set(self._terminology) - set(filtered_burst['keyword'].unique())

    @property
    def text_filename(self):
        """Get input text filename."""
        return self._text_filename

    @property
    def rawtext(self):
        """Get raw input text."""
        return self._rawtext

    @property
    def terminology(self):
        """Get list of terms."""
        return self._terminology

    @property
    def offsets(self):
        """Get term offsets dictionary."""
        return self._offsets

    @property
    def bursts(self):
        """Get detected bursts DataFrame."""
        return self._bursts

    def __repr__(self):
        return 'BurstExtractor(text_filename={0}, wordlist={1})'.format(
            repr(self._text_filename), repr(self._terminology))
