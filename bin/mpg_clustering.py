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
import networkx as nx

from argparse import ArgumentParser, SUPPRESS
from pyannote import clicommon
from pyannote.parser import AnnotationParser
from pyannote.algorithm.mpg.gurobi import GurobiModel

argparser = ArgumentParser(parents=[clicommon.parser],
                           description='Probability Graph Clustering')

# MANDATORY ARGUMENT (INPUT): PATH TO PROBABILITY GRAPH
# Probability graph is loaded on request
def input_parser(path):
    def load_mpg(uri):
        return nx.read_gpickle(clicommon.replaceURI(path, uri))
    return load_mpg
msg = 'path to input probability graph. ' + clicommon.msgURI()
argparser.add_argument('input', type=input_parser, metavar='mpg.pkl', help=msg)

# MANDATORY ARGUMENT (OUTPUT): PATH TO FINAL ANNOTATION
# Returns a writer and file handle (make sure it doesn't exist)
def output_parser(path):
    try:
       with open(path) as f: pass
    except IOError as e:
        writer, extension = AnnotationParser.guess(path)
        return writer(), open(path, 'w')
    raise IOError('ERROR: output file %s already exists. Delete it first.\n' % path)
argparser.add_argument('output', type=output_parser, metavar='output.mdtm',
                       help='path to where to store the output')

# OPTIONAL ARGUMENTS: WHICH EDGES TO REMOVE
ggroup = argparser.add_argument_group('Probability graph')
ggroup.add_argument('--no-ss', action='store_true', dest='ss',
                       help='remove speaker diarization edges')
ggroup.add_argument('--no-hh', action='store_true', dest='hh',
                       help='remove face clustering edges')
ggroup.add_argument('--no-si', action='store_true', dest='si',
                       help='remove speaker recognition edges')
ggroup.add_argument('--no-hi', action='store_true', dest='hi',
                       help='remove face recognition edges')
ggroup.add_argument('--no-sh', action='store_true', dest='sh',
                       help='remove speaker/face edges')
ggroup.add_argument('--no-sw', action='store_true', dest='sw',
                       help='remove speaker/written edges')
ggroup.add_argument('--no-hw', action='store_true', dest='hw',
                       help='remove face/written edges')

# OPTIONAL ARGUMENTS: OPTIMIZATION
ogroup = argparser.add_argument_group('Optimization')
def method_parser(name):
    methods = {'primal':0, 'dual':1, 'barrier':2, 'concurrent':3, 'deterministic':4}
    return methods[name]

ogroup.add_argument('--method', default='concurrent', type=str,
                    choices = ('primal', 'dual', 'barrier', 'concurrent', 'deterministic'),
                    help="set algorithm used to solve the root node of the MIP "
                         "model: primal simplex, dual simplex, barrier, "
                         "concurrent (default) or deterministic concurrent.")
ogroup.add_argument('--mip-gap', type=float, metavar='MIPGAP', default=1e-4,
                    help='The MIP solver will terminate when the relative gap '
                         'between the lower and upper objective bound is less '
                         'than MIPGAP times the upper bound.')
ogroup.add_argument('--time-limit', type=int, metavar='N', default=SUPPRESS,
                       help='stop optimization after N minutes')
ogroup.add_argument('--threads', type=int, metavar='N', default=SUPPRESS, 
                    help='number of threads to use.')
# ogroup.add_argument('--prune-mm', type=float, metavar='P', default=0.0,
#                     help='set probability of mono-modal edges to zero '
#                          'in case it is already lower than P.')
# ogroup.add_argument('--maxnodes', type=int, metavar='N', default=SUPPRESS,
#                     help='do not try to perform optimization if number of '
#                          'is higher than N.')

fgroup = argparser.add_argument_group('Objective function')
fgroup.add_argument('--objective', type=int, metavar='N', default=1,
                    help='select objective function:'
                         '1 = Maximize ∑ α.xij.pij + (1-α).(1-xij).(1-pij)'
                         '2 = Maximize ∑ α.wij.xij.pij + (1-α).wij.(1-xij).(1-pij)'
                         '3 = Maximize modularity'
                         '4 = Maximize ∑ α.xij.log(pij) + (1-α).(1-xij).log(1-pij)')
fgroup.add_argument('--alpha', type=float, metavar='ALPHA', default=0.5,
                    help='set α value to ALPHA in objective function.')

try:
    args = argparser.parse_args()
except IOError as e:
    sys.exit(e)


if not hasattr(args, 'uris'):
    raise IOError('missing list of resources (--uris)')

mipGap = args.mip_gap
method = method_parser(args.method)
threads = args.threads if hasattr(args, 'threads') else None
timeLimit = args.time_limit*60 if hasattr(args, 'time_limit') else None
quiet = len(args.verbose) < 2

writer, f = args.output

for u, uri in enumerate(args.uris):
    
    if args.verbose:
        sys.stdout.write('[%d/%d] %s\n' % (u+1, len(args.uris), uri))
        sys.stdout.flush()
    
    # load probability graph
    pg = args.input(uri)
    
    # selectively remove some edges (as requested by the user)
    if args.ss:
        pg.remove_diarization_edges('speaker')
    if args.hh:
        pg.remove_diarization_edges('head')
    if args.si:
        pg.remove_recognition_edges('speaker')
    if args.hi:
        pg.remove_recognition_edges('head')
    if args.sh:
        pg.remove_crossmodal_edges('speaker', 'head')
    if args.sw:
        pg.remove_crossmodal_edges('speaker', 'written')
    if args.hw:
        pg.remove_crossmodal_edges('head', 'written')
    
    # create ILP problem
    model = GurobiModel(pg, method=method,
                            mipGap=mipGap,
                            threads=threads,
                            timeLimit=timeLimit,
                            quiet=quiet)
    
    # actual optimization
    if args.objective == 1:
        annotations = model.probMaximizeIntraMinimizeInter(alpha=args.alpha)
    elif args.objective == 2:
        annotations = model.weightedProbMaximizeIntraMinimizeInter(alpha=args.alpha)
    elif args.objective == 3:
        annotations = model.maximizeModularity()
    elif args.objective == 4:
        annotations = model.logProbMaximizeIntraMinimizeInter(alpha=args.alpha)
    
    # save to file
    for uri, modality in annotations:
        writer.write(annotations[uri, modality], f=f)

f.close()
