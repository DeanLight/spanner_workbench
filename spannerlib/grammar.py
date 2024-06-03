# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/002_spannerlog_grammar.ipynb.

# %% auto 0
__all__ = ['logger', 'SpannerlogGrammar', 'lark_to_nx_aux', 'lark_to_nx', 'parse_spannerlog']

# %% ../nbs/002_spannerlog_grammar.ipynb 4
from typing import no_type_check, Set, Sequence, Any, Callable
from typing import Sequence, Dict
from lark import Lark,Token, Tree, Transformer
import yaml
import networkx as nx

import logging
logger = logging.getLogger(__name__)
from graph_rewrite import rewrite,rewrite_iter,draw

from .utils import checkLogs, UniqueId


# %% ../nbs/002_spannerlog_grammar.ipynb 6
SpannerlogGrammar = r"""
start: (_NEWLINE)* (statement (_NEWLINE)+)* (statement)?

?statement: relation_declaration
          | add_fact
          | remove_fact
          | rule
          | query
          | assignment

assignment: var_name "=" string
          | var_name "=" span
          | var_name "=" int
          | var_name "=" var_name
          | var_name "=" "read" "(" string ")" -> read_assignment
          | var_name "=" "read" "(" var_name ")" -> read_assignment

relation_declaration: "new" _SEPARATOR relation_name "(" decl_term_list ")"

decl_term_list: decl_term ("," decl_term)*

?decl_term: "str" -> decl_string
          | "span" -> decl_span
          | "int" -> decl_int

rule: rule_head "<-" rule_body_relation_list

rule_head: relation_name "(" free_var_name_list ")"

rule_body_relation_list: rule_body_relation ("," rule_body_relation)*

?rule_body_relation: relation
                   | ie_relation

relation: relation_name "(" term_list ")"

ie_relation: relation_name "(" term_list ")" "->" "(" term_list ")"

query: "?" relation_name "(" term_list ")"

term_list: term ("," term)*

?term: const_term
     | free_var_name

add_fact: relation_name "(" const_term_list ")"
        | relation_name "(" const_term_list ")" "<-" _TRUE

remove_fact: relation_name "(" const_term_list ")" "<-" _FALSE

const_term_list: const_term ("," const_term)*

?const_term: span
          | string
          | int
          | var_name

span: "[" int "," int ")"

int: INT -> integer

string: STRING

free_var_name_list: free_var_name ("," free_var_name)*

relation_name: LOWER_CASE_NAME
             | UPPER_CASE_NAME

var_name: LOWER_CASE_NAME

free_var_name : UPPER_CASE_NAME

_TRUE: "True"
_FALSE: "False"

LOWER_CASE_NAME: ("_"|LCASE_LETTER) ("_"|LETTER|DIGIT)*
UPPER_CASE_NAME: UCASE_LETTER ("_"|LETTER|DIGIT)*

_COMMENT: "#" /[^\n]*/

_SEPARATOR: (_WS_INLINE | _LINE_OVERFLOW_ESCAPE)+

STRING: "\"" (_STRING_INTERNAL (_LINE_OVERFLOW_ESCAPE)+)* _STRING_INTERNAL "\""

_LINE_OVERFLOW_ESCAPE: "\\" _NEWLINE

_NEWLINE: CR? LF
CR : /\r/
LF : /\n/

LCASE_LETTER: "a".."z"
UCASE_LETTER: "A".."Z"
LETTER: UCASE_LETTER | LCASE_LETTER
DIGIT: "0".."9"
_WS_INLINE: (" "|/\t/)+
%ignore _WS_INLINE
_STRING_INTERNAL: /.*?/ /(?<!\\)(\\\\)*?/
INT: DIGIT+
%ignore _LINE_OVERFLOW_ESCAPE
%ignore _COMMENT
"""

# %% ../nbs/002_spannerlog_grammar.ipynb 11
import itertools
def lark_to_nx_aux(tree,node_id,g,counter):
    if isinstance(tree, Token):
        g.add_node(node_id,val=tree.value)
    elif isinstance(tree, Tree):
        if isinstance(tree.data,Token):
            node_type = tree.data.value
        else:
            node_type = tree.data
        g.add_node(node_id,type=node_type)
        for i,child in enumerate(tree.children):
            child_id = next(counter)
            g.add_edge(node_id,child_id,idx=i)
            lark_to_nx_aux(child,child_id,g,counter)
            


def lark_to_nx(t):
    g = nx.DiGraph()
    counter = itertools.count()
    lark_to_nx_aux(t,next(counter),g,counter)
    return g
    




# %% ../nbs/002_spannerlog_grammar.ipynb 12
def parse_spannerlog(spannerlog_code: str, # code to parse
                     start='start', # non terminal symbol to start parsing from
                     as_string=False, # whether to return the parse tree as a pretty string
                     as_tree=False, # whether to return as a lark Tree object
                     as_nx=True, # whether to return as an networkx graph
                     split_statements=False, # whether to return a list of individual statements
                     ):
    parser = Lark(SpannerlogGrammar, parser='lalr',start=start)
    tree = parser.parse(spannerlog_code)
    if as_string:
        if split_statements:
            return [s.pretty() for s in tree.children]
        return tree.pretty()
    if as_tree:
        if split_statements:
            return tree.children
        return tree
    if as_nx:
        if split_statements:
            return [lark_to_nx(s) for s in tree.children]
        return lark_to_nx(tree)

