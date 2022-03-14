""" arrayframe.py
Description:
"""
# Package Header #
from ..header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from collections.abc import Iterable, Iterator, Sized
from contextlib import contextmanager
from bisect import bisect_right
import math
from typing import Any, NamedTuple
from warnings import warn

# Third-Party Packages #
from baseobjects import singlekwargdispatchmethod
from baseobjects.cachingtools import timed_keyless_cache
import numpy as np

# Local Packages #
from .arrayframeinterface import ArrayFrameInterface
from ..datacontainer.datacontainer import ArrayContainer


# Definitions #
# Classes #
class FrameIndex(NamedTuple):
    index: int | None
    start_index: int | None
    inner_index: int | None


class RangeIndices(NamedTuple):
    start: FrameIndex | int | None
    stop: FrameIndex | int | None


class ArrayFrame(ArrayFrameInterface):
    """A frame for holding different data types which are similar to a numpy array.

    This object acts as an abstraction of several contained numpy like objects, to appear as combined numpy array.
    Accessing the data within can be used with standard numpy data indexing which is based on the overall data at the
    deepest layer of the structure.

    Attributes:
        is_updating:
        is_combine:
        returns_frame: Determines if methods will return frames or numpy arrays.
        mode: Determines if this frame is editable or read only.
        target_shape: The shape that frame should be and if resized the shape it will default to.
        axis: The axis of the data which this frame extends for the contained data frames.
        combine_type: The object type to return when combining frames.
        return_frame_type: The frame type to return when returning frames from this object.
        frames: The list of frames/objects in this frame.

    Args:
        frames:
        mode:
    """
    # TODO: Consider making the frame work multidimensional. (Only single-dimensional right now.)
    default_return_frame_type: ArrayFrameInterface = ArrayFrameInterface
    default_combine_type: ArrayFrameInterface | None = ArrayContainer

    # Magic Methods
    # Construction/Destruction
    def __init__(
        self,
        frames: Iterable | None = None,
        mode: str = 'a',
        update: bool = True,
        init: bool = True
    ) -> None:
        # Parent Attributes #
        super().__init__(init=False)

        # New Attributes #
        # Descriptors #
        # System
        self.is_combine: bool = False
        self.returns_frame: bool = False
        self.mode: str = 'a'

        # Shape
        self.target_shape: Iterable[int] | None = None
        self.axis: int = 0

        # Assign Classes #
        self.combine_type = self.default_combine_type
        self.return_frame_type = self.default_return_frame_type

        # Containers #
        self.frames: list = []

        # Object Construction #
        if init:
            self.construct(frames=frames, mode=mode, update=update)

    @property
    def shapes(self) -> tuple[tuple[int]]:
        """Returns the shapes of all contained frames and uses cached value if available."""
        try:
            return self.get_shapes.caching_call()
        except AttributeError:
            return self.get_shapes()

    @property
    def min_shape(self) -> tuple[tuple[int]]:
        """Get the minimum shapes from the contained frames/objects if they are different across axes."""
        try:
            return self.get_min_shape.caching_call()
        except AttributeError:
            return self.get_min_shape()
    
    @property
    def max_shape(self) -> tuple[tuple[int]]:
        """Get the maximum shapes from the contained frames/objects if they are different across axes."""
        try:
            return self.get_max_shape.caching_call()
        except AttributeError:
            return self.get_max_shape()
    
    @property
    def shape(self) -> tuple[int]:
        """Returns the shape of this frame if all contained shapes are the same and uses cached value if available."""
        try:
            return self.get_shape.caching_call()
        except AttributeError:
            return self.get_shape()

    @property
    def lengths(self) -> tuple[int]:
        """Returns the lengths of each contained frames as a tuple and uses cached value if available."""
        try:
            return self.get_lengths.caching_call()
        except AttributeError:
            return self.get_lengths()

    @property
    def length(self) -> int:
        """Returns the sum of all lengths of contained frames and uses cached value if available."""
        try:
            return self.get_length.caching_call()
        except AttributeError:
            return self.get_length()

    @property
    def frame_start_indices(self) -> tuple[int]:
        """Returns the start index of the contained frames and uses cached value if available."""
        try:
            return self.get_frame_start_indices.caching_call()
        except AttributeError:
            return self.get_frame_start_indices()

    @property
    def frame_end_indices(self) -> tuple[int]:
        """Returns the end index of the contained frames and uses cached value if available."""
        try:
            return self.get_frame_end_indices.caching_call()
        except AttributeError:
            return self.get_frame_end_indices()

    # Arithmetic
    def __add__(self, other: "ArrayFrame" | list):
        """When the add operator is called it concatenates this frame with other frames or a list."""
        return self.concatenate(other=other)

    # Instance Methods
    # Constructors/Destructors
    def construct(self, frames: Iterable = None, mode: str = None, update: bool = None) -> None:
        self.disable_updating()

        if frames is not None:
            self.frames.clear()
            self.frames.extend(frames)

        if mode is not None:
            self.mode = mode

        if update is not None:
            self.is_updating = update

    # Editable Copy Methods
    def default_editable_method(self) -> ArrayFrameInterface:
        return self.combine_frames()

    # Cache and Memory
    def refresh(self) -> None:
        """Resets this frame's caches and fills them with updated values."""
        self.get_shapes()
        self.get_shape()
        self.get_lengths()
        self.get_length()

    def clear_all_caches(self) -> None:
        """Clears this frame's caches and all the contained frame's caches."""
        self.clear_caches()
        for frame in self.frames:
            try:
                frame.clear_all_caches()
            except AttributeError:
                continue

    # Updating
    def enable_updating(self, get_caches: bool = False) -> None:
        """Enables updating for this frame and all contained frames/objects.

        Args:
            get_caches: Determines if get_caches will run before setting the caches.
        """
        self.timed_caching(get_caches=get_caches)
        for frame in self.frames:
            frame.enable_updating(get_caches=get_caches)

    def enable_last_updating(self, get_caches: bool = False) -> None:
        """Enables updating for this frame and the last contained frame/object.

        Args:
            get_caches: Determines if get_caches will run before setting the caches.
        """
        self.timed_caching(get_caches=get_caches)
        try:
            self.frames[-1].enable_updating(get_caches=get_caches)
        except IndexError as e:
            pass  # Maybe raise warning.

    def disable_updating(self, get_caches: bool = False) -> None:
        """Disables updating for this frame and all contained frames/objects.

        Args:
            get_caches: Determines if get_caches will run before setting the caches.
        """
        self.timeless_caching(get_caches=get_caches)
        for frame in self.frames:
            frame.disable_updating(get_caches=get_caches)

    # Getters
    @timed_keyless_cache(lifetime=1.0, call_method="clearing_call", collective=False)
    def get_shapes(self) -> tuple[tuple[int]]:
        """Get the shapes from the contained frames/objects.

        Returns:
            The shapes of the contained frames/objects.
        """
        self.get_lengths.clear_cache()
        return tuple(frame.shape for frame in self.frames)

    @timed_keyless_cache(lifetime=1.0, call_method="clearing_call", collective=False)
    def get_min_shape(self) -> tuple[tuple[int]]:
        """Get the minimum shapes from the contained frames/objects if they are different across axes.

        Returns:
            The minimum shapes of the contained frames/objects.
        """
        n_frames = len(self.frames)
        n_dims = [None] * n_frames
        shapes = [None] * n_frames
        for index, frame in enumerate(self.frames):
            shapes[index] = shape = frame.shape
            n_dims[index] = len(shape)

        max_dims = max(n_dims)
        shape_array = np.zeros((n_frames, max_dims), dtype='i')
        for index, s in enumerate(shapes):
            shape_array[index, :n_dims[index]] = s

        shape = [None] * max_dims
        for ax in range(max_dims):
            if ax == self.axis:
                shape[ax] = sum(shape_array[:, ax])
            else:
                shape[ax] = min(shape_array[:, ax])
        return tuple(shape)

    @timed_keyless_cache(lifetime=1.0, call_method="clearing_call", collective=False)
    def get_max_shape(self) -> tuple[tuple[int]]:
        """Get the maximum shapes from the contained frames/objects if they are different across axes.

        Returns:
            The maximum shapes of the contained frames/objects.
        """
        n_frames = len(self.frames)
        n_dims = [None] * n_frames
        shapes = [None] * n_frames
        for index, frame in enumerate(self.frames):
            shapes[index] = shape = frame.shape
            n_dims[index] = len(shape)

        max_dims = max(n_dims)
        shape_array = np.zeros((n_frames, max_dims), dtype='i')
        for index, s in enumerate(shapes):
            shape_array[index, :n_dims[index]] = s

        shape = [None] * max_dims
        for ax in range(max_dims):
            if ax == self.axis:
                shape[ax] = sum(shape_array[:, ax])
            else:
                shape[ax] = max(shape_array[:, ax])
        return tuple(shape)

    @timed_keyless_cache(lifetime=1.0, call_method="clearing_call", collective=False)
    def get_shape(self) -> tuple[tuple[int]]:
        """Get the shape of this frame from the contained frames/objects.

         If the contained frames/object are different across axes this will raise a warning and return the minimum
         shape.

        Returns:
            The shape of this frame or the minimum shapes of the contained frames/objects.
        """

        if not self.validate_shape():
            warn(f"The arrayframe '{self}' does not have a valid shape, returning minimum shape.")
        try:
            return self.get_min_shape.caching_call()
        except AttributeError:
            return self.get_min_shape()

    @timed_keyless_cache(lifetime=1.0, call_method="clearing_call", collective=False)
    def get_lengths(self) -> tuple[int]:
        """Get the lengths of the contained frames/objects.

        Returns:
            All the lengths of the contained frames/objects.
        """
        self.get_length.clear_cache()

        shapes = self.shapes
        lengths = [0] * len(shapes)
        for index, shape in enumerate(shapes):
            lengths[index] = shape[self.axis]

        return tuple(lengths)

    @timed_keyless_cache(lifetime=1.0, call_method="clearing_call", collective=False)
    def get_length(self) -> int:
        """Get the length of this frame as the sum of the contained frames/objects length.

        Returns:
            The length of this frame.
        """
        return int(sum(self.lengths))

    @timed_keyless_cache(lifetime=1.0, call_method="clearing_call", collective=False)
    def get_frame_start_indices(self) -> tuple[int]:
        """Get the start indices of the contained files based on the lengths of the contained frames/objects.

        Returns:
            The start indices of each of the contained frames/objects.
        """
        lengths = self.lengths
        starts = [None] * len(lengths)
        previous = 0
        for index, frame_length in enumerate(self.lengths):
            starts[index] = int(previous)
            previous += frame_length
        return tuple(starts)

    @timed_keyless_cache(lifetime=1.0, call_method="clearing_call", collective=False)
    def get_frame_end_indices(self) -> tuple[int]:
        """Get the end indices of the contained files based on the lengths of the contained frames/objects.

        Returns:
            The end indices of each of the contained frames/objects.
        """
        lengths = self.lengths
        ends = [None] * len(lengths)
        previous = -1
        for index, frame_length in enumerate(self.lengths):
            previous += frame_length
            ends[index] = int(previous)
        return tuple(ends)

    # Main Get Item
    @singlekwargdispatchmethod("item")
    def get_item(self, item: Any) -> Any:
        """Get an item from this frame based on the input. For Ellipsis return all the data.

        Args:
            item: An object to get an item from this frame.

        Returns:
            An object from this arrayframe
        """
        if item is Ellipsis:
            return self.get_all_data()
        else:
            raise TypeError(f"A {type(item)} cannot be used to get an item from {type(self)}.")

    @get_item.register
    def _(self, item: slice) -> Any:
        """Get an item from this frame based on a slice and return a range of contained data.

        Args:
            item: The slice to select the data range to return.

        Returns:
            The data of interest from within this frame.
        """
        return self.get_range_slice(item)

    @get_item.register
    def _(self, item: Iterable) -> Any:
        """Get an item from this frame based on an iterable and return a range of contained data.

        Args:
            item: The slice to select the data range to return.

        Returns:
            The data of interest from within this frame.
        """
        is_slices = True
        for element in item:
            if isinstance(element, int):
                is_slices = False
                break

        if is_slices:
            return self.get_slices(item)
        else:
            return self.get_from_index(item)

    @get_item.register
    def _(self, item: int) -> ArrayFrameInterface:
        """Get an item from this frame based on an int and return a frame.

        Args:
            item: The index of the frame to return.

        Returns:
            The frame interest from within this frame.
        """
        return self.get_frame(item)

    # Shape
    def validate_shape(self) -> bool:
        """Checks if this data frame has a valid/continuous shape.

        Returns:
            If this data frame has a valid/continuous shape.
        """
        shapes = list(self.shapes)
        if shapes:
            shape = list(shapes.pop())
            shape.pop(self.axis)
            for s in shapes:
                s = list(s)
                s.pop(self.axis)
                if s != shape:
                    return False
        return True

    def reshape(self, shape: Iterable[int] | None = None, **kwargs: Any) -> None:
        """Changes the shape of the data frame without changing its data.

        Args:
            shape: The target shape to change this frame to.
            kwargs: Any additional kwargs need to change the shape of contained frames/objects
        """
        if shape is None:
            shape = self.target_shape

        for frame in self.frames:
            if not frame.validate_shape() or frame.shape != shape:
                frame.change_size(shape, **kwargs)

    # Frames
    def frame_sort_key(self, frame: Any) -> Any:
        """The key to be used in sorting with the frame as the sort basis.

        Args:
            frame: The frame to sort.
        """
        return frame

    def sort_frames(self, key: Any = None, reverse: bool = False) -> None:
        """Sorts the contained frames/objects.

        Args:
            key: The key base the sorting from.
            reverse: Determines if this frame will be sorted in reverse order.
        """
        if key is None:
            key = self.frame_sort_key
        self.frames.sort(key=key, reverse=reverse)

    # Container
    @singlekwargdispatchmethod("other")
    def concatenate(self, other: "ArrayFrame" | list) -> ArrayFrameInterface:
        """Concatenates this frame object with another frame or a list.

        Args:
            other: The other object to concatenate this frame with.

        Returns:
            A new frame which is the concatenation of this frame and another object.
        """
        raise TypeError(f"A {type(other)} cannot be used to concatenate a {type(self)}.")

    @concatenate.register
    def _(self, other: "ArrayFrame") -> ArrayFrameInterface:
        """Concatenates this frame object with another frame.

        Args:
            other: The other frame to concatenate this frame with.

        Returns:
            A new frame which is the concatenation of this frame and the other frame.
        """
        return type(self)(frames=self.frames + other.frames, update=self.is_updating)

    @concatenate.register
    def _(self, other: list) -> ArrayFrameInterface:
        """Concatenates this frame object with another list.

        Args:
            other: The other list to concatenate this frame with.

        Returns:
            A new frame which is the concatenation of this frame and another list.
        """
        return type(self)(frames=self.frames + other, update=self.is_updating)

    def append(self, item: Any) -> None:
        """Append an item to the frame.

        Args:
            item: The object to add to this frame.
        """
        self.frames.append(item)

    # Find Inner Indices within Frames
    def find_inner_frame_index(self, super_index: int) -> FrameIndex:
        """Find the frame and inner index of a super index.

        Args:
            super_index: The super index to find.

        Returns:
            The index information as a FrameIndex.
        """
        length = self.length
        frame_start_indices = self.frame_start_indices

        # Check if index is in range.
        if super_index >= length or (super_index + length) < 0:
            raise IndexError("index is out of range")

        # Change negative indexing into positive.
        if super_index < 0:
            super_index = length - super_index

        # Find
        frame_index = bisect_right(frame_start_indices, super_index) - 1
        frame_start_index = frame_start_indices[frame_index]
        frame_inner_index = int(super_index - frame_start_index)
        return FrameIndex(frame_index, frame_start_index, frame_inner_index)

    def find_inner_frame_indices(self, super_indices: Iterable[int]) -> tuple[FrameIndex]:
        """Find the frame and inner index of several super indices.

        Args:
            super_indices: The super indices to find.

        Returns:
            The indices' information as FrameIndex objects.
        """
        length = self.length
        frame_start_indices = self.frame_start_indices
        super_indices = list(super_indices)
        inner_indices = [None] * len(super_indices)

        # Validate Indices
        for i, super_index in enumerate(super_indices):
            # Check if super_index is in range.
            if super_index >= length or (super_index + length) < 0:
                raise IndexError("super_index is out of range")

            # Change negative indexing into positive.
            if super_index < 0:
                super_indices[i] = self.length + super_index

        # Finding Methods
        if len(super_indices) <= 32:  # Few indices to find
            for i, super_index in enumerate(super_indices):
                frame_index = bisect_right(frame_start_indices, super_index) - 1
                frame_start_index = frame_start_indices[frame_index]
                frame_inner_index = int(super_index - frame_start_index)
                inner_indices[i] = FrameIndex(frame_index, frame_start_index, frame_inner_index)
        else:  # Many indices to find
            frame_indices = list(np.searchsorted(frame_start_indices, super_indices, side='right') - 1)
            for i, frame_index in enumerate(frame_indices):
                frame_start_index = frame_start_indices[frame_index]
                frame_inner_index = int(super_indices[i] - frame_start_index)
                inner_indices[i] = FrameIndex(frame_index, frame_start_index, frame_inner_index)

        return tuple(inner_indices)

    def parse_range_super_indices(self, start: int | None = None, stop: int | None = None) -> RangeIndices:
        """Parses indices for a range and returns them as FrameIndex objects.

        Args:
            start: The start index of the range.
            stop: The stop index of the range.

        Returns:
            The start and stop indices as FrameIndex objects in a RangeIndices object.
        """
        if start is not None and stop is not None:
            start_index, stop_index = self.find_inner_frame_indices([start, stop])
        else:
            if start is not None:
                start_index = self.find_inner_frame_index(start)
            else:
                start_index = FrameIndex(0, 0, 0)
            if stop is not None:
                stop_index = self.find_inner_frame_index(stop)
            else:
                stop_frame = len(self.frames) - 1
                stop_index = FrameIndex(stop_frame, self.frame_start_indices[stop_frame], self.lengths[stop_frame])

        return RangeIndices(start_index, stop_index)

    # Get Ranges of Data with Slices
    def get_slices(self, slices: Iterable[slice], frame: bool | None = None) -> ArrayFrameInterface | np.ndarray:
        """Get data from within using slices to determine the ranges.

        Args:
            slices: The slices along the axes to get data from
            frame: Determines if returned object is a Frame or an array, default is this object's setting.

        Returns:
            The requested range.
        """
        if (frame is None and self.returns_frame) or frame:
            return self.get_slices_frame(slices=slices)
        else:
            return self.get_slices_array(slices=slices)

    def get_slices_frame(self, slices: Iterable[slice] | None = None) -> ArrayFrameInterface:
        """Gets a range of data as a new frame.

        Args:
            slices: The ranges to get the data from.

        Returns:
            The requested range as a frame.
        """
        slices = list(slices)
        axis_slice = slices[self.axis]
        range_frame_indices = self.parse_range_super_indices(start=axis_slice.start, stop=axis_slice.stop)

        start_frame = range_frame_indices.start.index
        stop_frame = range_frame_indices.stop.index

        return self.return_frame_type(frames=[self.frames[start_frame:stop_frame]])

    def get_slices_array(self, slices: Iterable[slice | int | None] | None = None) -> np.ndarray:
        """Gets a range of data as an array.

        Args:
            slices: The ranges to get the data from.

        Returns:
            The requested range as an array.
        """
        if slices is None:
            slices = [slice(None)] * len(self.max_shape)

        # Create nan numpy array
        max_shape = self.max_shape
        slices = list(slices)
        full_slices = slices + [slice(None)] * (len(max_shape) - len(slices))
        t_shape = [None] * len(full_slices)
        for i, slice_ in enumerate(full_slices):
            if slice_ is not None:
                start = 0 if slice_.start is None else slice_.start
                stop = max_shape[i] if slice_.stop is None else slice_.stop
                step = 1 if slice_.step is None else slice_.step
                t_shape[i] = (stop - start) // step
            else:
                t_shape[i] = 1
        data = np.empty(shape=t_shape)
        data.fill(np.nan)

        # Get range via filling the array with values
        return self.fill_slices_array(data_array=data, slices=full_slices)

    def fill_slices_array(
        self,
        data_array: np.ndarray,
        array_slices: Iterable[slice] | None = None,
        slices: Iterable[slice | int | None] | None = None,
    ) -> np.ndarray:
        """Fills a given array with values from the contained frames/objects.

        Args:
            data_array: The numpy array to fill.
            array_slices: The slices to fill within the data_array.
            slices: The slices to get the data from.

        Returns:
            The original array but filled.
        """
        slices = list(slices)
        # Get indices range
        da_shape = data_array.shape
        axis_slice = slices[self.axis]
        range_frame_indices = self.parse_range_super_indices(start=axis_slice.start, stop=axis_slice.stop)

        start_frame = range_frame_indices.start.index
        stop_frame = range_frame_indices.stop.index
        axis_slice.start = range_frame_indices.start.inner_index
        axis_slice.stop = inner_stop = range_frame_indices.stop.inner_index

        # Get start and stop array locations
        if array_slices is None:
            array_slices = [slice(None)] * len(da_shape)
        else:
            array_slices = list(array_slices)

        da_axis_slice = array_slices[self.axis]
        array_start = 0 if da_axis_slice.start is None else da_axis_slice.start
        array_stop = da_shape[self.axis] if da_axis_slice.stop is None else da_axis_slice.stop

        # Contained frame/object fill kwargs
        fill_kwargs = {
            "data_array": data_array,
            "array_start": array_slices,
            "slices": slices
        }

        # Get Data
        if start_frame == stop_frame:
            self.frames[start_frame].fill_ranges_array(**fill_kwargs)
        else:
            # First Frame
            frame = self.frames[start_frame]
            f_shape = frame.max_shape
            d_size = np.array(f_shape + (0,) * (len(da_shape) - len(f_shape)))
            da_axis_slice.stop = array_start + d_size
            axis_slice.stop = None
            frame.fill_range_frame(**fill_kwargs)

            # Middle Frames
            axis_slice.stop = None
            for frame in self.frames[start_frame + 1:stop_frame]:
                da_axis_slice.start = da_axis_slice.stop
                da_axis_slice.start += 1
                f_shape = frame.max_shape
                d_size = np.array(f_shape + (0,) * (len(da_shape) - len(f_shape)))
                da_axis_slice.stop = da_axis_slice.start + d_size
                frame.fill_range_frame(**fill_kwargs)

            # Last Frame
            da_axis_slice.start = da_axis_slice.stop
            da_axis_slice.start += 1
            da_axis_slice.stop = array_stop
            fill_kwargs["stop"] = inner_stop
            frame.fill_range_frame(**fill_kwargs)

        return data_array

    # Main Axis Get Range
    def get_main_axis_range(
        self,
        start: int | None = None,
        stop: int | None = None,
        step: int | None = None,
        frame: bool | None = None,
    ) -> ArrayFrameInterface | np.ndarray:
        """Gets a range of data along the main axis.

        Args:
            start: The first super index of the range to get.
            stop: The length of the range to get.
            step: The interval to get the data of the range.
            frame: Determines if returned object is a Frame or an array, default is this object's setting.

        Returns:
            The requested range.
        """
        slices = [slice(None)] * len(self.max_shape)
        slices[self.axis] = slice(start=start, stop=stop, step=step)
        if (frame is None and self.returns_frame) or frame:
            return self.get_slices_frame(slices=slices)
        else:
            return self.get_slices_array(slices=slices)

    def get_main_axis_slice(self, item: slice, frame: bool | None = None) -> ArrayFrameInterface | np.ndarray:
        """Gets a range of data along the main axis using a slice.

        Args:
            item: The slice which is the range to get the data from.
            frame: Determines if returned object is a Frame or an array, default is this object's setting.

        Returns:
            The requested range.
        """
        slices = [slice(None)] * len(self.max_shape)
        slices[self.axis] = item
        if (frame is None and self.returns_frame) or frame:
            return self.get_slices_frame(slices=slices)
        else:
            return self.get_slices_array(slices=slices)

    # Get Frame based on Index
    def get_frame(self, index: int, frame: bool | None = None) -> ArrayFrameInterface | np.ndarray:
        """Get a contained frame/object or data from a contained frame/object.

        Args:
            index: The frame index to get the data from.
            frame: Determines if returned object is a Frame or an array, default is this object's setting.

        Returns:
            The requested frame or data.
        """
        if (frame is None and self.returns_frame) or frame:
            return self.frames[index]
        else:
            return self.frames[index].get_slices_array()

    def get_all_data(self, frame: bool | None = None) -> Any:
        """Get all the contained frames/objects as another frame or data from the contained frames/objects.

        Args:
            frame: Determines if returned object is a Frame or an array, default is this object's setting.

        Returns:
            The new frame or all the data as an array
        """
        if (frame is None and self.returns_frame) or frame:
            return self
        else:
            return self.get_slices_array()

    # Get Frame within by Index
    @singlekwargdispatchmethod("indices")
    def get_from_index(
        self,
        indices: Sized[int | slice | Iterable] | int | slice,
        reverse: bool = False,
        frame: bool | None = True,
    ) -> Any:
        """Gets data from this object if given an index which can be in serval formats.

        Args:
            indices: The indices to find the data from.
            reverse:  Determines, when using a Sized of indices, if it will be read in reverse order.
            frame: Determines if returned object is a Frame or an array, default is this object's setting.

        Returns:
            The requested frame or data.
        """
        raise TypeError(f"A {type(indices)} be used to get from super_index for a {type(self)}.")

    @get_from_index.register(Sized)
    def _(
        self,
        indices: Sized[int | slice | Iterable[slice | int | None]],
        reverse: bool = False,
        frame: bool | None = True,
    ) -> ArrayFrameInterface | np.ndarray:
        """Gets a nested frame or data from within this frame.

        Args:
            indices: A series of indices of the nested frames to get from, can end with slices to get ranges of data.
            reverse: Determines if the indices series will be read in reverse order.
            frame:  Determines if returned object is a Frame or an array, default is this object's setting.

        Returns:
            The requested frame or data.
        """
        indices = list(indices)
        if not reverse:
            index = indices.pop(0)
        else:
            index = indices.pop()

        if indices:
            return self.frames[index].get_from_index(indices=indices, reverse=reverse, frame=frame)
        elif isinstance(index, Iterable):
            return self.get_slices(slices=index, frame=frame)
        elif isinstance(index, int):
            return self.get_from_index(indices=index, frame=frame)
        else:
            return self.get_main_axis_slice(item=indices, frame=frame)

    @get_from_index.register
    def _(self, indices: int, frame: bool | None = True) -> Any:
        """Get a contained frame/object or data from a contained frame/object.

        Args:
            indices: The frame index to get the data from.
            frame: Determines if returned object is a Frame or an array, default is this object's setting.

        Returns:
            The requested frame or data.
        """
        return self.get_frame(index=indices, frame=frame)

    # Combine
    def combine_frames(
        self,
        start: int | None = None,
        stop: int | None = None,
        step: int | None = None
    ) -> ArrayFrameInterface:
        """Combines a range of frames into a single frame.

        Args:
            start: The start frame.
            stop: The stop frame.
            step: The step between frames to combine.

        Returns:
            A single combined frame.
        """
        return self.combine_type(frames=self.frames[start:stop:step])


# Assign Cyclic Definitions
ArrayFrame.default_return_frame_type = ArrayFrame