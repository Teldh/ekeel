"""
Text clustering module for subtitle analysis.

This module provides functionality for clustering subtitle sentences
based on their semantic embeddings and timestamps.
"""

import torch
import datetime
from sentence_transformers import util


class Cluster:
    """
    Cluster of related subtitles with their embeddings.

    Attributes
    ----------
    index : int
        Cluster identifier
    sentences : list
        List of subtitle texts
    embeddings : list
        List of sentence embeddings
    mean_embedding : torch.Tensor
        Mean embedding vector for cluster
    start_time : float
        Start timestamp of cluster
    end_time : float
        End timestamp of cluster
    keyframes : list
        List of keyframe indices
    summary : list
        Summary sentences for cluster

    Methods
    -------
    merge_cluster(c)
        Merge another cluster into this one
    add_sentence(s, e)
        Add new sentence with its embedding
    """

    def __init__(self, index, subtitle, embedding):
        self.index = index
        self.sentences = [subtitle["text"]]
        self.embeddings = [embedding]
        self.mean_embedding = embedding
        self.start_time = subtitle["start"]
        self.end_time = subtitle["end"]
        self.keyframes = []
        self.summary = []

    def merge_cluster(self, c):
        """
        Merge another cluster into this one.

        Parameters
        ----------
        c : Cluster
            Cluster to merge

        Returns
        -------
        Cluster
            Self with merged contents
        """
        self.sentences = self.sentences + c.sentences
        self.embeddings = self.embeddings + c.embeddings
        self.mean_embedding = self.mean_embedding + c.mean_embedding
        self.end_time = c.end_time
        self.keyframes = self.keyframes + c.keyframes
        return self

    def add_sentence_deprecated(self, s, e):
        """Old ver, use add_sentence instead. Add sentence s and compute the new mean embedding value for the cluster"""
        self.sentences.append(s)
        # for i in range(0,len(e)):
        #     self._mean_embedding[i] = int((self._mean_embedding[i] + e[i])/2)
        somma = self._mean_embedding.add(e)
        self._mean_embedding = torch.div(somma, 2)

    def add_sentence(self, s, e):
        """
        Add new sentence and update mean embedding.

        Parameters
        ----------
        s : str
            Sentence text
        e : torch.Tensor
            Sentence embedding
        """
        self.sentences.append(s)
        self.embeddings.append(e)

        temp_emb = self.embeddings[0]
        # for i in range(len(self.embeddings[0])):
        #     tot = 0
        #     for j in range(len(self.embeddings)):
        #         tot += self.embeddings[j][i]
        #     tot /= len(self.embeddings)
        #     temp_emb.append(tot)

        for emb in range(1, len(self.embeddings)):
            temp_emb.add(emb)

        temp_emb = torch.div(temp_emb, len(self.embeddings))

        self.mean_embedding = temp_emb

    def __str__(self):
        output_str = f"cluster {self.index}\n"
        output_str += f"t: ({str(datetime.timedelta(seconds=self.start_time))},{str(datetime.timedelta(seconds=self.end_time))})\n"
        output_str += f"{self._sentences.__str__()}\n"
        #output_str += f"{self.keyframes.__str__()}\n"

        '''output_str += "Riassunto: \n"
        for i, s in enumerate(self.summary):
            output_str += f"{i}. {s.__str__()}\n"'''
        return output_str

    @property
    def sentences(self):
        return self._sentences

    @sentences.setter
    def sentences(self, s):
        self._sentences = s

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, value):
        self._index = value

    @property
    def mean_embedding(self):
        return self._mean_embedding

    @mean_embedding.setter
    def mean_embedding(self, value):
        self._mean_embedding = value

    @property
    def summary(self):
        return self._summary

    @summary.setter
    def summary(self, s):
        self._summary = s

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, e):
        self._end_time = e

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, s):
        self._start_time = s


def create_cluster_list(timed_sentences, embeddings, c_threshold):
    """
    Create list of clusters from timed sentences.

    Parameters
    ----------
    timed_sentences : list
        List of dictionaries containing text and timestamps
    embeddings : list
        List of sentence embeddings
    c_threshold : float
        Clustering similarity threshold

    Returns
    -------
    list
        List of Cluster objects
    """
    c_id = 0
    cluster_list = [Cluster(c_id, timed_sentences[0], embeddings[0])]
    sum = 0

    for i in range(1, len(embeddings)):
        sum += util.pytorch_cos_sim(embeddings[i], embeddings[i - 1])[0].numpy()[0]

    c_threshold = (sum / len(embeddings))/1.5
    #print("somma", sum, sum / len(embeddings), c_threshold)


    for i in range(1, len(embeddings)):
        '''Cosine similarity'''
        similarity_mean = util.pytorch_cos_sim(cluster_list[c_id].mean_embedding, embeddings[i])
        similarity_last = util.pytorch_cos_sim(embeddings[i-1], embeddings[i])

        if similarity_mean[0].numpy()[0] > c_threshold or similarity_last[0].numpy()[0] > c_threshold:
            cluster_list[c_id].add_sentence(timed_sentences[i]["text"], embeddings[i])
            cluster_list[c_id].end_time = timed_sentences[i]["end"]

        else:
            c_id += 1
            new_cluster = Cluster(c_id, timed_sentences[i], embeddings[i])
            cluster_list.append(new_cluster)

    return cluster_list


def aggregate_short_clusters_deprecated(clusters, seconds):
    refined_clusters = []
    temp_cluster = None
    fl = False
    for c in clusters:
        if c.end_time - c.start_time > seconds and not fl:
            refined_clusters.append(c)
        elif fl:
            refined_clusters.append(temp_cluster.merge_cluster(c))
            fl = False
        else:
            temp_cluster = c
            fl = True
    return refined_clusters


def aggregate_short_clusters(clusters:list[Cluster], seconds):
    """
    Merge clusters shorter than specified duration.

    Parameters
    ----------
    clusters : list[Cluster]
        List of clusters to process
    seconds : float
        Minimum cluster duration

    Returns
    -------
    list
        List of merged Cluster objects
    """
    merge_times = []
    s = 0
    for e, c in enumerate(clusters):
        if clusters[e].end_time - clusters[s].start_time > seconds:
            merge_times.append({"start":s, "end":e})
            s = e+1
        elif e == len(clusters)-1:
            # if the last cluster is too short, I merge it with the last second-last
            merge_times[-1] = ({"start":merge_times[-1]["start"], "end":e})

    #print(f"merge times: {merge_times}")

    refined_clusters = []
    for m in merge_times:
        temp_cluster = clusters[m["start"]]
        for k in range(m["start"]+1,m["end"]+1):
            temp_cluster.merge_cluster(clusters[k])
        refined_clusters.append(temp_cluster)

    return refined_clusters


