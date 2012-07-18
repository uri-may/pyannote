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


from pyannote.algorithm.clustering.agglomerative.base import MatrixIMx, AgglomerativeClustering
from pyannote.algorithm.clustering.model import BICMMx
from pyannote.algorithm.clustering.agglomerative.constraint import ContiguousCMx
from pyannote.algorithm.clustering.agglomerative.stop import NegativeSMx, MaximumModularitySMx

class BICClustering(AgglomerativeClustering, MatrixIMx, BICMMx, NegativeSMx):
    """
    BIC clustering
    
    Parameters
    ----------
    covariance_type : {'full', 'diag'}, optional
        Full or diagonal covariance matrix. Default is 'full'.
    penalty_coef : float, optional
        Coefficient of model size penalty. Default is 3.5.
        
    Examples
    --------
        
        >>> clustering = BICClustering()
        >>> annotation = Annotation(...)
        >>> feature = PrecomputedPeriodicFeature( ... )
        >>> new_annotation = clustering(annotation, feature)
        
    """
    
    def __init__(self, covariance_type='full', penalty_coef=3.5):
        super(BICClustering, self).__init__(covariance_type=covariance_type,
                                            penalty_coef=penalty_coef)


class QBICClustering(AgglomerativeClustering, MatrixIMx, BICMMx, MaximumModularitySMx):
    
    def __init__(self, covariance_type='full', penalty_coef=3.5):
        super(QBICClustering, self).__init__(covariance_type=covariance_type,
                                             penalty_coef=penalty_coef,
                                             edge_threshold=0.0)


class BICRecombiner(BICClustering, ContiguousCMx):
    """
    Recombine contiguous segments based on BIC criterion.
    
    Parameters
    ----------
    covariance_type : {'full', 'diag'}, optional
        Full or diagonal covariance matrix. Default is 'diag'.
    penalty_coef : float, optional
        Coefficient for model size penalty. Default is 3.5.
    tolerance : float, optional
        Temporal tolerance for notion of 'contiguous' segments, in seconds.
        Default is 500ms.
        
    Examples
    --------
        
        >>> clustering = BICClustering()
        >>> annotation = Annotation(...)
        >>> feature = PrecomputedPeriodicFeature( ... )
        >>> new_annotation = clustering(annotation, feature)
    
    """
    def __init__(self, covariance_type='diag', penalty_coef=3.5, tolerance=0.5, 
                       **kwargs):
        super(BICRecombiner, self).__init__(covariance_type=covariance_type, 
                                            penalty_coef=penalty_coef,
                                            tolerance=tolerance, **kwargs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
  