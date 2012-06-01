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

"""This module defines constraint mixin (CMx) for agglomerative clustering.

    A ConstraintMixin (CMx) must implement the following methods:
    
    * cmx_setup(**kwargs)
    * cmx_init(**kwargs)
    * cmx_update(new_label, old_labels)
    * cmx_meet(labels)

"""

from pyannote.algorithm.clustering.base import BaseConstraintMixin

from pyannote.base.matrix import LabelMatrix
class ContiguousCMx(BaseConstraintMixin):
    """
    Two labels are mergeable if they are contiguous
    """
    
    def cmx_setup(self, tolerance=0., **kwargs):
        self.cmx_tolerance = tolerance
        self.cmx_xsegment = lambda s: .5*tolerance << s >> .5*tolerance
    
    def cmx_init(self, **kwargs):
        """
        Two labels are mergeable if they are contiguous
        """
        
        self.cmx_contiguous = LabelMatrix(dtype=bool, default=False)
        labels = self.annotation.labels()
        for l, label in enumerate(labels):
            
            # extended coverage
            cov = self.annotation.label_coverage(label)
            xcov = cov.copy(segment_func=self.cmx_xsegment)
            
            for other_label in labels[l+1:]:
                
                # other extended coverage
                other_cov = self.annotation.label_coverage(other_label)
                other_xcov = other_cov.copy(segment_func=self.cmx_xsegment)
                
                # are labels contiguous?
                if xcov & other_xcov:
                    self.cmx_contiguous[label, other_label] = True
                    self.cmx_contiguous[other_label, label] = True
                # False is the default value.
                # else:
                #     self.cmx_contiguous[label, other_label] = False
                #     self.cmx_contiguous[other_label, label] = False
    
    def cmx_update(self, new_label, merged_labels):
        
        # remove rows and columns for old labels
        for label in merged_labels:
            if label == new_label:
                continue
            del self.cmx_contiguous[label, :]
            del self.cmx_contiguous[:, label]
        
        # extended coverage
        cov = self.annotation.label_coverage(new_label)
        xcov = cov.copy(segment_func=self.cmx_xsegment)
        
        # update row and column for new label
        labels = self.annotation.labels()
        
        for label in labels:
            
            if label == new_label:
                continue
                
            # other extended coverage
            other_cov = self.annotation.label_coverage(label)
            other_xcov = other_cov.copy(segment_func=self.cmx_xsegment)
                
            # are labels contiguous?
            contiguous = bool(xcov & other_xcov)
            self.cmx_contiguous[new_label, label] = contiguous
            self.cmx_contiguous[label, new_label] = contiguous
    
    def cmx_meet(self, labels):
        for l, label in enumerate(labels):
            for other_label in labels[l+1:]:
                if not self.cmx_contiguous[label, other_label]:
                    return False
        return True


import networkx as nx
import numpy as np
from pyannote.algorithm.util.modularity import Modularity
from pyannote.algorithm.clustering.base import MatrixIMx
class IncreaseModularityCMx(BaseConstraintMixin):
    
    def cmx_setup(self, **kwargs):
        if not isinstance(self, MatrixIMx):
            raise ValueError('IncreaseModularityCMx requires MatrixIMx.')
    
    def cmx_init(self):
        g = nx.DiGraph()
        for i, j, s in self.imx_similarity.iter_pairs(data=True):
            if s == -np.inf:
                continue
            g.add_edge(i, j, weight=s)
        self.cmx_modularity = Modularity(g, weight='weight')
        self.cmx_partition = {i:i for i in self.imx_similarity.iter_ilabels()}
        self.cmx_q = [self.cmx_modularity(self.cmx_partition)]
        
    def cmx_update(self, new_label, merged_labels):
        for label in merged_labels:
            self.cmx_partition[label] = new_label
        self.cmx_q.append(self.cmx_modularity(self.cmx_partition))
    
    def cmx_meet(self, labels):
        partition = dict(self.cmx_partition)
        for label in labels:
            partition[label] = labels[0]
        q = self.cmx_modularity(partition)
        return q > self.cmx_q[-1]


# class XTagsCMx(BaseConstraintMixin):
#     
#     def cmx_init(self, xtags=None, **kwargs):
#         """
#         """
#         
#         # keep track
#         self.cmx_xtags = xtags
#         self.cmx_conflicting_xtags = LabelMatrix(dtype=bool, default=False)
#         labels = self.annotation.labels()
#         for l, label in enumerate(labels):
#             
#             # set of tags intersecting label
#             cov = self.annotation.label_coverage(label)
#             tags = set(self.cmx_xtags(cov, mode='loose').labels())
#             
#             for other_label in labels[l+1:]:
#                 
#                 # set of tags intersecting other label
#                 other_cov = self.annotation.label_coverage(other_label)
#                 other_tags = set(self.cmx_xtags(other_cov, mode='loose').labels())
#                 
#                 # are there any tag conflicts?
#                 conflicting_xtags = bool(tags ^ other_tags)
#                 self.cmx_conflicting_xtags[other_label, label] = conflicting_xtags
#                 self.cmx_conflicting_xtags[label, other_label] = conflicting_xtags
#     
#     def cmx_update(self, new_label, merged_labels):
#         
#         # remove rows and columns for old labels
#         for label in merged_labels:
#             if label == new_label:
#                 continue
#             del self.cmx_conflicting_xtags[label, :]
#             del self.cmx_conflicting_xtags[:, label]
#         
#         # set of tags intersecting new label
#         cov = self.annotation.label_coverage(new_label)
#         tags = set(self.cmx_xtags(cov, mode='loose').labels())
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
#             other_tags = set(self.cmx_xtags(other_cov, mode='loose').labels())
#             
#             # are there any tag conflicts
#             conflicting_xtags = bool(tags ^ other_tags)
#             self.cmx_conflicting_xtags[new_label, label] = conflicting_xtags
#             self.cmx_conflicting_xtags[label, new_label] = conflicting_xtags
#     
#     def cmx_meet(self, labels):
#         for l, label in enumerate(labels):
#             for other_label in labels[l+1:]:
#                 if self.cmx_conflicting_xtags[label, other_label]:
#                     return False
#         return True
# 



if __name__ == "__main__":
    import doctest
    doctest.testmod()
