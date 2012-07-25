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

class BaseModelMixin(object):
    """
    Clustering model mixin
    
    """
    def mmx_setup(self, **kwargs):
        """
        Setup model internal variables
        """
        pass
    
    def mmx_fit(self, label, **kwargs):
        """
        Create model
        
        Parameters
        ----------
        label : any valid label
            The `label` to model
        
        Returns
        -------
        model : any object
            The model for `label`
        
        """
        name = self.__class__.__name__
        raise NotImplementedError('%s sub-class must implement method'
                                  'mmx_fit()' % name)
    
    def mmx_symmetric(self):
        """
        Is model similarity symmetric?
        
        Returns
        -------
        symmetric: bool
            True if similarity is symmetric, False otherwise.
        
        """
        return False
    
    def mmx_compare(self, label, other_label, **kwargs):
        """
        Similarity between two labels
        
        Parameters
        ----------
        label, other_label : any valid label
            The labels to compare
            
        Returns
        -------
        similarity : float
            Similarity between the two labels, the higher the more similar
        
        """
        name = self.__class__.__name__
        raise NotImplementedError('%s sub-class must implement method'
                                  'mmx_compare()' % name)
    
    def mmx_merge(self, labels, **kwargs):
        """
        Merge models
        
        Parameters
        ----------
        labels : list of valid labels
            The labels whose models should be merged
            
        Returns
        -------
        model : any object
            The merged models
        
        """
        name = self.__class__.__name__
        raise NotImplementedError('%s sub-class must implement method'
                                  'mmx_merge()' % name)


import pyfusion.normalization.bayes
import numpy as np
class PosteriorMixin(object):
    
    def _get_X(self, annotation, feature):
        
        # one model per label
        models = {label : self.mmx_fit(label, annotation=annotation,
                                              feature=feature)
                  for label in annotation.labels()}
        
        # total number of tracks
        N = len([_ for _ in annotation.iterlabels()])
        
        # similarity between tracks
        X = np.empty((N, N), dtype=np.float32)
        for i, (_, _, Li) in enumerate(annotation.iterlabels()):
            for j, (_, _, Lj) in enumerate(annotation.iterlabels()):
                if self.mmx_symmetric() and j > i:
                    break
                X[i, j] = self.mmx_compare(Li, Lj, models=models)
                if self.mmx_symmetric():
                    X[j, i] = X[i, j]
        
        return X
    
    def _get_y(self, annotation):
        
        # total number of tracks
        N = len([_ for _ in annotation.iterlabels()])
        
        # intialize clustering status as -1 (unknown)
        y = -np.ones((N,N), dtype=np.int8)
        
        for i, (Si, _, Li) in enumerate(annotation.iterlabels()):
            
            # if more than one track -- don't know which is which
            if len(annotation[Si, :]) > 1:
                y[i, :] = -1
                y[:, i] = -1
            
            for j, (Sj, _, Lj) in enumerate(annotation.iterlabels()):
                if j > i:
                    break
                if len(annotation[Sj, :]) > 1:
                    y[:, j] = -1
                    y[j, :] = -1
                    continue
                y[i, j] = (Li == Lj)
                y[j, i] = y[i, j]
        
        return y
        
    def fit_posterior(self, annotations, features, **kwargs):
        """
        Train posterior
        
        Parameters
        ----------
        annotations : list of :class:`Annotation`
        features : list of :class:`Feature`
        
        """
        
        self.posterior = pyfusion.normalization.bayes.Posterior(pos_label=1,
                                                                neg_label=0,
                                                                parallel=False)
                                                                
        X = np.concatenate([self._get_X(annotation, features[a]).reshape((-1,1))
                            for a, annotation in enumerate(annotations)])
        y = np.concatenate([self._get_y(annotation).reshape((-1, 1)) 
                            for a, annotation in enumerate(annotations)])
        self.posterior.fit(X, y=y)
    
    def transform_posterior(self, S):
        """
        
        Parameters
        ----------
        S : 
            Similarity matrix
        
        Returns
        -------
        P : 
            Probability matrix
        
        """
        
        return self.posterior.transform(S.reshape((-1, 1))).reshape(S.shape)
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
