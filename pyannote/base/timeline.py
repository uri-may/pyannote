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

# TODO: Faster implementation of .__contains__() (for use in .__iadd__()) 
#       Possibly with an additional interal set of segments?
#       or with interpolated binary search.

from segment import Segment, RevSegment, SEGMENT_PRECISION
  
class Timeline(object):
    """
    Ordered set of segments.
    
    A timeline can be seen as an ordered set of non-empty segments (Segment).
    Segments can overlap -- though adding an already exisiting segment to a 
    timeline does nothing.
    
    Parameters
    ----------
    segments : Segment iterator, optional
        initial set of segments
    video : string, optional
        name of (audio or video) segmented document
    
    Returns
    -------
    timeline : Timeline
        New timeline 
    
    Examples
    --------
    Create a new empty timeline
        
        >>> timeline = Timeline()
        >>> if not timeline:
        ...    print "Timeline is empty."
        Timeline is empty.
    
    Add one segment (+=)
    
        >>> segment = Segment(0, 1)
        >>> timeline += segment
        >>> if len(timeline) == 1:
        ...    print "Timeline contains only one segment."
        Timeline contains only one segment.
    
    Add all segments from another timeline
    
        >>> other_timeline = Timeline([Segment(0.5, 3), Segment(6, 8)])
        >>> timeline += other_timeline
        
    Get timeline extent, coverage & duration
        
        >>> extent = timeline.extent()
        >>> print extent
        [0 --> 8]
        >>> coverage = timeline.coverage()
        >>> print coverage
        [
           [0 --> 3]
           [6 --> 8]
        ]
        >>> duration = timeline.duration()
        >>> print "Timeline covers a total of %g seconds." % duration
        Timeline covers a total of 5 seconds.
    
    Iterate over (sorted) timeline segments
        
        >>> for segment in timeline:
        ...    print segment
        [0 --> 1]
        [0.5 --> 3]
        [6 --> 8]
    
    Segmentation
    
        >>> segmentation = timeline.segmentation()
        >>> print segmentation
        [
           [0 --> 0.5]
           [0.5 --> 1]
           [1 --> 3]
           [6 --> 8]
        ]
        >>> if timeline.is_segmentation():
        ...    print "Timeline is a segmentation."
        >>> if segmentation.is_segmentation():
        ...    print "Timeline is a segmentation."
        Timeline is a segmentation.
        
    Gaps
    
        >>> timeline = timeline.copy()
        >>> print timeline
        [
           [0 --> 1]
           [0.5 --> 3]
           [6 --> 8]
        ]
        >>> print timeline.gaps()
        [
           [3 --> 6]
        ]
        >>> segment = Segment(0, 10)
        >>> print timeline.gaps(segment)
        [
           [3 --> 6]
           [8 --> 10]
        ]
        
    """
    
    def __init__(self, segments=None, video=None):
        
        super(Timeline, self).__init__()
        
        # path to (or any identifier of) segmented video
        self.__video = video
        
        # this list is meant to store segments (as Segment object).
        # it is always sorted (using Segment comparison operators,
        # i.e. more or less sorted by segment start time).
        self.__segments = [] 
        
        # this list is meant to store reversed segments (as RevSegment object)
        # it is always sorted (using RevSegment comparison operators,
        # i.e. more or less sorted by segment end time).
        self.__rsegments = []
        
        if segments is not None:
            try:
                # Add every segment, one after the other
                for segment in segments:
                    self += segment
            except Exception, e:
                raise ValueError('Timeline must be initialized using a'
                                 'Segment iterator.')
    
    def __get_video(self): 
        return self.__video
    def __set_video(self, value):
        self.__video = value
    video = property(fget=__get_video, fset=__set_video)
    """Path to (or any identifier of) segmented video
    
    Examples
    --------
    
    >>> timeline = Timeline(video="MyVideo.avi")
    >>> timeline.video = "MyOtherVideo.avi"
    >>> print timeline.video
    MyOtherVideo.avi
    
    """
    
    # Recursive binary search helper function
    def __search_helper(self, element, sorted_list, left, right):
        
        # Stop recursive search when position is found.
        if (left+1) >= right:
            return right
            
        # Binary search pivot
        mid = (left+right)/2
        
        if element < sorted_list[mid]:
            # Search in left part
            return self.__search_helper(element, sorted_list, left, mid)
        else:
            # Search in right part
            return self.__search_helper(element, sorted_list, mid, right)
    
    def __search(self, element, sorted_list):
        """Search insertion position in sorted list.
        
        Parameters
        ----------        
        element : any object with comparison operators
            Element meant to be inserted into `sorted_list`
        sorted_list : list of objects of same type as `element`
            Sorted list into which `element` is to be inserted.
        
        Returns
        -------        
        index : int
            Index of position where to insert `element` into `sorted_list`
            so that the resulting list is still sorted.
                
        """
        # If list is empty, add unique element to the list
        if len(sorted_list) == 0:
            return 0
        
        # If element is smaller than the smallest element of the list,
        # add it at the beginning of the list
        if element < sorted_list[0]:
            return 0
            
        # If element is greater than the greatest element of the list,
        # add it at the end of the list
        if element > sorted_list[-1]:
            return len(sorted_list)
    
        # Otherwise, binary search for the correct position
        return self.__search_helper(element, sorted_list, 0, len(self))    
    
    def __iadd__(self, other):
        """Use expression 'timeline += other'
        
        Add new segment(s) to the timeline.
        
        Parameters
        ----------
        other : Segment or Segment iterator
            Can be a Timeline since it is a Segment iterator.

        Returns
        -------
        timeline : Timeline (self)
            Original timeline with added segments.
        
        """
        
        # timeline += segment
        if isinstance(other, Segment):
            
            # do nothing if segment is empty of already exists
            if (not other) or (other in self.__segments):
                return self
            
            # position in Segment list
            index = self.__search(other, self.__segments)
                
            # position in RevSegment list
            rehto = RevSegment(other)
            xedni = self.__search(rehto, self.__rsegments)
                
            # add segment in both lists
            self.__segments.insert(index, other)
            self.__rsegments.insert(xedni, rehto)
            
            return self
            
        # timeline += other_timeline
        if isinstance(other, Timeline):
            # check for video conflict
            if self.video != other.video:
                raise ValueError("video conflict:"
                                 "'%s' and '%s" % (self.video, other.video))
        
        # call timeline += segment for each segment in iterator/timeline
        # will raise a TypeError in case one segment cannot be added
        try:
            for segment in other:
                self += segment
            return self
        except Exception, e:
            raise TypeError("unsupported operand type(s) for +=:"
                            "must be Segment or Segment iterator.")
    
    def __add__(self, other):
        """Use expression 'timeline + other'
        
        See Also
        --------
        __iadd__
        
        """
        timeline = self.copy()
        timeline += other
        return timeline
    
    def __len__(self):
        """Use expression 'len(timeline)'

        Returns
        -------
        number : int
            Number of segments in timeline
        
        """
        return len(self.__segments)
        
    def __nonzero__(self):
        """Use expression 'if timeline'
        
        Returns
        -------
        valid : bool
            False if timeline is empty (contains no segment),
            True otherwise
        
        """
        return len(self) > 0
    
    def __iter__(self):
        """Sorted segment iterator"""
        return iter(self.__segments)
    
    def __reversed__(self):
        """Reverse-sorted segment iterator"""
        return reversed(self.__segments)
    
    def __getitem__(self, key):
        """Use the expressions 'timeline[i]' or 'timeline[i:j]'
        
        Parameters
        ----------
        key : int or slice
        
        Returns
        -------
        segment : Segment
            key.th segment if key is int.
        segments : list
            list of segments if key is a slice.
        
        Raises
        ------
        IndexError when requested segment is out of range.
        
        Examples
        --------
        
            >>> timeline = Timeline()
            >>> timeline += [Segment(0, 1), Segment(1, 2), Segment(1, 8)]
            >>> timeline += [Segment(2,3), Segment(2, 4), Segment(6, 7)]
            
            >>> segment = timeline[3]
            >>> print segment
            [2 --> 3]
            >>> segments = timeline[2:5]
            >>> print segments
            [<Segment(1, 8)>, <Segment(2, 3)>, <Segment(2, 4)>]
            >>> segments = timeline[:3]
            >>> print segments
            [<Segment(0, 1)>, <Segment(1, 2)>, <Segment(1, 8)>]
            >>> segment = timeline[12]
            Traceback (most recent call last):
            ...
            IndexError: list index out of range
            
        """        
        return self.__segments[key]
    
    def index(self, segment):
        """Find position of segment
        
        Parameters
        ----------
        segment : Segment
            Segment to look for (must exist in timeline).
        
        Returns
        -------
        index : int
            Position of segment in timeline, such as timeline[index] == segment 
        
        Raises
        ------
        TypeError if segment is not a Segment
        ValueError if segment does not exist in timeline
        
        Examples
        --------
        
            >>> timeline = Timeline()
            >>> timeline += [Segment(0, 1), Segment(1, 2), Segment(1, 8)]
            >>> timeline += [Segment(2,3), Segment(2, 4), Segment(6, 7)]
            
            >>> segment = Segment(2, 4)
            >>> position = timeline.index(segment)
            >>> print "Segment %s is at position #%d." % (segment, position)
            Segment [2 --> 4] is at position #4.
            >>> segment = Segment(4, 12)
            >>> position = timeline.index(segment)
            Traceback (most recent call last):
            ...
            ValueError: timeline does not contain segment [4 --> 12].
        
        """
        
        if not isinstance(segment, Segment):
            raise TypeError("unsupported type: '%s'. " 
                            "Must be Segment." % type(segment).__name__)
        
        index = self.__search(segment, self.__segments)-1
        if self[index] == segment:
            return index
        else:
            raise ValueError("timeline does not contain segment %s." % segment)
    
    # ------------------------------------------------------------------- #
    
    def __intersecting(self, segment):
        """Sorted list of intersecting segments"""
        
        # if segment is empty, it intersects nothing.
        if not segment:
            return []
        
        # any intersecting segment starts before segment ends 
        # and ends after it starts
        
        dummy_end = Segment(segment.end-SEGMENT_PRECISION, \
                            segment.end-SEGMENT_PRECISION)
        index = self.__search(dummy_end, self.__segments)
        # property 1:
        # every segment in __segments[:index] starts before key ends
        
        dummy_start = RevSegment(Segment(segment.start+SEGMENT_PRECISION, \
                                         segment.start+SEGMENT_PRECISION))
        xedni = self.__search(dummy_start, self.__rsegments)
        # property 2:
        # every segment in __rsegments[xedni:] ends after key starts
        
        # get segments with both properties
        both = set(self.__segments[:index]) & set(self.__rsegments[xedni:])
        
        # make sure every RevSegment is converted to Segment
        # and return their sorted list
        return sorted([rsegment.copy() for rsegment in both])
    
    def __call__(self, subset, mode='intersection'):
        """Sub-timeline
        
        Use expression 'timeline(subset, mode='intersection')
        
        Parameters
        ----------
        subset : Segment or Timeline
        
        mode : {'strict', 'loose', 'intersection'}
            Default `mode` is 'intersection'.
        
        Returns
        -------
        timeline : Timeline
            In 'strict' mode, `timeline` only contains segments that are fully 
            included in provided segment or timeline coverage.
            In 'loose' mode, `timeine` contains every segment intersecting 
            provided segment or timeline.
            'intersection' mode is similar to 'loose' mode except sub-timeline
            segments are trimmed to be fully included in provided segment or 
            timeline.
             
        
        Examples
        --------
        
            >>> timeline = Timeline()
            >>> timeline += [Segment(0, 1), Segment(1, 2), Segment(1, 8)]
            >>> timeline += [Segment(2,3), Segment(2, 4), Segment(6, 7)]
            >>> print timeline(Segment(1.5, 6.5), mode='loose')
            [
               [1 --> 2]
               [1 --> 8]
               [2 --> 3]
               [2 --> 4]
               [6 --> 7]
            ]
            >>> print timeline(Segment(1.5, 3), mode='intersection')
            [
               [1.5 --> 2]
               [1.5 --> 3]
               [2 --> 3]
            ]
            >>> print timeline(Segment(1.5, 4), mode='strict')
            [
               [2 --> 3]
               [2 --> 4]
            ]
        
        """
        
        if not isinstance(subset, (Segment, Timeline)):
            raise TypeError("unsupported argument type: '%s'. Must be "
                            "Segment or Timeline." % type(subset).__name__)
        
        if isinstance(subset, Segment):
            segment = subset     
            isegments = self.__intersecting(segment)
            if mode == 'strict':
                isegments = [isegment for isegment in isegments \
                                      if isegment in segment]
            elif mode == 'intersection':
                isegments = [isegment & segment for isegment in isegments]
            elif mode == 'loose':
                pass
            else:
                raise ValueError('Unsupported mode (%s).' % mode)
            timeline = Timeline(segments=isegments, video=self.video)
        
        
        elif isinstance(subset, Timeline):
            timeline = Timeline(video=self.video)
            for segment in subset.coverage():
                timeline += self.__call__(segment, mode=mode)
        
        return timeline
    
    def __setitem__(self, key, value):
        raise NotImplementedError("use '+=' operator to add and 'del' operator"
                                  "to remove segment(s).")
    
    def __delitem__(self, key):
        """Use expression 'del timeline[i]' or 'del timeline[segment]' 
        
        Remove segment(s) from timeline (corresponding to provided index)
        
        Parameters
        ----------
        key : int, slice or Segment
            Index of segments or Segment to remove.
            
        Raises
        ------
        TypeError if key is neither int, slice or Segment
        ValueError if segment does not exist in timeline
        
        Examples
        --------
        
            >>> timeline = Timeline()
            >>> timeline += [Segment(0, 1), Segment(1, 2), Segment(2,3)]
            >>> timeline += [Segment(2, 4), Segment(1, 8), Segment(6, 7)]

            Try to remove unexisting segment

            >>> del timeline[Segment(3, 4)]
            Traceback (most recent call last):
            ...
            ValueError: timeline does not contain segment [3 --> 4].
            
            Remove segment
            
            >>> del timeline[Segment(1, 2)]
            >>> print timeline
            [
               [0 --> 1]
               [1 --> 8]
               [2 --> 3]
               [2 --> 4]
               [6 --> 7]
            ]
            
            Remove fourth segment
            
            >>> del timeline[3]
            >>> print timeline
            [
               [0 --> 1]
               [1 --> 8]
               [2 --> 3]
               [6 --> 7]
            ]
            
            Remove second and third segments
            
            >>> del timeline[1:3]
            >>> print timeline
            [
               [0 --> 1]
               [6 --> 7]
            ]
        
        """
        
        if not isinstance(key, (int, slice, Segment)):
            raise KeyError("unsupported type for key: '%s'. Must be int, "
                           "slice or Segment." % type(key).__name__)
        
        # del timeline[i]
        # remove i.th segment
        if isinstance(key, int):
            # find segment in reverse sorted list
            segment = self.__segments[key]
            yek = self.__search(RevSegment(segment), self.__rsegments)-1
            # delete segment in both lists
            del self.__segments[key]
            del self.__rsegments[yek]
            
        # del timeline[i:j]
        # remove i.th to (j-1).th segments
        elif isinstance(key, slice):
            segments = self.__segments[key]
            for segment in segments:
                # find segment in sorted list
                index = self.__search(segment, self.__segments)-1
                # find segment in reverse sorted list
                xedni = self.__search(RevSegment(segment), self.__rsegments)-1
                # delete segment in both lists
                del self.__segments[index]
                del self.__rsegments[xedni]
                
        # del timeline[segment]
        # remove segment (if it exists)                
        elif isinstance(key, Segment):
            # find position of segment
            i = self.index(key)
            # remove segment
            self.__delitem__(i)
        
    def clear(self):
        """Faster 'del timeline[:]'"""
        del self.__segments[:]
        del self.__rsegments[:]
    
    def __eq__(self, other):
        """Use expression 'timeline1 == timeline2'
        """
        if isinstance(other, Timeline):
            return (len(self) == len(other)) and \
                    all([segment == other[s] for s, segment in enumerate(self)])
        else:
            return False

    def __ne__(self, other):
        """Use expression 'timeline1 != timeline2'
        """
        if isinstance(other, Timeline):
            return (len(self) != len(other)) or \
                    any([segment != other[s] for s, segment in enumerate(self)])
        else:
            return True

    def __str__(self):
        """Human-friendly representation"""
        
        string = "[\n"
        for segment in self:
            string += "   %s\n" % segment
        string += "]"
        return string
    
    def __repr__(self):
        return "<Timeline(%s)>" % self.__segments
    
    
    # =================================================================== #          
    def __contains__(self, included):
        """Inclusion
        
        Use expression 'segment in timeline' or 'other_timeline in timeline'
        
        Parameters
        ----------
        included : Segment or Timeline
        
        Returns
        -------
        contains : bool
            True if every segment in `included` exists in timeline,
            False otherwise
        
        """
        
        if not isinstance(included, (Segment, Timeline)):
            raise TypeError("unsupported type '%s'. Must be"
                            "Segment or Timeline." % type(included).__name__)
        
        # True if `included` segment exists in timeline,
        # False otherwise
        if isinstance(included, Segment):
            try:
                i = self.index(included)
                return True
            except Exception, e:
                return False
        
        # True if every segment of included timeline 
        # exists in timeline, False otherwise
        elif isinstance(included, Timeline):
            return all([segment in self for segment in included])

    def covers(self, covered, mode='strict'):
        """Coverage check
        
        Check whether timeline covers other segment or timeline.
        
        In 'strict' mode, a segment is covered if at least one segment of 
        the timeline contains it.
        
        In 'loose' mode, a segment is covered if their exists a set of segments
        whose coverage fully contains it.
        
        Parameters
        ----------
        covered : Segment or Timeline
        mode : {'strict', 'loose'}, optional
            Default is 'strict'
        
        Returns
        -------
        covers : bool
            True if timeline covers `covered`, False otherwise
        
        """
        
        if not isinstance(covered, (Segment, Timeline)):
            raise TypeError("unsupported type '%s'. Must be"
                            "Segment or Timeline." % type(covered).__name__)
        
        if mode not in ['loose', 'strict']:
            raise NotImplementedError("unsupported mode '%s'." % mode)
            
        if mode == 'strict':
            
            # True if other segment is contained 
            # by at least one segment of the timeline
            if isinstance(covered, Segment):
                return any([covered in segment \
                            for segment in self(covered, mode='loose')])
            
            # True if timeline covers all other timeline segment
            elif isinstance(covered, Timeline):
                return all([self.covers(segment, mode='strict') \
                            for segment in covered])

        # 'loose' mode is equivalent to 'strict' mode applied on coverage
        elif mode == 'loose':
            coverage = self.coverage()
            return coverage.covers(covered, mode='strict')
        
    
    def __and__(self, other):
        """Intersection of two timelines (or a timeline and a segment)
        
        Use expression 'timeline & segment' or 'timeline & other_timeline
        
        Parameters
        ----------
        other : Segment or Timeline
        
        Returns
        -------
        intersection : Timeline
            Coverage of the timeline made of the intersection of the original
            timeline and the provided segment (or timeline segments).
        
        """
        return self(other, mode='intersection').coverage()
    
    def __or__(self, other):
        """Union of two timelines (or a timeline and a segment)
        
        Use expression 'timeline | segment' or 'timeline | other_timeline
        
        Parameters
        ----------
        other : Segment or Timeline
        
        Returns
        -------
        union : Timeline
            Coverage of the timeline made of segments from both the original
            timeline and the provided timeline (or segment)
        
        """
        return (self + other).coverage()
    
    def empty(self):
        """Empty copy of a timeline.
        
        Examples
        --------
        
            >>> timeline = Timeline(video="MyVideo.avi")
            >>> timeline += [Segment(0, 1), Segment(2, 3)]
            >>> empty = timeline.empty()
            >>> print empty.video
            MyVideo.avi
            >>> print empty
            [
            ]
        
        """
        return Timeline(video=self.video)
    
    def copy(self, segment_func=None):
        """Duplicate timeline.
        
        If segment_func is provided, apply it to each segment first.
        
        Parameters
        ----------
        segment_func : function
        
        Returns
        -------
        timeline : Timeline
            A (possibly modified) copy of the timeline

        Examples
        --------
        
            >>> timeline = Timeline(video="MyVideo.avi")
            >>> timeline += [Segment(0, 1), Segment(2, 3)]
            >>> cp = timeline.copy()
            >>> print cp.video
            MyVideo.avi
            >>> print cp
            [
               [0 --> 1]
               [2 --> 3]
            ]
        
        """
        timeline = self.empty()
        
        # If segment_func is not provided
        # make it a pass-through function
        if segment_func is None:
            segment_func = lambda segment: segment

        for segment in self:
            timeline += segment_func(segment)
        
        return timeline
    
    def extent(self):
        """Timeline extent
        
        The extent of a timeline is the segment of minimum duration that
        contains every segments of the timeline. It is unique, by definition.
        The extent of an empty timeline is an empty segment.
        
        Returns
        -------
        extent : Segment
            Timeline extent
            
        Examples
        --------
            
            >>> timeline = Timeline(video="MyVideo.avi")
            >>> timeline += [Segment(0, 1), Segment(9, 10)]
            >>> print timeline.extent()
            [0 --> 10]
        
        """
        if self:
            # The extent of a timeline ranges from the start time
            # of the earliest segment to the end time of the latest one.
            start_time = self.__segments[0].start
            end_time = self.__rsegments[-1].end
            return Segment(start=start_time, end=end_time)
        else:
            # The extent of an empty timeline is an empty segment 
            return Segment()        
    
    def coverage(self):
        """Timeline coverage
        
        The coverage of timeline is the timeline with the minimum number of
        segments with exactly the same time span as the original timeline.
        It is (by definition) unique and does not contain any overlapping 
        segments.

        Returns
        -------
        coverage : Timeline
            Timeline coverage
        
        """

        # The coverage of an empty timeline is an empty timeline.
        if not self:
            return self.copy()
        
        # Make sure video attribute is kept.
        coverage = Timeline(video=self.video)
        
        # Principle: 
        #   * gather all segments with no gap between them
        #   * add one segment per resulting group (their union |)
        # Note:
        #   Since segments are kept sorted internally, 
        #   there is no need to perform an exhaustive segment clustering.
        #   We just have to consider them in their natural order.
        
        # Initialize new coverage segment
        # as very first segment of the timeline
        new_segment = self[0]
        
        for segment in self[1:]:
            
            # If there is no gap between new coverage segment and next segment,
            if not (segment ^ new_segment):
                # Extend new coverage segment using next segment
                new_segment |= segment
            
            # If there actually is a gap,
            else:
                # Add new segment to the timeline coverage
                coverage += new_segment
                # Initialize new coerage segment as next segment
                # (right after the gap)
                new_segment = segment
        
        # Add new segment to the timeline coverage
        coverage += new_segment
        
        return coverage
    
    def duration(self):
        """Timeline duration
        
        Returns
        -------
        duration : float
            Duration of timeline coverage, in seconds.
        
        """
        
        # The timeline duration is the sum of the durations
        # of the segments in the timeline coverage. 
        return sum([segment.duration for segment in self.coverage()])
    
    def gaps(self, focus=None):
        """Timeline gaps
        
        Parameters
        ----------
        focus : None, Segment or Timeline
        
        Returns
        -------
        gaps : Timeline
            Timeline made of all gaps from original timeline, and delimited
            by provided segment or timeline.
        
        Raises
        ------
        TypeError when `focus` is neither None, Segment nor Timeline
        
        Examples
        --------
        
        """
        if focus is None:
            focus = self.extent()
        
        if not isinstance(focus, (Segment, Timeline)):
            raise TypeError("unsupported operand type(s) for -':"
                            "%s and Timeline." % type(focus).__name__)
        
        # segment focus
        if isinstance(focus, Segment):
            
            # starts with an empty timeline
            timeline = self.empty()
            
            # `end` is meant to store the end time of former segment
            # initialize it with beginning of provided segment `focus`
            end = focus.start
            
            # focus on the intersection of timeline and provided segment
            for segment in self(focus, mode='intersection').coverage():
                
                # add gap between each pair of consecutive segments
                # if there is no gap, segment is empty, therefore not added
                # see .__iadd__ for more information.
                timeline += Segment(start=end, end=segment.start)
                
                # keep track of the end of former segment
                end = segment.end
            
            # add final gap (if not empty)
            timeline += Segment(start=end, end=focus.end)

        # other_timeline - timeline
        elif isinstance(focus, Timeline):
            
            # starts with an empty timeline
            timeline = self.empty()
            
            # add gaps for every segment in coverage of provided timeline
            for segment in focus.coverage():
                timeline += self.gaps(focus=segment)
        
        return timeline
    
    def is_segmentation(self):
        """Check whether timeline contains overlapping segments
        
        Examples
        --------
            
            >>> timeline = Timeline()
            >>> timeline += [Segment(2, 3), Segment(2, 4)]
            >>> if timeline.is_segmentation():
            ...    print "Timeline has no overlapping segments."
            ... else:
            ...    print "Timeline has overlapping segments."
            Timeline has overlapping segments.
        
        """
        
        # Empty timelines have no overlapping segments
        if not self:
            return True
        
        end = self[0].end
        for s, segment in enumerate(self[1:]):
            # use Segment.__nonzero__ (for precision-related reasons...)
            if Segment(start=segment.start, end=end):
                return False
            end = segment.end
        return True
    
    def segmentation(self):
        """Non-overlapping timeline
        
        Create the unique timeline with same coverage and same set of segment 
        boundaries as original timeline, but with no overlapping segments.
        
        A picture is worth a thousand words:
        
            Original timeline:
            |------|    |------|     |----|
              |--|    |-----|     |----------|
        
            Non-overlapping timeline
            |-|--|-|  |-|---|--|  |--|----|--|
        
        Returns
        -------
        timeline : Timeline
        
        Examples
        --------
        
            >>> timeline = Timeline()
            >>> timeline += [Segment(0, 1), Segment(1, 2), Segment(2,3)]
            >>> timeline += [Segment(2, 4), Segment(6, 7)]
            >>> print timeline.segmentation()
            [
               [0 --> 1]
               [1 --> 2]
               [2 --> 3]
               [3 --> 4]
               [6 --> 7]
            ]
            
        """
        
        # return a copy if it has no overlapping segments
        if self.is_segmentation():
            return self.copy()

        # get all boundaries (sorted)
        # |------|    |------|     |----|
        #   |--|    |-----|     |----------|
        # becomes
        # | |  | |  | |   |  |  |  |    |  |
        boundaries = []
        for s, segment in enumerate(self):
            start = segment.start
            end   = segment.end
            if start not in boundaries:
                boundaries.append(start)
            if end   not in boundaries:
                boundaries.append(end) 
        boundaries = sorted(boundaries)

        # create new partition timeline
        # | |  | |  | |   |  |  |  |    |  |
        # becomes
        # |-|--|-|  |-|---|--|  |--|----|--|

        # start with an empty copy
        timeline = self.empty()
        
        start = boundaries[0]
        for boundary in boundaries[1:]:
            
            new_segment = Segment(start=start, end=boundary)
            
            # only add segments that are covered by original timeline
            if self.covers(new_segment, mode='strict'):
                timeline += Segment(start=start, end=boundary)
        
            start = boundary
        
        return timeline
    
    def is_partition(self):
        """Check for partition
        
        A partition is a segmentation, covering its extent exactly.
        
        Returns
        -------
        is_seg : bool
            True if timeline is a partition 
            False otherwise.
            
        
        Examples
        ---------
        
            >>> timeline = Timeline()
            >>> timeline += [Segment(0, 1), Segment(1, 2), Segment(3, 4)]
            >>> if timeline.is_partition():
            ...     print "Timeline is a partition."
            >>> timeline += Segment(2, 3)
            >>> if timeline.is_partition():
            ...     print "Timeline is a partition."
            Timeline is a partition.
            >>> timeline += Segment(3.5, 5)
            >>> if timeline.is_partition():
            ...     print "Timeline is a partition."
            
        """
        return self and \
               self.is_segmentation() and \
               Timeline([self.extent()], video=self.video) == self.coverage()
    
    

class Segmentation(Timeline):    
    def __iadd__(self, other):
        raise NotImplementedError('')
        
class Partition(Segmentation):
    def __iadd__(self, other):
        raise NotImplementedError('')
    def __delitem__(self, key):
        raise NotImplementedError('')
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()

    