# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../../../../../nbs/10_src.rgxlog_interpreter.src.rgxlog.engine.passes.optimizations_passes.ipynb.

# %% auto 0
__all__ = ['PruneUnnecessaryProjectNodes', 'RemoveUselessRelationsFromRule']

# %% ../../../../../../../nbs/10_src.rgxlog_interpreter.src.rgxlog.engine.passes.optimizations_passes.ipynb 3
from fastcore.utils import *

# %% ../../../../../../../nbs/10_src.rgxlog_interpreter.src.rgxlog.engine.passes.optimizations_passes.ipynb 4
from typing import Any, Set, Union, List, Tuple

from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.datatypes.ast_node_types import IERelation, Relation, Rule
from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.datatypes.primitive_types import DataTypes
from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.passes.lark_passes import GenericPass
from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.state.graphs import TermGraphBase, GraphBase, TermNodeType, TYPE, VALUE
from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.utils.general_utils import get_output_free_var_names, get_input_free_var_names, fixed_point
from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.utils.passes_utils import get_new_rule_nodes

# %% ../../../../../../../nbs/10_src.rgxlog_interpreter.src.rgxlog.engine.passes.optimizations_passes.ipynb 5
class PruneUnnecessaryProjectNodes(GenericPass):
    """
    This class prunes project nodes that gets a relation with one column (therefore, the project is redundant).
    For example, the rule A(X) <- B(X) will yield the following term graph:
        rule_rel node (of A)
            union node
                project node (on X)
                   get_rel node (get B)
    since we project a relation with one column, after this pass the term graph will be:
        rule_rel node (of A)
            union node
                get_rel node (get B)
    """

    def __init__(self, term_graph: TermGraphBase, **kwargs: Any) -> None:
        self.term_graph = term_graph
        
    def run_pass(self, **kwargs: Any) -> None:
        pass

# %% ../../../../../../../nbs/10_src.rgxlog_interpreter.src.rgxlog.engine.passes.optimizations_passes.ipynb 6
@patch
def run_pass(self: PruneUnnecessaryProjectNodes, **kwargs: Any) -> None:
    self.prune_project_nodes()

# %% ../../../../../../../nbs/10_src.rgxlog_interpreter.src.rgxlog.engine.passes.optimizations_passes.ipynb 7
@patch
def prune_project_nodes(self: PruneUnnecessaryProjectNodes) -> None:
    """
    Prunes the redundant project nodes.
    """

    project_nodes = self.term_graph.get_all_nodes_with_attributes(type=TermNodeType.PROJECT)
    for project_id in project_nodes:
        if self.is_input_relation_of_node_has_arity_of_one(project_id):
            # in this case the input relations of the project node has arity of one so we prune to node
            # the node has exactly one child so we connect the child to project's node parent (it's a union node)

            self.term_graph.add_edge(self.term_graph.get_parent(project_id), self.term_graph.get_child(project_id))
            self.term_graph.remove_node(project_id)

# %% ../../../../../../../nbs/10_src.rgxlog_interpreter.src.rgxlog.engine.passes.optimizations_passes.ipynb 8
@patch
def is_input_relation_of_node_has_arity_of_one(self: PruneUnnecessaryProjectNodes, node_id: GraphBase.NodeIdType) -> bool:
    """
    @param node_id: id of the node.
    @note: we expect id of project/join node.
    @return: the arity of the relation that the node gets during the execution.
    """

    # this methods suppose to work for both project nodes and join nodes.
    # project nodes always have one child while join nodes always have more than one child.
    # for that reason, we traverse all the children of the node.
    node_ids = self.term_graph.get_children(node_id)
    free_vars: Set[str] = set()

    def is_relation_has_one_free_var(relation_: Union[Relation, IERelation]) -> bool:
        """
        Check whether relation is only one free variable.
        @param relation_: a relation or an ie_relation.
        """

        return len(relation_.get_term_list()) == 1

    for node_id in node_ids:
        node_attrs = self.term_graph[node_id]
        node_type = node_attrs[TYPE]

        if node_type in (TermNodeType.GET_REL, TermNodeType.RULE_REL, TermNodeType.CALC):
            relation = node_attrs[VALUE]
            # if relation has more than one free var we can't prune the project
            if not is_relation_has_one_free_var(relation):
                return False

            free_vars |= set(relation.get_term_list())

        elif node_type is TermNodeType.SELECT:
            relation_child_id = self.term_graph.get_child(node_id)
            relation = self.term_graph[relation_child_id][VALUE]
            if not is_relation_has_one_free_var(relation):
                return False

            relation_free_vars = [var for var, var_type in zip(relation.get_term_list(), relation.get_type_list()) if var_type is DataTypes.free_var_name]
            free_vars |= set(relation_free_vars)

        elif node_type is TermNodeType.JOIN:
            # the input of project node is the same as the input of the join node
            return self.is_input_relation_of_node_has_arity_of_one(node_id)

    return len(free_vars) == 1

# %% ../../../../../../../nbs/10_src.rgxlog_interpreter.src.rgxlog.engine.passes.optimizations_passes.ipynb 9
class RemoveUselessRelationsFromRule(GenericPass):
    """
    This pass removes duplicated relations from a rule.
    For example, the rule A(X) <- B(X), C(Y) contains a redundant relation (C(Y)).
    After this pass the rule will be A(X) <- B(X).

    @note: in the rule A(X) <- B(X, Y), C(Y); C(Y) is not redundant!
    """

    def __init__(self, parse_graph: GraphBase, **kwargs: Any) -> None:
        self.parse_graph = parse_graph
        
    @staticmethod
    def remove_useless_relations(rule: Rule) -> None:
        """
        Finds redundant relations and removes them from the rule.
        @param rule: a rule.
        """
        relevant_free_vars = set(rule.head_relation.get_term_list())

        # relation without free vars are always relevant
        initial_useless_relations_and_types = [(rel, rel_type) for rel, rel_type in zip(rule.body_relation_list, rule.body_relation_type_list)
                                               if len(get_output_free_var_names(rel)) != 0]

        def step_function(current_useless_relations_and_types: List[Tuple[Union[Relation, IERelation], str]]) -> List[Tuple[Union[Relation, IERelation], str]]:
            """
            Used by fixed pont algorithm.

            @param current_useless_relations_and_types: current useless relations and their types
            @return: useless relations after considering the new relevant free vars.
            """

            next_useless_relations_and_types = []
            for relation, rel_type in current_useless_relations_and_types:
                term_list = get_output_free_var_names(relation)
                if len(relevant_free_vars.intersection(term_list)) == 0:
                    next_useless_relations_and_types.append((relation, rel_type))
                else:
                    relevant_free_vars.update(term_list)
                    relevant_free_vars.update(get_input_free_var_names(relation))

            return next_useless_relations_and_types

        useless_relations_and_types = fixed_point(start=initial_useless_relations_and_types, step=step_function, distance=lambda x, y: int(len(x) != len(y)))

        relevant_relations_and_types = set(zip(rule.body_relation_list, rule.body_relation_type_list)).difference(useless_relations_and_types)
        new_body_relation_list, new_body_relation_type_list = zip(*relevant_relations_and_types)
        rule.body_relation_list = list(new_body_relation_list)
        rule.body_relation_type_list = list(new_body_relation_type_list)
    def run_pass(self, **kwargs: Any) -> None:
        pass

# %% ../../../../../../../nbs/10_src.rgxlog_interpreter.src.rgxlog.engine.passes.optimizations_passes.ipynb 10
@patch
def run_pass(self: RemoveUselessRelationsFromRule, **kwargs: Any) -> None:
    rules = get_new_rule_nodes(self.parse_graph)
    for rule_node_id in rules:
        rule: Rule = self.parse_graph[rule_node_id][VALUE]
        RemoveUselessRelationsFromRule.remove_useless_relations(rule)
