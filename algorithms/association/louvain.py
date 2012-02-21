#!/usr/bin/env python
# encoding: utf-8

import networkx as nx

import pyannote.algorithms.community
from pyannote.base.association import Mapping, OneToOneMapping, MElement, NoMatch
from pyannote.base.comatrix import Confusion, AutoConfusion
from hungarian import Hungarian

class Louvain(object):
    """
    """
    def __init__(self, normalize=False, overlap=False, complete=False, force=False, recursive=False):
        super(Louvain, self).__init__()
        self.__normalize = normalize
        self.__overlap = overlap
        self.__complete = complete
        self.__force = force
        if complete:
            self.__hungarian = Hungarian(normalize=normalize, force=force)
        self.__recursive = recursive
    
    def __get_normalize(self): 
        return self.__normalize
    normalize = property(fget=__get_normalize, \
                     fset=None, \
                     fdel=None, \
                     doc="Normalize confusion matrix?")

    def __get_overlap(self): 
        return self.__overlap
    overlap = property(fget=__get_overlap, \
                     fset=None, \
                     fdel=None, \
                     doc="Intra-modality overlap?")

    def __get_force(self): 
        return self.__force
    force = property(fget=__get_force, \
                     fset=None, \
                     fdel=None, \
                     doc="Force mapping?")

    def __get_complete(self): 
        return self.__complete
    complete = property(fget=__get_complete, \
                     fset=None, \
                     fdel=None, \
                     doc="Complete one-to-one mapping?")

    def __get_recursive(self): 
        return self.__recursive
    recursive = property(fget=__get_recursive, \
                     fset=None, \
                     fdel=None, \
                     doc="Recursive calls until convergence?")


    def __partition_to_cluster(self, partition):
        clusters = {}
        for node in partition:
            if partition[node] not in clusters:
                clusters[partition[node]] = []
            clusters[partition[node]].append(node)
        return clusters

    def __autoconfusion_graph(self, A):
    
        # AutoConfusion matrix
        M = AutoConfusion(A, neighborhood=0., normalize=self.normalize)
    
        # Shape and labels
        Na, Na = M.shape
        alabels, alabels = M.labels
    
        G = nx.Graph()
        for i in range(Na):
            alabel_i = alabels[i]
            anode_i = MElement(A.modality, alabel_i)
            G.add_node(anode_i)
            for j in range(i+1, Na):
                alabel_j = alabels[j]
                anode_j = MElement(A.modality, alabel_j)
                if M[alabel_i, alabel_j] > 0.:
                    G.add_edge(anode_i, anode_j)
                    G[anode_i][anode_j]['weight'] = M[alabel_i, alabel_j]
    
        return G
    
    def __confusion_graph(self, A, B):
    
        # Confusion matrix
        M = Confusion(A, B, normalize=self.normalize)
    
        # Shape and labels
        Na, Nb = M.shape
        alabels, blabels = M.labels
    
        # Confusion graph
        G = nx.Graph()
        for a, alabel in enumerate(alabels):
            anode = MElement(A.modality, alabel)
            G.add_node(anode)
            for blabel in blabels:
                bnode = MElement(B.modality, blabel)
                if a < 1:
                    G.add_node(bnode)
                if M[alabel, blabel] > 0.:
                    G.add_edge(anode, bnode)
                    G[anode][bnode]['weight'] = M[alabel, blabel]
    
        if self.overlap:
            Ga = self.__autoconfusion_graph(A)
            G.add_edges_from(Ga.edges(data=True))
        
            Gb = self.__autoconfusion_graph(B)
            G.add_edges_from(Gb.edges(data=True))
        
        return G
    
    def __call__(self, A, B, init=None, recursive=False):
        
        if recursive:
            if init is None:
                init = Mapping(A.modality, B.modality)
                init += (A.IDs, B.IDs)

            new_init = self(A, B, init=init, recursive=False)
            if new_init == init:
            
            else:
                return self(A, B, init=new_init, recursive=True)
            
        else:
            
            # first call
            if init is None:
                init = self(A, B, init=None)
            
            new_init = self(A, B, init=init)
            
            if new_init != init:
                init = new_init
                return self(A, B, init=init)
            else:
                
            
        else:
        
            G = self.__confusion_graph(A, B)
    
            if nx.number_connected_components(G) == len(G.nodes()):
                partition = {node: n for n, node in enumerate(G.nodes_iter())}
            else:
                # Community detection
                partition = pyannote.algorithms.community.best_partition(G)

            clusters = self.__partition_to_cluster(partition)
    
            # Many-to-many mapping
            M = Mapping(A.modality, B.modality)
            for cluster in clusters:
                nodes = clusters[cluster]
                key = [node.element for node in nodes if node.modality == A.modality]
                value = [node.element for node in nodes if node.modality == B.modality]
                M += (key, value)
    
            if self.complete:
                M = self.__hungarian(A, B, init=M)
        
            return M