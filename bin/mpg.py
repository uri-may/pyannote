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

import sys
import pickle
import networkx as nx
import numpy as np

from argparse import ArgumentParser, SUPPRESS
from pyannote import clicommon
from pyannote.algorithm.clustering.optimization.graph import *

argparser = ArgumentParser(parents=[clicommon.parser],
                           description='Multimodal Probability Graph')

from pyannote.parser import AnnotationParser
def mm_parser(path):
    """Speaker diarization & face clustering source annotation
    
    Parameters
    ----------
    path : str
        Path to source annotation (may contain [URI] placeholder)
    
    Returns
    -------
    annotation_generator : func or AnnotationParser
        callable (e.g. annotation_generator(uri)) object 
        that returns the annotation for a given resource.
    
    """
    if clicommon.containsURI(path):
        return lambda u: AnnotationParser()\
                         .read(clicommon.replaceURI(path, u), uri=u)(u)
    else:
        return AnnotationParser().read(path)

def ss_param_parser(param_pkl):
    """Speaker diarization
    
    - [L] label nodes
    - [T] track nodes
    - [L] -- [L] soft edges
    - [T] == [L] hard edges
    
    Parameters
    ----------
    param_pkl : str
        Path to 'param.pkl' parameter file.
        
    Returns
    -------
    graph_generator : LabelSimilarityGraph
        callable (e.g. graph_generator(annotation, feature)) object 
        that returns a label similarity graph [L] -- [L] augmented
        with a diarization graph [T] == [L]
    """
    
    with open(param_pkl, 'r') as f:
        params = pickle.load(f)
    
    mmx = params.pop('__mmx__')
    s2p = params.pop('__s2p__')
    
    class SSGraph(LabelSimilarityGraph, mmx):
        def __init__(self):
            super(SSGraph, self).__init__(s2p=s2p, **params)
    
    ssGraph = SSGraph()
    diarizationGraph = DiarizationGraph()
    
    def graph_generator(annotation, feature):
        G = ssGraph(annotation, feature) # [L] -- [L] edges
        g = diarizationGraph(annotation) # [T] == [L] edges
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
        return G
    
    return graph_generator

from pyannote.parser import PLPParser
def ss_plp_parser(path):
    """PLP feature loader
    
    Parameters
    ----------
    path : str
        Path to PLP feature file (with [URI] placeholder)
    
    Returns
    -------
    load_plp : func
        function that takes uri as unique argument and returns PLP features
    
    """
    def load_plp(uri):
        return PLPParser().read(clicommon.replaceURI(path, uri))
    
    return load_plp

def si_parser(path):
    """Speaker identification scores
    
    Parameters
    ----------
    path : str
        Path to speaker identification scores
        
    Returns
    -------
    load_scores : func or ScoresParser
        callable that takes uri as unique argument and return speaker
        identification scores as Panda MultiIndex (segment/track) DataFrame
    """
    if clicommon.containsURI(path):
        return lambda u: AnnotationParser()\
                         .read(clicommon.replaceURI(path, u), uri=u)(u)
    else:
        return AnnotationParser().read(path)

def si_param_parser(param_pkl):
    """Speaker identification graph
    
    - [T] track nodes
    - [I] identity nodes
    - [T] -- [I] soft edges
    
    Parameters
    ----------
    param_pkl : str
        Path to 'param.pkl' parameter file.
        
    Returns
    -------
    graph_generator : ScoresGraph
        callable (e.g. graph_generator(annotation, feature)) object 
        that returns a label similarity graph
    """
    
    with open(param_pkl, 'r') as f:
        params = pickle.load(f)
    
    s2p = params.pop('__s2p__')
    
    class SIGraph(ScoresGraph):
        def __init__(self):
            super(SIGraph, self).__init__(s2p=s2p, **params)
    
    return SIGraph()


from pyannote.algorithm.clustering.model import PrecomputedMMx
def hh_param_parser(param_pkl):
    """Face clustering
    
    Parameters
    ----------
    param_pkl : str or None
        Path to 'param.pkl' parameter file.
        
    Returns
    -------
    graph_generator : LabelSimilarityGraph
        callable (e.g. graph_generator(annotation, feature)) object 
        that returns a label similarity graph
    """
    
    if param_pkl is None:
        class HHGraph(LabelSimilarityGraph, PrecomputedMMx):
            def __init__(self):
                super(HHGraph, self).__init__()
        
        graph_generator = HHGraph()
    else:
        with open(param_pkl, 'r') as f:
            params = pickle.load(f)
    
        mmx = params.pop('__mmx__')
        func = params.pop('__s2p__')
    
        class HHGraph(LabelSimilarityGraph, mmx):
            def __init__(self):
                super(HHGraph, self).__init__(func=func, **params)
    
        graph_generator = HHGraph()
    
    return graph_generator


from pyannote.parser import LabelMatrixParser
def hh_precomputed_parser(path):
    """Precomputed similarity matrix loader
    
    Parameters
    ----------
    path : str
        Path to precomputed matrices (with [URI] placeholder)
    
    Returns
    -------
    load_matrix : func
        function that takes uri as unique argument and returns matrix
    
    """
    
    def load_matrix(uri):
        return LabelMatrixParser().read(clicommon.replaceURI(path, uri))
    
    return load_matrix
    
def hi_parser(path):
    raise NotImplementedError('--hi option is not supported yet.')

def hi_param_parser(path):
    raise NotImplementedError('--hi-param option is not supported yet.')

def wi_parser(path):
    """Written name detection source
    
    Parameters
    ----------
    path : str
        Path to written name detection source
    
    Returns
    -------
    annotation_generator : AnnotationParser
        callable (e.g. annotation_generator(uri)) object
        that returns the annotation for a given resource
    
    """
    return AnnotationParser().read(path)

def wi_param_parser(path):
    """Written names
    
    - [T] track nodes
    - [I] identity nodes
    - [T] == [I] hard edges
    
    """
    if path is None:
        graph_generator = AnnotationGraph()
    else:
        raise NotImplementedError('--wi-param option is not supported yet.')
    return graph_generator

def ni_parser(path):
    raise NotImplementedError('--ni option is not supported yet.')

def ni_param_parser(path):
    raise NotImplementedError('--ni-param option is not supported yet.')

def x_param_parser(param_pkl):
    """Cross-modal graph
    
    - [t1] sub-track nodes (first modality)
    - [t2] sub-track nodes (second modality)
    - [t1] -- [t2] soft edges
    
    - [T1] track nodes (first modality)
    - [T2] track nodes (second modality)
    - [t1] == [T1] hard edges
    - [t2] == [T2] hard edges
    
    Parameters
    ----------
    param_pkl : str
        Path to 'param.pkl' parameter file
    
    Returns
    -------
    graph_generator : TrackCooccurrenceGraph
        callable (e.g. graph_generator(speaker, head)) object 
        that returns a label cooccurrence graph
    
    """
    with open(param_pkl, 'r') as f:
        params = pickle.load(f)
    
    tcg = TrackCooccurrenceGraph(**params)
    
    def xgraph(src1, src2):
        modA = tcg.modalityA
        modB = tcg.modalityB
        mod1 = src1.modality
        mod2 = src2.modality
        if mod1 == modA and mod2 == modB:
            return tcg(src1, src2)
        elif mod1 == modB and mod2 == modA:
            return tcg(src2, src1)
        else:
            msg = 'Crossmodal graph modality mismatch [%s/%s] vs. [%s/%s].' \
                  % (modA, modB, mod1, mod2)
            raise IOError(msg)
        
    return xgraph


msg = "path where to store multimodal probability graph." + clicommon.msgURI()
argparser.add_argument('output', type=str, metavar='graph.pkl', help=msg)

# == Speaker ==
sgroup = argparser.add_argument_group('[speaker] modality')

# Speaker diarization

msg = "path to source for speaker diarization. " + clicommon.msgURI()
sgroup.add_argument('--ss', type=mm_parser, metavar='source.mdtm', 
                    default=SUPPRESS, help=msg)

sgroup.add_argument('--ss-param', metavar='param.pkl', 
                    type=ss_param_parser, dest='ssgraph', default=SUPPRESS,
                    help='path to trained parameters for speaker diarization')

msg = "path to PLP feature files." + clicommon.msgURI()
sgroup.add_argument('--ss-plp', type=ss_plp_parser, metavar='uri.plp', help=msg)

# Speaker identification

sgroup.add_argument('--si', type=si_parser, metavar='source.etf0',
                    default=SUPPRESS,
                    help='path to speaker identification scores')

sgroup.add_argument('--si-param', metavar='param.pkl',
                    type=si_param_parser, dest='sigraph', default=SUPPRESS,
                    help='path to trained parameters for speaker identification')

sgroup.add_argument('--si-nbest', metavar='N', type=int, default=SUPPRESS,
                    help='path to trained parameters for speaker identification')

# == Head ==
hgroup = argparser.add_argument_group('[head] modality')

# Face clustering
msg = "path to source for head clustering. " + clicommon.msgURI()
hgroup.add_argument('--hh', type=mm_parser, metavar='source.mdtm', 
                    default=SUPPRESS, help=msg)

hgroup.add_argument('--hh-param', type=hh_param_parser, metavar='param.pkl',
                    dest='hhgraph', default=SUPPRESS,
                    help='path to trained parameters for head clustering')

msg = "path to precomputed similarity matrices." + clicommon.msgURI()
hgroup.add_argument('--hh-precomputed', type=hh_precomputed_parser, 
                    metavar='matrix.pkl', help=msg)

# Head recognition
hgroup.add_argument('--hi', type=hi_parser, metavar='source.nbl',
                    default=SUPPRESS,
                    help='path to source for head recognition')

hgroup.add_argument('--hi-param', type=hi_param_parser, metavar='param.pkl',
                    default=SUPPRESS, help='path to trained parameters for head '
                                           'recognition')

# == Written ==
wgroup = argparser.add_argument_group('[written] modality')

# Written name detection
wgroup.add_argument('--wi', type=wi_parser, metavar='source.mdtm',
                    default=SUPPRESS, 
                    help='path to source for written name detection')

wgroup.add_argument('--wi-param', type=wi_param_parser, metavar='param.pkl', 
                    default=wi_param_parser(None), dest='wigraph', 
                    help='path to trained parameters for written name '
                         'detection')


# == Spoken ==
ngroup = argparser.add_argument_group('[spoken] modality')

# Spoken name detection
ngroup.add_argument('--ni', type=ni_parser, metavar='source.mdtm',
                    default=SUPPRESS,
                    help='path to source for spoken name detection')

ngroup.add_argument('--ni-param', type=ni_param_parser, metavar='param.pkl',
                    help='path to trained parameters for spoken name '
                         'detection')

# == Cross-modality ==
xgroup = argparser.add_argument_group('cross-modality')

xgroup.add_argument('--sh-param', metavar='param.pkl', type=x_param_parser,
                    dest='shgraph', default=SUPPRESS,
                    help='path to trained parameters for '
                         '[speaker/head] cross-modal clustering.')

xgroup.add_argument('--sw-param', metavar='param.pkl', type=x_param_parser,
                    dest='swgraph', default=SUPPRESS,
                    help='path to trained parameters for '
                         '[speaker/written] cross-modal clustering.')

xgroup.add_argument('--sn-param', metavar='param.pkl', type=x_param_parser,
                    dest='sngraph', default=SUPPRESS,
                    help='path to trained parameters for '
                         '[speaker/spoken] cross-modal clustering.')

xgroup.add_argument('--hw-param', metavar='param.pkl', type=x_param_parser,
                    dest='hwgraph', default=SUPPRESS,
                    help='path to trained parameters for '
                         '[head/written] cross-modal clustering.')

xgroup.add_argument('--hn-param', metavar='param.pkl', type=x_param_parser,
                    dest='hngraph', default=SUPPRESS,
                    help='path to trained parameters for '
                         '[head/spoken] cross-modal clustering.')

xgroup.add_argument('--wn-param', metavar='param.pkl', type=x_param_parser,
                    dest='wngraph', default=SUPPRESS,
                    help='path to trained parameters for '
                         '[written/spoken] cross-modal clustering.')

try:
    args = argparser.parse_args()
except IOError as e:
    sys.exit(e)

if hasattr(args, 'uris'):
    uris = args.uris

import time

for u, uri in enumerate(uris):
    
    if args.verbose:
        sys.stdout.write('[%d/%d] %s\n' % (u+1, len(uris), uri))
        sys.stdout.flush()
    
    # make sure output file will not be overwritten
    path = clicommon.replaceURI(args.output, uri)
    try:
       with open(path) as foutput:
           raise IOError('ERROR: output file %s already exists. Delete it first.\n' % path)
    except IOError as e:
       foutput = open(path, 'w')
    
    if hasattr(args, 'uem'):
        uem = args.uem(uri)
    else:
        uem = None
    
    # start with an empty graph
    G = nx.Graph()
    
    # SPEAKER DIARIZATION & IDENTIFICATION
    # ====================================
    
    # load speaker diarization input (ss)
    if hasattr(args, 'ss'):
        ss_src = args.ss(uri=uri, modality='speaker')
        if uem is not None:
            ss_src = ss_src.crop(uem, mode='intersection')
    else:
        ss_src = None
    
    # load speaker identification scores (si)
    if hasattr(args, 'si'):
        si_src = args.si(uri=uri, modality='speaker')
        if uem is not None:
            si_src = si_src.crop(uem, mode='intersection')
        if ss_src is None:
            ss_src = si_src.to_annotation(threshold=np.inf)
    else:
        si_src = None
    
    # speaker diarization
    if hasattr(args, 'ssgraph'):
        
        if args.verbose:
            sys.stdout.write('   - [speaker/speaker] similarity graph\n')
            sys.stdout.flush()
        
        # get PLP features
        plp = args.ss_plp(uri)
        
        # build speaker similarity graph
        g = args.ssgraph(ss_src, plp)
        
        # add it the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    # speaker identification
    if hasattr(args, 'sigraph'):
        
        if args.verbose:
            sys.stdout.write('   - [speaker] identity graph\n')
            sys.stdout.flush()
        
        # keep only n-best identities
        if hasattr(args, 'si_nbest'):
            si_src = si_src.nbest(args.si_nbest)
        
        # make sure the tracks are named the same way 
        # in speaker diarization and speaker identification
        if ss_src is not None:
            assert ss_src.timeline == si_src.timeline, \
                   "speaker diarization and identification timelines are not the same"
            for s in ss_src:
                assert ss_src.tracks(s) == si_src.tracks(s), \
                       "ss and si tracks are not the same " \
                       "%r: %r vs. %r" % (s, ss_src.tracks(s), si_src.tracks(s))
        
        # build speaker identity graph
        g = args.sigraph(si_src)
        
        # add it to the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    # HEAD CLUSTERING & RECOGNITION
    # =============================
    
    # load face clustering input (hh)
    if hasattr(args, 'hh'):
        hh_src = args.hh(uri=uri, modality='head')
        if uem is not None:
            hh_src = hh_src.crop(uem, mode='intersection')
    else:
        hh_src = None
    
    # load head identification scores (hi)
    if hasattr(args, 'hi'):
        hi_src = args.hi(uri=uri, modality='head')
        if uem is not None:
            hi_src = hi_src.crop(uem, mode='intersection')
    else:
        hi_src = None
    
    # face clustering
    if hasattr(args, 'hhgraph'):
        
        if args.verbose:
            sys.stdout.write('   - [head/head] similarity graph\n')
            sys.stdout.flush()
        
        # if --hh option is missing, try to use head tracks from --hi option
        if hh_src is None:
            if hi_src is None:
                raise ValueError('missing head tracks')
            else:
                hh_src = hi_src.to_annotation(threshold=np.inf)
        
        # get precomputed matrix
        precomputed = args.hh_precomputed(uri)
        
        # build head similarity graph
        g = args.hhgraph(hh_src, precomputed)
        
        # add it the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    # face recognition
    if hasattr(args, 'higraph'):
        
        if args.verbose:
            sys.stdout.write('   - [head] identity graph\n')
            sys.stdout.flush()
        
        # keep only n-best identities
        if hasattr(args, 'hi_nbest'):
            hi_src = hi_src.nbest(args.hi_nbest)
        
        # make sure the tracks are named the same way 
        # in head clustering and head recognition
        if hh_src is not None:
            assert hh_src.timeline == hi_src.timeline and \
                   all([hh_src.tracks(s) == hi_src.track(s) for s in hh_src]), \
                   "head clustering and recognition tracks are not the same"
        
        # build head identity graph
        g = args.higraph(hi_src)
        
        # add it to the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    # WRITTEN NAMES
    # =============
    
    if hasattr(args, 'wi'):
        wi_src = args.wi(uri=uri, modality='written')
        if uem is not None:
            wi_src = wi_src.crop(uem, mode='intersection')
    else:
        wi_src = None
    
    # written name detection
    if hasattr(args, 'wi'):
        
        if args.verbose:
            sys.stdout.write('   - [written] identity graph\n')
            sys.stdout.flush()
        
        # build written identity graph
        g = args.wigraph(wi_src)
        
        # add it to the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    # SPOKEN NAMES
    # ============
    
    # spoken name detection
    if hasattr(args, 'ni'):
        pass
    
    # speaker/head
    if hasattr(args, 'shgraph'):
        
        if args.verbose:
            sys.stdout.write('   - [speaker/head] crossmodal graph\n')
            sys.stdout.flush()
        
        # build speaker/head graph
        g = args.shgraph(ss_src, hh_src)
        # add it to the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    # speaker/written
    if hasattr(args, 'swgraph'):
        
        if args.verbose:
            sys.stdout.write('   - [speaker/written] crossmodal graph\n')
            sys.stdout.flush()
        
        # build speaker/written graph
        g = args.swgraph(ss_src, wi_src)
        # add it to the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    # speaker/spoken
    if hasattr(args, 'sngraph'):
        
        if args.verbose:
            sys.stdout.write('   - [speaker/spoken] crossmodal graph\n')
            sys.stdout.flush()
        
        # build speaker/spoken graph
        g = args.sngraph(ss_src, ni_src)
        # add it to the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    # head/written
    if hasattr(args, 'hwgraph'):
        
        if args.verbose:
            sys.stdout.write('   - [head/written] crossmodal graph\n')
            sys.stdout.flush()
        
        # build head/written graph
        g = args.hwgraph(hh_src, wi_src)
        # add it to the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    # head/spoken
    if hasattr(args, 'hngraph'):
        
        if args.verbose:
            sys.stdout.write('   - [head/spoken] crossmodal graph\n')
            sys.stdout.flush()
        
        # build head/spoken graph
        g = args.sngraph(hh_src, ni_src)
        # add it to the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    # written/spoken
    if hasattr(args, 'wngraph'):
        
        if args.verbose:
            sys.stdout.write('   - [written/spoken] crossmodal graph\n')
            sys.stdout.flush()
        
        # build written/spoken graph
        g = args.wngraph(wi_src, ni_src)
        # add it to the multimodal graph
        G.add_nodes_from(g.nodes_iter(data=True))
        G.add_edges_from(g.edges_iter(data=True))
    
    
    G = add_unique_identity_constraint(G)
    G = add_twin_tracks_constraint(G)
    G = add_cooccurring_labels_contraint(G)
    
    
    # dump graph
    nx.write_gpickle(G, foutput)
    foutput.close()


