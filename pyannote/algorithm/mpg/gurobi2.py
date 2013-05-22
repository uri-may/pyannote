#!/usr/bin/env python
# encoding: utf-8

# Copyright 2013 Herve BREDIN (bredin@limsi.fr)

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


import sys
import numpy as np
import networkx as nx
from pyannote import Annotation, Unknown
from node import TrackNode, IdentityNode

# initialize Gurobi solver
try:
    # try to rely on the existing GRB_LICENSE_FILE variable first
    import gurobipy as grb
except:
    # otherwise, try hard-coded license file
    import os
    import socket
    pathToLicense = "%s/licenses/%s.lic" % (os.getenv('GUROBI_HOME'),
                                            socket.gethostname())
    os.putenv('GRB_LICENSE_FILE', pathToLicense)
    try:
        import gurobipy as grb
    except:
        sys.stderr.write('Cannot initialize Gurobi solver.')


class ILPClustering(object):
    """
    """
    def __init__(self):
        super(ILPClustering, self).__init__()

        # empty (silent) model
        self.model = grb.Model()
        self.model.setParam(grb.GRB.Param.OutputFlag, False)

        # empty set of variables
        self.x = {}

    # =================================================================
    # VARIABLES
    # =================================================================

    def add_pair_variables(self, items):
        """Add one variable per pair of items"""

        for I in items:
            for J in items:
                self.x[I, J] = self.model.addVar(vtype=grb.GRB.BINARY)
        self.model.update()

    # =================================================================
    # CONSTRAINTS
    # =================================================================

    def add_reflexivity_constraints(self, items):
        """Add reflexivity constraints (I~I, for all I)"""

        for I in items:
            constr = self.x[I, I] == 1
            self.model.addConstr(constr)

    def add_symmetry_constraints(self, items):
        """Add symmetry constratins

        For any pair (I, J), I~J implies J~I
        """

        N = len(items)
        for i in range(N):
            I = items[i]
            for j in range(i+1, N):
                J = items[j]
                constr = self.x[I, J] == self.x[J, I]
                self.model.addConstr(constr)

    def add_transitivity_constraints(self, items):
        """Add transitivity contraints

        For any triplet (I,J,K), I~J and J~K implies I~K
        """

        N = len(items)
        for i in range(N):
            I = items[i]
            for j in range(i+1, N):
                J = items[j]
                for k in range(j+1, N):
                    K = items[k]
                    constr = self.x[J, K]+self.x[I, K]-self.x[I, J] <= 1
                    self.model.addConstr(constr)
                    constr = self.x[I, J]+self.x[I, K]-self.x[J, K] <= 1
                    self.model.addConstr(constr)
                    constr = self.x[I, J]+self.x[J, K]-self.x[I, K] <= 1
                    self.model.addConstr(constr)

    def add_asymmetric_transitivity_constraints(self, tracks, identities):
        """Add asymmetric transitivity constraints

        For any pair of tracks (T, S) and any identity I,
            T~I and T~S implies S~I

        However, T~I and S~I does not imply T~S
        """

        Nt = len(tracks)
        Ni = len(identities)

        for i in range(Ni):
            I = identities[i]
            for t in range(Nt):
                T = tracks[t]
                for s in range(t+1, Nt):
                    S = tracks[s]
                    constr = self.x[T, I]+self.x[T, S]-self.x[S, I] <= 1
                    self.model.addConstr(constr)
                    constr = self.x[S, I]+self.x[T, S]-self.x[T, I] <= 1
                    self.model.addConstr(constr)

    def add_hard_constraints(self, items, similarity, get_similarity):
        """Add hard constraints

        If sim(I, J) = 0, then I|J.
        If sim(I, J) = 1, then I~J.
        """

        N = len(items)
        for i in range(N):
            I = items[i]
            for j in range(i+1, N):
                J = items[j]
                s = get_similarity(I, J, similarity)
                if s in [0, 1]:
                    constr = self.x[I, J] == s
                    self.model.addConstr(constr)

    def add_unique_identity_constraints(self, tracks, identities):
        """Add unique identity constraints

        For any track T, T is connected to at most one identity I
        """

        for T in tracks:
            constr = grb.quicksum([self.x[T, I] for I in identities]) <= 1
            self.model.addConstr(constr)

    # =================================================================
    # OBJECTIVE FUNCTIONS
    # =================================================================

    def get_inter_cluster_dissimilarity(self, items,
                                        similarity, get_similarity):
        """Inter-cluster dissimilarity:  ∑ (1-xij).(1-pij)
                                        i∈I
                                        j∈I
        """
        values = [(1-get_similarity(I, J, similarity))*(1-self.x[I, J])
                  for I in items for J in items
                  if not np.isnan(get_similarity(I, J, similarity))]
        return grb.quicksum(values)

    def get_intra_cluster_similarity(self, items,
                                     similarity, get_similarity):
        """Intra-cluster similarity: ∑  xij.pij
                                    i∈I
                                    j∈I
        """
        values = [get_similarity(I, J, similarity)*self.x[I, J]
                  for I in items for J in items
                  if not np.isnan(get_similarity(I, J, similarity))]
        return grb.quicksum(values)

    def get_bipartite_similarity(self, items, otherItems,
                                 similarity, get_similarity):
        """Bi-partite similarity: ∑  xij.pij
                                 i∈I
                                 j∈J
        """
        values = [get_similarity(I, J, similarity)*self.x[I, J]
                  for I in items for J in otherItems
                  if not np.isnan(get_similarity(I, J, similarity))]
        return grb.quicksum(values)

    def get_bipartite_dissimilarity(self, items, otherItems,
                                    similarity, get_similarity):
        """Bi-partite dissimilarity: ∑ (1-xij).(1-pij)
                                    i∈I
                                    j∈J
        """
        values = [(1-get_similarity(I, J, similarity))*(1-self.x[I, J])
                  for I in items for J in otherItems
                  if not np.isnan(get_similarity(I, J, similarity))]
        return grb.quicksum(values)

    def solve(self, init=None,
              method=None, mip_focus=None, heuristics=None,
              mip_gap=None, time_limit=None,
              threads=None, verbose=False):
        """
        Solve ILP problem

        Parameters
        ----------
        init : dict, optional
        method : {}, optional
        mip_focus : {}, optional
        heuristics : {}, optional
        mip_gap : float, optional
        time_limit : float, optional
            Time limit in seconds.
        threads : int, optional
        verbose : boolean, optional

        Returns
        -------
        solution : dict


        """

        # initial solution
        if init:
            for (I, J), variable in init.iteritems():
                self.x[I, J].start = variable

        # Gurobi behavior
        if method:
            self.model.setParam(grb.GRB.Param.Method, method)
        if mip_focus:
            self.model.setParam(grb.GRB.Param.MIPFocus, mip_focus)
        if heuristics:
            self.model.setParam(grb.GRB.Param.Heuristics, heuristics)

        # Stopping criteria
        if mip_gap:
            self.model.setParam(grb.GRB.Param.MIPGap, mip_gap)
        if time_limit:
            self.model.setParam(grb.GRB.Param.TimeLimit, time_limit)

        if threads:
            self.model.setParam(grb.GRB.Param.Threads, threads)

        self.model.setParam(grb.GRB.Param.OutputFlag, verbose)

        # Gurobi powaaaaa!
        self.model.optimize()

        # read solution
        solution = {}
        for key, variable in self.x.iteritems():
            solution[key] = variable.x

        return solution

    def to_annotation(self, solution, modality, uri):

        # convert solution to list of clusters
        c = nx.Graph()
        for (I, J), same_cluster in solution.iteritems():
            c.add_node(I),
            c.add_node(J)
            if same_cluster:
                c.add_edge(I, J)

        clusters = nx.connected_components(c)

        annotation = Annotation(uri=uri, modality=modality)
        for cluster in clusters:

            # obtain cluster identity
            inodes = [node for node in cluster
                      if isinstance(node, IdentityNode)]
            if len(inodes) > 1:
                raise ValueError('Cluster contains more than one identity.')
            if inodes:
                identity = inodes[0].identifier
            else:
                identity = Unknown()

            # obtain cluster tracks
            tnodes = [node for node in cluster if isinstance(node, TrackNode)
                      and node.uri == uri and node.modality == modality]

            for node in tnodes:
                annotation[node.segment, node.track] = identity

        return annotation

    def dump_model(self, path):
        """
        Dump Gurobi model to file (for debugging purpose)

        Parameters
        ----------
        path : str
            Where to dump Gurobi model

        """

        # model (lazy) update
        self.model.update()

        # dump to file
        self.model.write(path)


class Finkel2008(ILPClustering):
    """

    Maximize ∑  α.xij.pij + (1-α).(1-xij).(1-pij)
            i,j

    References
    ----------
    * "Enforcing Transitivity in Coreference Resolution"
      J.R. Finkel and C.D. Manning
      Annual Meeting of the Association for Computational Linguistics:
      Human Language Technologies (ACL HLT), 2008.
    * ""

    """

    def __init__(self, items, similarity, get_similarity, debug=False):

        super(Finkel2008, self).__init__()

        self.items = items
        self.similarity = similarity
        self.get_similarity = get_similarity

        # Variables
        self.add_pair_variables(self.items)

        # Constraints
        self.add_reflexivity_constraints(self.items)
        self.add_hard_constraints(self.items, self.similarity,
                                  self.get_similarity)
        self.add_symmetry_constraints(self.items)
        self.add_transitivity_constraints(self.items)

        self.model.update()

    def set_objective(self, alpha=0.5, **kwargs):
        """
        Set objective function

        Parameters
        ----------
        alpha : float, optional
            Set α in above equation (0 < α < 1)

        """

        intra = self.get_intra_cluster_similarity(self.items, self.similarity,
                                                  self.get_similarity)
        inter = self.get_inter_cluster_dissimilarity(self.items,
                                                     self.similarity,
                                                     self.get_similarity)
        self.model.setObjective(alpha*intra+(1-alpha)*inter, grb.GRB.MAXIMIZE)
        self.model.update()

# class DupuyConstraintMixin(object):
#     """

#     Dupuy et al. ...
#     """

#     def set_constraints(self, items, similarity, get_similarity,
#                         delta=0.5, **kwargs):
#         """

#         Parameters
#         ----------
#         items :

#         similarity :

#         get_similarity :

#         delta : float, optional
#             Prevent items with similarity lower than delta from ending
#             in the same cluster. Must fall in [0, 1] range.

#         """
#         # Equation 1.3 (in Dupuy et al., JEP'12)
#         # every item is associated to exactly one centroid
#         for J in items:
#             constr = grb.quicksum([self.x[C, J] for C in items]) == 1
#             self.model.addConstr(constr)

#         # Equation 1.4 (in Dupuy et al., JEP'12)
#         # prevent items from being associated to a dissimilar centroid
#         for C in items:
#             for I in items:
#                 sCI = get_similarity(C, I, similarity)
#                 if np.isnan(sCI):
#                     continue
#                 constr = (1-sCI) * self.x[C, I] <= (1-delta)
#                 self.model.addConstr(constr)

#         # Equation 1.5 (missing in Dupuy et al.)
#         # activate a centroid as soon as an item is associated to it
#         for C in items:
#             for I in items:
#                 constr = self.x[C, C] >= self.x[C, I]
#                 self.model.addConstr(constr)

#         # model (lazy) update
#         self.model.update()

#         return self


# class DupuyObjectiveMixin(object):
#     """

#     """

#     def set_objective(self, items, similarity, get_similarity, **kwargs):
#         """

#         """

#         # number of items
#         N = len(items)

#         # number of activated centroids
#         centroids = grb.quicksum([self.x[C, C] for C in items])

#         # cluster cohesion (ie total similarity to centroids)
#         cohesion = grb.quicksum([get_similarity(C, I, similarity)*self.x[C, I]
#                                  for C in items for I in items if C != I])

#         # according to a discussion I had with Mickael Rouvier,
#         # F (in Dupuy et al. 2012) is actually the sum over all items
#         # of the maximum distance to all other items
#         # in short, F = N

#         # minimize both number of centroids and dispersion
#         self.model.setObjective(centroids - 1./N * cohesion, grb.GRB.MINIMIZE)

#         # model (lazy) update
#         self.model.update()

#         return self
