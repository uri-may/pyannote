#!/usr/bin/env python
# encoding: utf-8

# Copyright 2012 Herve BREDIN (bredin@limsi.fr)

# This file is part of PyAnnote.
# 
#     PyAnnote is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
# 
#     PyAnnote is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
# 
#     You should have received a copy of the GNU General Public License
#     along with PyAnnote.  If not, see <http://www.gnu.org/licenses/>.

"""This module defines constraint mixin for agglomerative clustering.

    A ConstraintMixin must implement the following methods:
        * _setup(**kwargs)
        * _initialize()
        * _update(new_label, old_labels)
        * _meet_constraint(labels)

"""

from pyannote.algorithm.clustering.base import BaseConstraintMixin

from pyannote.base.matrix import LabelMatrix
class ContiguousConstraintMixin(BaseConstraintMixin):
    """
    Two labels are mergeable if they are contiguous
    """
    
    def _get_tolerance(self):
        return self.__tolerance
    tolerance = property(fget=_get_tolerance)
    
    def _setup_constraint(self, tolerance=0., **kwargs):
        self.__tolerance = tolerance
    
    def __xsegment(self, segment):
        """
        Extend segment by half tolerance on both side
        """
        return .5*self.tolerance << segment >> .5*self.tolerance
    
    def _initialize_constraint(self, **kwargs):
        """
        Two labels are mergeable if they are contiguous
        """
        
        self.__contiguous = LabelMatrix(dtype=bool, default=False)
        labels = self.annotation.labels()
        for l, label in enumerate(labels):
            
            # extended coverage
            cov = self.annotation.label_coverage(label)
            xcov = cov.copy(segment_func=self.__xsegment)
            
            for other_label in labels[l+1:]:
                
                # other extended coverage
                other_cov = self.annotation.label_coverage(other_label)
                other_xcov = other_cov.copy(segment_func=self.__xsegment)
                
                # are labels contiguous?
                if xcov & other_xcov:
                    self.__contiguous[label, other_label] = True
                    self.__contiguous[other_label, label] = True
                # False is the default value.
                # else:
                #     self.__contiguous[label, other_label] = False
                #     self.__contiguous[other_label, label] = False
    
    def _update_constraint(self, new_label, merged_labels):
        
        # remove rows and columns for old labels
        for label in merged_labels:
            if label == new_label:
                continue
            del self.__contiguous[label, :]
            del self.__contiguous[:, label]
        
        # extended coverage
        cov = self.annotation.label_coverage(new_label)
        xcov = cov.copy(segment_func=self.__xsegment)
        
        # update row and column for new label
        labels = self.annotation.labels()
        
        for label in labels:
            
            if label == new_label:
                continue
                
            # other extended coverage
            other_cov = self.annotation.label_coverage(label)
            other_xcov = other_cov.copy(segment_func=self.__xsegment)
                
            # are labels contiguous?
            contiguous = bool(xcov & other_xcov)
            self.__contiguous[new_label, label] = contiguous
            self.__contiguous[label, new_label] = contiguous
    
    def _meet_constraint(self, labels):
        for l, label in enumerate(labels):
            for other_label in labels[l+1:]:
                if not self.__contiguous[label, other_label]:
                    return False
        return True


import networkx as nx
import numpy as np
from pyannote.algorithm.util.modularity import Modularity
class IncreaseModularityConstraintMixin(BaseConstraintMixin):
    
    def _setup_constraint(self, **kwargs):
        pass
    
    def _initialize_constraint(self):
        g = nx.DiGraph()
        for i, j, s in self.similarity.iter_pairs(data=True):
            if s == -np.inf:
                continue
            g.add_edge(i, j, weight=np.maximum(0,s))
        self.__modularity = Modularity(g, weight='weight')
        self.__partition = {i:i for i in self.similarity.iter_ilabels()}
        self.__q = [self.__modularity(self.__partition)]
        
    def _update_constraint(self, new_label, merged_labels):
        for label in merged_labels:
            self.__partition[label] = new_label
        self.__q.append(self.__modularity(self.__partition))
    
    def _meet_constraint(self, labels):
        partition = dict(self.__partition)
        for label in labels:
            partition[label] = labels[0]
        q = self.__modularity(partition)
        return q > self.__q[-1]


# class XTagsConstraintMixin(BaseConstraintMixin):
#     
#     def _initialize_constraint(self, xtags=None, **kwargs):
#         """
#         """
#         
#         # keep track
#         self.__xtags = xtags
#         self.__conflicting_xtags = LabelMatrix(dtype=bool, default=False)
#         labels = self.annotation.labels()
#         for l, label in enumerate(labels):
#             
#             # set of tags intersecting label
#             cov = self.annotation.label_coverage(label)
#             tags = set(self.__xtags(cov, mode='loose').labels())
#             
#             for other_label in labels[l+1:]:
#                 
#                 # set of tags intersecting other label
#                 other_cov = self.annotation.label_coverage(other_label)
#                 other_tags = set(self.__xtags(other_cov, mode='loose').labels())
#                 
#                 # are there any tag conflicts?
#                 conflicting_xtags = bool(tags ^ other_tags)
#                 self.__conflicting_xtags[other_label, label] = conflicting_xtags
#                 self.__conflicting_xtags[label, other_label] = conflicting_xtags
#     
#     def _update_constraint(self, new_label, merged_labels):
#         
#         # remove rows and columns for old labels
#         for label in merged_labels:
#             if label == new_label:
#                 continue
#             del self.__conflicting_xtags[label, :]
#             del self.__conflicting_xtags[:, label]
#         
#         # set of tags intersecting new label
#         cov = self.annotation.label_coverage(new_label)
#         tags = set(self.__xtags(cov, mode='loose').labels())
#         
#         # update row and column for new label
#         labels = self.annotation.labels()
#         
#         for label in labels:
#             
#             if label == new_label:
#                 continue
#                 
#             # set of tags intersection other label
#             other_cov = self.annotation.label_coverage(label)
#             other_tags = set(self.__xtags(other_cov, mode='loose').labels())
#             
#             # are there any tag conflicts
#             conflicting_xtags = bool(tags ^ other_tags)
#             self.__conflicting_xtags[new_label, label] = conflicting_xtags
#             self.__conflicting_xtags[label, new_label] = conflicting_xtags
#     
#     def _meet_constraint(self, labels):
#         for l, label in enumerate(labels):
#             for other_label in labels[l+1:]:
#                 if self.__conflicting_xtags[label, other_label]:
#                     return False
#         return True
# 



if __name__ == "__main__":
    import doctest
    doctest.testmod()
