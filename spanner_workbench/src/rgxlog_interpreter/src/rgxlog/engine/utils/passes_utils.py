# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../../../../../nbs/08_src.rgxlog_interpreter.src.rgxlog.engine.utils.passes_utils.ipynb.

# %% auto 0
__all__ = ['ParseNodeType', 'assert_expected_node_structure_aux', 'assert_expected_node_structure', 'unravel_lark_node',
           'get_new_rule_nodes']

# %% ../../../../../../../nbs/08_src.rgxlog_interpreter.src.rgxlog.engine.utils.passes_utils.ipynb 4
from enum import Enum

from lark import Tree as LarkNode
from typing import Any, Callable, Iterable

from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.state.graphs import GraphBase, EvalState
from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.utils.expected_grammar import rgxlog_expected_children_names_lists

# %% ../../../../../../../nbs/08_src.rgxlog_interpreter.src.rgxlog.engine.utils.passes_utils.ipynb 5
class ParseNodeType(Enum):
    """
    will be used as parse graph node types.
    """

    ADD_FACT = "add_fact"
    REMOVE_FACT = "remove_fact"
    QUERY = "query"
    RELATION_DECLARATION = "relation_declaration"
    RULE = "rule"

    def __str__(self) -> str:
        return self.value

# %% ../../../../../../../nbs/08_src.rgxlog_interpreter.src.rgxlog.engine.utils.passes_utils.ipynb 6
def assert_expected_node_structure_aux(lark_node: Any) -> None:
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

# %% ../../../../../../../nbs/08_src.rgxlog_interpreter.src.rgxlog.engine.utils.passes_utils.ipynb 7
def assert_expected_node_structure(func: Callable) -> Callable:
    """
    Use this decorator to check whether a method's input lark node has a structure that is expected by the lark passes
    the lark node and its children are checked recursively

    @note that this decorator should only be used on methods that expect lark nodes that weren't converted to
    structured nodes.

    some lark nodes may have multiple structures (e.g. assignment). in this case this check will succeed if the lark
    node has one of those structures.
    """

    def wrapped_method(visitor: Any, lark_node: Any) -> Any:
        assert_expected_node_structure_aux(lark_node)
        return func(visitor, lark_node)

    return wrapped_method

# %% ../../../../../../../nbs/08_src.rgxlog_interpreter.src.rgxlog.engine.utils.passes_utils.ipynb 8
def unravel_lark_node(func: Callable) -> Callable:
    """
    Even after converting a lark tree to use structured nodes, the methods in lark passes will still receive a lark
    node as an input, and the child of said lark node will be the actual structured node that the method will work
    with.

    use this decorator to replace a method's lark node input with its child structured node.
    """

    def wrapped_method(visitor: Any, lark_node: LarkNode) -> Any:
        structured_node = lark_node.children[0]
        return func(visitor, structured_node)

    return wrapped_method

# %% ../../../../../../../nbs/08_src.rgxlog_interpreter.src.rgxlog.engine.utils.passes_utils.ipynb 9
def get_new_rule_nodes(parse_graph: GraphBase) -> Iterable[GraphBase.NodeIdType]:
    """
    Finds all rules that weren't added to the term graph yet.
    """

    return parse_graph.get_all_nodes_with_attributes(type=ParseNodeType.RULE, state=EvalState.NOT_COMPUTED)
