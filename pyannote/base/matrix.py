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

import numpy as np
import warnings

class LabelMatrix(object):
    """
    2D-matrix indexed by labels.
    
    Parameters
    ----------
    ilabels, jlabels : list of labels, optional
    Mij : NumPy array, optional
    default : float, optional
    
    Returns
    -------
    matrix : LabelMatrix
    
    """
    def __init__(self, ilabels=None, jlabels=None, Mij=None, default=0.):
        super(LabelMatrix, self).__init__()
        
        # -- ilabels
        if ilabels is None:
            self.__ilabels = []
        elif isinstance(ilabels, list):
            self.__ilabels = list(ilabels)
        else:
            raise ValueError('')
                
        # -- jlabels
        if jlabels is None:
            self.__jlabels = []
        elif isinstance(jlabels, list):
            self.__jlabels = list(jlabels)
        else:
            raise ValueError('')
        
        # --
        self.__label2i = {ilabel:i for i, ilabel in enumerate(self.__ilabels)}
        self.__label2j = {jlabel:j for j, jlabel in enumerate(self.__jlabels)}
        
        # --
        self.__default = default
        
        # --
        ni = len(self.__ilabels)
        nj = len(self.__jlabels)
        
        if Mij is None:
            if ni or nj:
                self.__Mij = self.__default * np.ones((ni, nj))
            else:
                self.__Mij = None
        else:
            self.__Mij = np.array(Mij)
            Ni, Nj = self.__Mij.shape
            if (ni, nj) != (Ni, Nj):
                raise ValueError('%d x %d matrix is expected (got %d x %d).' % \
                                 (ni, nj, Ni, Nj))
    
    def __get_default(self):
        return self.__default
    default = property(fget=__get_default)
    """Default value"""
    
    def __get_T(self): 
        return LabelMatrix(self.__jlabels, self.__ilabels, self.__Mij.T)
    T = property(fget=__get_T)
    """Transposed co-matrix"""
    
    def __get_shape(self):
        if self.__Mij is None:
            return 0, 0
        else:
            return self.__Mij.shape
    shape = property(fget=__get_shape)
    """Matrix shape"""
    
    def __get_M(self):
        return self.__Mij
    def __set_M(self, M):
        if M.shape != self.shape:
            raise ValueError('Shape mismatch %s %s' % (self.shape, M.shape))
        self.__Mij = M
    M = property(fget=__get_M, fset=__set_M)
    "Matrix as Numpy array"
                 
    def __get_labels(self):
        return self.__ilabels, self.__jlabels
    labels = property(fget=__get_labels)
    """Matrix labels"""
    
    def __getitem__(self, key):
        """"""
        if isinstance(key, tuple) and len(key) == 2:
            
            ilabel = key[0]
            jlabel = key[1]
            
            if isinstance(ilabel, (tuple, list, set)) and \
               isinstance(jlabel, (tuple, list, set)):
                C = LabelMatrix(default=self.default)
                ilabels = sorted(ilabel)
                jlabels = sorted(jlabel)
                for ilabel in ilabels:
                    for jlabel in jlabels:
                        C[ilabel, jlabel] = self[ilabel, jlabel]
                return C
            else:            
                if ilabel in self.__label2i and \
                   jlabel in self.__label2j:
                    return self.__Mij[self.__label2i[ilabel], \
                                      self.__label2j[jlabel]]
                else:
                    return self.default
        else:
            raise KeyError('')
    
    # =================================================================== #
    
    def __add_ilabel(self, ilabel):
        n, m = self.shape
        self.__ilabels.append(ilabel)
        self.__label2i[ilabel] = n        
        self.__Mij = np.append(self.__Mij, \
                               self.default*np.ones((1, m)), \
                               axis=0)

    # ------------------------------------------------------------------- #

    def __add_jlabel(self, jlabel):
        n, m = self.shape
        self.__jlabels.append(jlabel)
        self.__label2j[jlabel] = m
        self.__Mij = np.append(self.__Mij, \
                               self.default*np.ones((n, 1)), \
                               axis=1)
        
    # ------------------------------------------------------------------- #
    
    def __setitem__(self, key, value):
        """
        
        Use expression 'matrix[label_i, label_j] = value
        
        """
        if isinstance(key, tuple) and len(key) == 2:
            
            ilabel = key[0]
            jlabel = key[1]
            
            if isinstance(ilabel, (tuple, list, set)) or \
               isinstance(jlabel, (tuple, list, set)):
                raise ValueError('')
            
            if self.__Mij is None:
                self.__ilabels.append(ilabel)
                self.__jlabels.append(jlabel)
                self.__label2i[ilabel] = 0
                self.__label2j[jlabel] = 0
                self.__Mij = value * np.ones((1,1))
            else:
                if ilabel not in self.__label2i:
                    self.__add_ilabel(ilabel)
                if jlabel not in self.__label2j:
                    self.__add_jlabel(jlabel)
                i = self.__label2i[ilabel]
                j = self.__label2j[jlabel]
                self.__Mij[i, j] = value
        
        else:
            raise KeyError('')
    
    def __delitem__(self, key):
        raise NotImplementedError('')
    
    def iter_ilabels(self, index=False):
        """
        
        """
        for ilabel in self.__ilabels:
            if index:
                yield self.__label2i[ilabel], ilabel
            else:
                yield ilabel
    
    def iter_jlabels(self, index=False):
        for jlabel in self.__jlabels:
            if index:
                yield self.__label2j[jlabel], jlabel
            else:
                yield jlabel
    
    def iter_pairs(self, data=False):
        for ilabel in self.__ilabels:
            for jlabel in self.__jlabels:
                if data:
                    yield ilabel, jlabel, self[ilabel, jlabel]
                else:
                    yield ilabel, jlabel
    
    # ------------------------------------------------------------------- #
    
    def copy(self):
        """Duplicate matrix.
        
        """
        ilabels, jlabels = self.labels
        C = LabelMatrix(list(ilabels), list(jlabels), \
                     np.copy(self.M), default=self.default)
        return C
    
    # ------------------------------------------------------------------- #

    def __neg__(self):
        ilabels, jlabels = self.labels
        C = LabelMatrix(list(ilabels), list(jlabels), -np.copy(self.M), \
                     default=-self.default)
        return C
    
    # ------------------------------------------------------------------- #

    def __iadd__(self, other):

        if self.default != other.default:
            warnings.warn('Incompatible default value. Uses %g.' % self.default)

        for ilabel, jlabel, value in other.iter_pairs(data=True):
            self[ilabel, jlabel] += value
        
        return self 

    # ------------------------------------------------------------------- #

    def __add__(self, other):
        C = self.copy()        
        C += other
        return C
    
    def argmax(self, axis=None, threshold=None, ties='all'):
        """
        
        :param axis:
        :type axis: 0, 1 or None
        
        :param threshold: threshold on maximum value
        :type threshold: float

        In case :data:`threshold` is provided and is higher than maximum value,
        then, returns an empty list.

        :param ties: tie handling -- keep all or just one?
        :type ties: 'all' (default) or 'any'
        
        :returns: dictionary of label pairs corresponding to maximum value in matrix.
                
        >>> C = Cooccurrence(A, B)
        >>> pairs = C.argmax(axis=0)
        >>> for a in A.labels():
        ...    if a in pairs:
        ...        print '%s --> %s' % (a, pairs[a])
        
        """
        
        if axis == 0:
            pairs = {}
            for i, ilabel in self.iter_ilabels(index=True):
                M = self.M[i,:]
                m = np.max(M)
                if threshold is None or m > threshold:
                    pairs[ilabel] = set([self.__jlabels[j[0]] \
                                         for j in np.argwhere(M == m)])
                else:
                    pairs[ilabel] = set([])
                if ties == 'any' and len(pairs[ilabel]) > 1:
                    pairs[ilabel] = set([pairs[ilabel].pop()])
            return pairs
        elif axis == 1:
            return self.T.argmax(axis=0, threshold=threshold)
            # pairs = {}
            # for j, jlabel in self.iter_jlabels(index=True):
            #     M = self.M[:,j]
            #     m = np.max(M)
            #     if threshold is None or m > threshold:
            #         pairs[jlabel] = set([self.__ilabels[i[0]] \
            #                              for i in np.argwhere(M == m)])
            #     else:
            #         pairs[jlabel] = set([])
            # return pairs
        else:
            m = np.max(self.M)
            if (threshold is None) or (m > threshold):
                pairs = np.argwhere(self.M == m)
            else:
                pairs = []
            return set([(self.__ilabels[i], self.__jlabels[j]) \
                        for i, j in pairs])
    
    def argmin(self, axis=None, threshold=None, ties='all'):
        return (-self).argmax(axis=axis, threshold=-threshold)
    
    def __str__(self):
        
        ilabels, jlabels = self.labels
        
        len_i = max([len(label) for label in ilabels])
        len_j = max(4, max([len(label) for label in jlabels]))
        
        fmt_label_i = "%%%ds" % len_i 
        fmt_label_j = "%%%ds" % len_j
        fmt_value = "%%%d.2f" % len_j
        
        string = fmt_label_i % " "
        string += " "
        string += " ".join([fmt_label_j % j for j in jlabels])
        
        for i in ilabels:
            string += "\n"
            string += fmt_label_i % i
            string += " "
            string += " ".join([fmt_value % self[i, j] for j in jlabels])
        
        return string

class Cooccurrence(LabelMatrix):
    """
    Cooccurrence matrix between two annotations
    
    Parameters
    ----------
    I, J : Annotation
    
    Returns
    --------
    matrix : Cooccurrence
        
    
    Examples
    --------
    
    >>> M = Cooccurrence(A, B)

    Get total confusion duration (in seconds) between id_A and id_B::
    
    >>> confusion = M[id_A, id_B]
    
    Get confusion dictionary for id_A::
    
    >>> confusions = M(id_A)
    
    """
    def __init__(self, I, J):
                
        n_i = len(I.labels())
        n_j = len(J.labels())
        Mij = np.zeros((n_i, n_j))
        super(Cooccurrence, self).__init__(I.labels(), J.labels(), Mij, default=0.)
                
        ilabels, jlabels = self.labels
        
        for i, ilabel in self.iter_ilabels(index=True):
            i_coverage = I(ilabel).timeline.coverage()
            
            for j, jlabel in self.iter_jlabels(index=True):
                j_coverage = J(jlabel).timeline.coverage()
                # self[ilabel, jlabel] = i_coverage(j_coverage, \
                #                               mode='intersection').duration()
                super(Cooccurrence, self).__setitem__((ilabel, jlabel), \
                i_coverage(j_coverage, mode='intersection').duration())
    
    def __setitem__(self, key, value):
        raise NotImplementedError('')
    
    def __delitem__(self, key):
        raise NotImplementedError('')


from pyannote.base.segment import SEGMENT_PRECISION
class CoTFIDF(Cooccurrence):
    """Term Frequency Inverse Document Frequency (TF-IDF) confusion matrix
    
    C[i, j] = TF(i, j) x IDF(i) where
        - documents are J labels
        - words are co-occurring I labels
    
                  duration of word i in document j         confusion[i, j]
    TF(i, j) = --------------------------------------- = -------------------
               total duration of I words in document j   sum confusion[:, j]
               
                        number of J documents                     
    IDF(i) = ---------------------------------------------- 
             number of J documents co-occurring with word i   
           
                      Nj
           = -----------------------
             sum confusion[i, :] > 0
    
    Parameters
    ---------
    words : :class:`pyannote.base.annotation.Annotation`
        Every label occurrence is considered a word 
        (weighted by the duration of the segment)
    documents : :class:`pyannote.base.annotation.Annotation`
        Every label is considered a document.
    idf : bool, optional
        If `idf` is set to True, returns TF x IDF.
        Otherwise, returns TF. Default is True
    log : bool, optional
        If `log` is True, returns TF x log IDF
    
    """
    def __init__(self, words, documents, idf=True, log=False):
        
        # initialize as co-occurrence matrix
        super(CoTFIDF, self).__init__(words, documents)
        Nw, Nd = self.shape
        
        # total duration of all words cooccurring with each document
        # np.sum(self.M, axis=0)[j] = 0 ==> self.M[i, j] = 0 for all i 
        # so we can safely use np.maximum(1e-3, ...) to avoid DivideByZero
        tf = self.M / np.tile(np.maximum(SEGMENT_PRECISION, \
                                         np.sum(self.M, axis=0)), (Nw, 1))
        
        # use IDF only if requested (default is True ==> use IDF)
        if idf:
            
            # number of documents cooccurring with each word
            # np.sum(self.M > 0, axis=1)[i] = 0 ==> tf[i, j] = 0 for all i
            # and therefore tf.idf [i, j ] = 0
            # so we can safely use np.maximum(1, ...) to avoid DivideByZero
            idf = np.tile(float(Nd)/np.maximum(1, np.sum(self.M > 0, axis=1)), \
                          (Nd, 1)).T
            
            # use log only if requested (defaults is False ==> do not use log)
            if log:
                idf = np.log(idf)

        else:
            idf = 1.
        
        self.M = tf * idf
        

class AutoCooccurrence(Cooccurrence):
    """
    Auto confusion matrix 
    
    Parameters
    ----------
    I : Annotation
    
    neighborhood : float, optional
    
    Examples
    --------
    
    >>> M = AutoCooccurrence(A, neighborhood=10)
    
    Get total confusion duration (in seconds) between id_A and id_B::
    
    >>> confusion = M[id_A, id_B]
    
    Get confusion dictionary for id_A::
    
    >>> confusions = M(id_A)
    
    
    """
    def __init__(self, I, neighborhood=0.):
        
        # extend each segment on left and right by neighborhood seconds
        segment_func = lambda s : neighborhood << s >> neighborhood
        xI = I.copy(segment_func=map_func)
        
        # auto-cooccurrence
        super(AutoCooccurrence, self).__init__(xI, xI)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

