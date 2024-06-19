# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/005_spans_and_pandas copy.ipynb.

# %% auto 0
__all__ = ['SpanParser', 'Span', 'SpanDtype', 'SpanArray']

# %% ../nbs/005_spans_and_pandas copy.ipynb 3
from abc import ABC, abstractmethod
import pytest

import pandas as pd
from pathlib import Path
from typing import no_type_check, Set, Sequence, Any,Optional,List,Callable,Dict,Union
from pydantic import BaseModel


# %% ../nbs/005_spans_and_pandas copy.ipynb 5
from enum import Enum
from typing import Any
from pydantic import ConfigDict

class Span():
    def __init__(self,start,end):
        self.start = start
        self.end = end

    def __lt__(self, other) -> bool:
        if self.start == other.start:
            return self.end < other.end

        return self.start < other.start
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Span):
            return False
        return self.start == value.start and self.end == value.end

    @classmethod
    def from_val(cls,val):
        if isinstance(val,Span):
            return val
        if isinstance(val, (list, tuple)) and len(val) == 2:
            return Span(start=val[0], end=val[1])
        raise ValueError('Invalid value to create Vector from: {}'.format(val))
    
    def as_tuple(self):
        return (self.start, self.end)

    def __str__(self):
        return f"[{self.start},{self.end})"

    def __repr__(self):
        return str(self)

    # # used for sorting `Span`s in dataframes
    def __hash__(self) -> int:
        return hash((self.start, self.end))

# %% ../nbs/005_spans_and_pandas copy.ipynb 6
import numpy as np
from pandas.core.dtypes.dtypes import PandasExtensionDtype
from pandas.api.extensions import ExtensionArray, ExtensionScalarOpsMixin, register_extension_dtype

@register_extension_dtype
class SpanDtype(PandasExtensionDtype):
    """
    Class to describe the custom Vector data type
    """
    type = Span       # Scalar type for data
    name = 'span'     # String identifying the data type name 

    @classmethod
    def construct_array_type(cls):
        """
        Return array type associated with this dtype
        """
        return SpanArray

    def __str__(self):
        return self.name
    
    def __hash__(self):
        return hash(self.name)

# %% ../nbs/005_spans_and_pandas copy.ipynb 7
from parse import parse,compile
SpanParser = compile('[{start:d},{end:d})')


# %% ../nbs/005_spans_and_pandas copy.ipynb 9
class SpanArray(ExtensionScalarOpsMixin, ExtensionArray):
    """
    Custom Extension Array type for an array of Vectors
    Needs to define:
    - Associated Dtype it is used with
    - How to construct array from sequence of scalars
    - How data is stored and accessed
    - Any custom array methods
    """

    def __init__(self, x_values, y_values, copy=False):
        """
        Initialise array of vectors from component X and Y values 
        (Allows efficient initialisation from existing lists/arrays)
        :param x_values: Sequence/array of vector x-component values
        :param y_values: Sequence/array of vector y-component values
        """
        self.x_values = np.array(x_values, dtype=np.int64, copy=copy)
        self.y_values = np.array(y_values, dtype=np.int64, copy=copy)

    @classmethod
    def _from_sequence_of_strings(
        cls, strings, *, dtype=SpanDtype, copy: bool = False
    ):
        vals=[]
        for string in strings:
            parsed_span = SpanParser.parse(string)
            if parsed_span is None:
                raise ValueError(f'could not parse string "{string}" as a span')
            vals.append(Span(parsed_span['start'],parsed_span['end']))
            
        return cls._from_sequence(vals)

    @classmethod
    def _from_sequence(cls, scalars, *, dtype=None, copy=False):
        """
        Construct a new ExtensionArray from a sequence of scalars. 
        Each element will be an instance of the scalar type for this array,
        or be converted into this type in this method.
        """
        # Construct new array from sequence of values (Unzip vectors into x and y components)
        x_values, y_values = zip(*[Span.from_val(val).as_tuple() for val in scalars])
        return SpanArray(x_values, y_values, copy=copy)

    @classmethod
    def from_vectors(cls, vectors):
        """
        Construct array from sequence of values (vectors)
        Can be provided as Vector instances or list/tuple like (x, y) pairs
        """
        return cls._from_sequence(vectors)

    @classmethod
    def _concat_same_type(cls, to_concat):
        """
        Concatenate multiple arrays of this dtype
        """
        return SpanArray(
            np.concatenate([arr.x_values for arr in to_concat]),
            np.concatenate([arr.y_values for arr in to_concat]),
        )

    @property
    def dtype(self):
        """
        Return Dtype instance (not class) associated with this Array
        """
        return SpanDtype()

    @property
    def nbytes(self):
        """
        The number of bytes needed to store this object in memory.
        """
        return self.x_values.nbytes + self.y_values.nbytes

    def __getitem__(self, item):
        """
        Retrieve single item or slice
        """
        if isinstance(item, int):
            # Get single vector
            return Span(self.x_values[item], self.y_values[item])

        else:
            # Get subset from slice  or boolean array
            return SpanArray(self.x_values[item], self.y_values[item])

    def __eq__(self, other):
        """
        Perform element-wise equality with a given vector value
        """
        if isinstance(other, (pd.Index, pd.Series, pd.DataFrame)):
            return NotImplemented

        return (self.x_values == other[0]) & (self.y_values == other[1])

    def __len__(self):
        return self.x_values.size

    def isna(self):
        """
        Returns a 1-D array indicating if each value is missing
        """
        return np.isnan(self.x_values)

    def take(self, indices, *, allow_fill=False, fill_value=None):
        """
        Take element from array using positional indexing
        """
        from pandas.core.algorithms import take
        if allow_fill and fill_value is None:
            fill_value = self.dtype.na_value

        x_result = take(self.x_values, indices, fill_value=fill_value, allow_fill=allow_fill)
        y_result = take(self.y_values, indices, fill_value=fill_value, allow_fill=allow_fill)
        return SpanArray(x_result, y_result)

    def copy(self):
        """
        Return copy of array
        """
        return SpanArray(np.copy(self.x_values), np.copy(self.y_values))

# Register operator overloads using logic defined in Vector class
SpanArray._add_comparison_ops()
