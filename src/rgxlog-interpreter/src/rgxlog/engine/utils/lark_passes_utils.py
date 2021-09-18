"""
this module contains helper functions and function decorators that are used in lark passes
"""
from lark import Tree as LarkNode
from typing import Set

from rgxlog.engine.datatypes.ast_node_types import Rule
from rgxlog.engine.utils.expected_grammar import rgxlog_expected_children_names_lists
from rgxlog.engine.utils.general_utils import get_input_free_var_names, get_output_free_var_names


def assert_expected_node_structure_aux(lark_node):
    """
    Checks whether a lark node has a structure that the lark passes expect.

    @param: lark_node: the lark node to be checked.
    """

    # check if lark_node is really a lark node. this is done because applying the check recursively might result in
    # some children being literal values and not lark nodes
    if isinstance(lark_node, LarkNode):
        node_type = lark_node.data
        if node_type in rgxlog_expected_children_names_lists:

            # this lark node's structure can be checked, get its children and expected children lists
            children_names = [child.data for child in lark_node.children if isinstance(child, LarkNode)]
            expected_children_names_lists = rgxlog_expected_children_names_lists[node_type]

            # check if the node's children names match one of the expected children names lists
            if children_names not in expected_children_names_lists:
                # the node has an unexpected structure, raise an exception
                expected_children_list_strings = [str(children) for children in expected_children_names_lists]
                expected_children_string = '\n'.join(expected_children_list_strings)
                raise Exception(f'node of type "{node_type}" has unexpected children: {children_names}\n'
                                f'expected one of the following children lists:\n'
                                f'{expected_children_string}')

        # recursively check the structure of the node's children
        for child in lark_node.children:
            assert_expected_node_structure_aux(child)


def assert_expected_node_structure(func):
    """
    Use this decorator to check whether a method's input lark node has a structure that is expected by the lark passes
    the lark node and its children are checked recursively

    @note that this decorator should only be used on methods that expect lark nodes that weren't converted to
    structured nodes.

    some lark nodes may have multiple structures (e.g. assignment). in this case this check will succeed if the lark
    node has one of those structures.
    """

    def wrapped_method(visitor, lark_node):
        assert_expected_node_structure_aux(lark_node)
        ret = func(visitor, lark_node)
        return ret

    return wrapped_method


def unravel_lark_node(func):
    """
    Even after converting a lark tree to use structured nodes, the methods in lark passes will still receive a lark
    node as an input, and the child of said lark node will be the actual structured node that the method will work
    with.

    use this decorator to replace a method's lark node input with its child structured node.
    """

    def wrapped_method(visitor, lark_node):
        structured_node = lark_node.children[0]
        return func(visitor, structured_node)

    return wrapped_method


def get_size_difference(set1: Set, set2: Set) -> int:
    """
    A utility function to be used as the distance function of the fixed point algorithm.

    @return: the size difference of set1 and set2.
    """
    size_difference = abs(len(set1) - len(set2))
    return size_difference


def get_bound_free_vars(rule: Rule, known_bound_free_vars: Set) -> Set:
    """
    a utility function to be used as the step function of the fixed point algorithm.
    this function iterates over all of the rule body relations, checking if each one of them is safe.
    if a rule is found to be safe, this function will mark its output free variables as bound.

    @param rule: a rule
    @param known_bound_free_vars: a set of the free variables in the rule that are known to be bound.
    @return: a union of 'known_bound_free_vars' with the bound free variables that were found.
    """

    for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
        # check if all of its input free variable terms of the relation are bound
        input_free_vars = get_input_free_var_names(relation)
        unbound_input_free_vars = input_free_vars.difference(known_bound_free_vars)
        if len(unbound_input_free_vars) == 0:
            # all input free variables are bound, mark the relation's output free variables as bound
            output_free_vars = get_output_free_var_names(relation)
            known_bound_free_vars = known_bound_free_vars.union(output_free_vars)

    return known_bound_free_vars
