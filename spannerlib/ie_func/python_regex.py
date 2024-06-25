# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/ie_func/04c_python_regex.ipynb.

# %% auto 0
__all__ = ['PYRGX_STRING', 'PYRGX', 'py_rgx_string', 'py_rgx']

# %% ../../nbs/ie_func/04c_python_regex.ipynb 3
import re
from typing import Iterable, Sequence

from ..span import Span

# %% ../../nbs/ie_func/04c_python_regex.ipynb 4
def py_rgx_string(text: str, regex_pattern: str) -> Iterable[Sequence]:
    """
    An IE function which runs regex using python's `re` and yields tuples of strings.

    @param text: The input text for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of strings that represents the results.
    """
    compiled_rgx = re.compile(regex_pattern)
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_strings = [match.group()]
        else:
            matched_strings = [group for group in match.groups()]
        yield matched_strings

# %% ../../nbs/ie_func/04c_python_regex.ipynb 5
PYRGX_STRING = [
    'py_rgx_string',
    py_rgx_string,
    [str, str],
    lambda output_arity: [str] * output_arity
]

# %% ../../nbs/ie_func/04c_python_regex.ipynb 6
def py_rgx(text: str, regex_pattern: str) -> Iterable[Sequence]:
    """
    An IE function which runs regex using python's `re` and yields tuples of spans.

    @param text: The input text for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of spans that represents the results.
    """
    compiled_rgx = re.compile(regex_pattern)
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_spans = [match.span()]
        else:
            matched_spans = [match.span(i) for i in range(1, num_groups + 1)]
        yield matched_spans

# %% ../../nbs/ie_func/04c_python_regex.ipynb 7
PYRGX = [
    'py_rgx_span',
    py_rgx,
    [str, str],
    lambda output_arity: [Span] * output_arity
]
