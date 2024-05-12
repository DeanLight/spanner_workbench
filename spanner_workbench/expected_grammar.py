# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01a_expected_grammar.ipynb.

# %% auto 0
__all__ = ['spannerlog_expected_children_names_lists']

# %% ../nbs/01a_expected_grammar.ipynb 3
from typing import Sequence, Dict

# %% ../nbs/01a_expected_grammar.ipynb 5
spannerlog_expected_children_names_lists: Dict[str, Sequence] = {

    'assignment': [
        ['var_name', 'string'],
        ['var_name', 'integer'],
        ['var_name', 'span'],
        ['var_name', 'var_name'],
    ],

    'read_assignment': [
        ['var_name', 'string'],
        ['var_name', 'var_name']
    ],

    'relation_declaration': [['relation_name', 'decl_term_list']],

    'rule': [['rule_head', 'rule_body_relation_list']],

    'rule_head': [['relation_name', 'free_var_name_list']],

    'relation': [['relation_name', 'term_list']],

    'ie_relation': [['relation_name', 'term_list', 'term_list']],

    'query': [['relation_name', 'term_list']],

    'add_fact': [['relation_name', 'const_term_list']],

    'remove_fact': [['relation_name', 'const_term_list']],

    'span': [
        ['integer', 'integer'],
        []  # allow empty list to support spans that were converted a datatypes.Span instance
    ],

    'integer': [[]],

    'string': [[]],

    'relation_name': [[]],

    'var_name': [[]],

    'free_var_name': [[]]
}