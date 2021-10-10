import csv
import logging
import os
import re
from lark.lark import Lark
from pandas import DataFrame
from pathlib import Path
from tabulate import tabulate
from typing import Tuple, List, Union, Optional, Callable, Type, Iterable, no_type_check, Any, Sequence

import rgxlog
import rgxlog.engine.engine
from rgxlog.engine.datatypes.ast_node_types import AddFact, RelationDeclaration
from rgxlog.engine.datatypes.primitive_types import Span, DataTypes, DataTypeMapping
from rgxlog.engine.engine import FALSE_VALUE, TRUE_VALUE
from rgxlog.engine.execution import (Query, FREE_VAR_PREFIX, naive_execution)
from rgxlog.engine.passes.adding_inference_rules_to_computation_graph import AddRulesToComputationTermGraph
from rgxlog.engine.passes.lark_passes import (RemoveTokens, FixStrings, CheckReservedRelationNames,
                                              ConvertSpanNodesToSpanInstances, ConvertStatementsToStructuredNodes,
                                              CheckDefinedReferencedVariables,
                                              CheckReferencedRelationsExistenceAndArity,
                                              CheckReferencedIERelationsExistenceAndArity, CheckRuleSafety,
                                              TypeCheckAssignments, TypeCheckRelations,
                                              SaveDeclaredRelationsSchemas, ResolveVariablesReferences,
                                              ExecuteAssignments, AddStatementsToNetxParseGraph, GenericPass)
from rgxlog.engine.state.graphs import TermGraph, NetxStateGraph, GraphBase, TermGraphBase
from rgxlog.engine.state.symbol_table import SymbolTable, SymbolTableBase
from rgxlog.engine.utils.general_utils import rule_to_relation_name, string_to_span, SPAN_PATTERN, QUERY_RESULT_PREFIX
from rgxlog.engine.utils.lark_passes_utils import LarkNode
from rgxlog.stdlib.json_path import JsonPath, JsonPathFull
from rgxlog.stdlib.nlp import (Tokenize, SSplit, POS, Lemma, NER, EntityMentions, CleanXML, Parse, DepParse, Coref,
                               OpenIE, KBP, Quote, Sentiment, TrueCase)
from rgxlog.stdlib.python_regex import PYRGX, PYRGX_STRING
from rgxlog.stdlib.rust_spanner_regex import RGX, RGX_STRING, RGX_FROM_FILE, RGX_STRING_FROM_FILE

CSV_DELIMITER = ";"

# ordered by rgx, json, nlp, etc.
PREDEFINED_IE_FUNCS = [PYRGX, PYRGX_STRING, RGX, RGX_STRING, RGX_FROM_FILE, RGX_STRING_FROM_FILE,
                       JsonPath, JsonPathFull,
                       Tokenize, SSplit, POS, Lemma, NER, EntityMentions, CleanXML, Parse, DepParse, Coref, OpenIE, KBP, Quote, Sentiment,
                       TrueCase]

STRING_PATTERN = re.compile(r"^[^\r\n]+$")

logger = logging.getLogger(__name__)


def _infer_relation_type(row: Iterable) -> Sequence[DataTypes]:
    """
    Guess the relation type based on the data.
    We support both the actual types (e.g. 'Span'), and their string representation ( e.g. `"[0,8)"`).

    @param row: an iterable of values, extracted from a csv file or a dataframe.
    @raise ValueError: if there is a cell inside `row` of an illegal type.
    """
    relation_types = []
    for cell in row:
        try:
            int(cell)  # check if the cell can be converted to integer
            relation_types.append(DataTypes.integer)
        except (ValueError, TypeError):
            if isinstance(cell, Span) or re.match(SPAN_PATTERN, cell):
                relation_types.append(DataTypes.span)
            elif re.match(STRING_PATTERN, cell):
                relation_types.append(DataTypes.string)
            else:
                raise ValueError(f"value doesn't match any datatype: {cell}")

    return relation_types


def _verify_relation_types(row: Iterable, expected_types: Iterable[DataTypes]) -> None:
    if _infer_relation_type(row) != expected_types:
        raise Exception(f"row:\n{str(row)}\ndoes not match the relation's types:\n{str(expected_types)}")


def _text_to_typed_data(term_list: Sequence[DataTypeMapping.term], relation_types: Sequence[DataTypes]) -> List[DataTypeMapping.term]:
    transformed_term_list: List[DataTypeMapping.term] = []
    for str_or_object, rel_type in zip(term_list, relation_types):
        if rel_type == DataTypes.span:
            if isinstance(str_or_object, Span):
                transformed_term_list.append(str_or_object)
            else:
                assert isinstance(str_or_object, str), "a span can only be a Span object or a string"
                transformed_span = string_to_span(str_or_object)
                if transformed_span is None:
                    raise TypeError(f"expected a Span, found this instead: {str_or_object}")
                transformed_term_list.append(transformed_span)

        elif rel_type == DataTypes.integer:
            if isinstance(str_or_object, Span):
                raise TypeError(f"expected an int, found Span instead: {str_or_object}")
            transformed_term_list.append(int(str_or_object))
        else:
            assert rel_type == DataTypes.string, f"illegal type given: {rel_type}"
            transformed_term_list.append(str_or_object)

    return transformed_term_list


def format_query_results(query: Query, query_results: List) -> Union[DataFrame, List]:
    """
    Formats a single result from the engine into a usable format.

    @param query: the query that was executed, and outputted `query_results`.
    @param query_results: the results after executing the aforementioned query.
    @return: a false value, a true value, or a dataframe representing the query + its results.
    """
    assert isinstance(query_results, list), "illegal results format"

    # check for the special conditions for which we can't print a table: no results were returned or a single
    # empty tuple was returned

    if query_results == FALSE_VALUE:  # empty list := false
        return FALSE_VALUE
    elif query_results == TRUE_VALUE:  # single tuple := true
        return TRUE_VALUE
    else:
        # convert the resulting tuples to a more organized format
        results_matrix = []
        for result in query_results:
            # span tuples are converted to Span objects
            converted_span_result = [Span(term[0], term[1]) if (isinstance(term, tuple) and len(term) == 2)
                                     else term
                                     for term in result]

            results_matrix.append(converted_span_result)

        # get the free variables of the query, they will be used as headers
        query_free_vars = [term for term, term_type in zip(query.term_list, query.type_list)
                           if term_type is DataTypes.free_var_name]

        return DataFrame(data=results_matrix, columns=query_free_vars)


def tabulate_result(result: Union[DataFrame, List]) -> str:
    """
    Organizes a query result in a table
    for example:
        {QUERY_RESULT_PREFIX}'lecturer_of(X, "abigail")':
          X
       -------
        linus
        walter

    there are two cases where a table will not be printed:
    1. the query returned no results. in this case '[]' will be printed
    2. the query returned a single empty tuple, in this case '[()]' will be printed

    @param result: the query result (free variable names are the dataframe's column names).
    @return: a tabulated string.
    """
    if isinstance(result, DataFrame):
        # query results can be printed as a table
        result_string = tabulate(result, headers="keys", tablefmt="presto", stralign="center", showindex=False)
    else:
        assert isinstance(result, list), "illegal result format"
        if len(result) == 0:
            result_string = "[]"
        else:
            assert len(result) == 1, "illegal result format"
            result_string = "[()]"

    return result_string


def queries_to_string(query_results: List[Tuple[Query, List]]) -> str:
    """
    Takes in a list of results from the engine and converts them into a single string, which contains
    either a table, a false value (=`[]`), or a true value (=`[tuple()]`), for each result.

    for example:

    {QUERY_RESULT_PREFIX}'lecturer_of(X, "abigail")':
      X
    --------
    linus
    walter


    @param query_results: List[the Query object used in execution, the execution's results (from engine)].
    """

    all_result_strings = []
    query_results = list(filter(None, query_results))  # remove Nones
    for query, results in query_results:
        query_result_string = tabulate_result(format_query_results(query, results))
        query_title = f"{QUERY_RESULT_PREFIX}'{query}':"

        # combine the title and table to a single string and save it to the prints buffer
        titled_result_string = f'{query_title}\n{query_result_string}\n'
        all_result_strings.append(titled_result_string)
    return "\n".join(all_result_strings)


class Session:
    def __init__(self, symbol_table: Optional[SymbolTableBase] = None, parse_graph: Optional[GraphBase] = None,
                 term_graph: Optional[TermGraphBase] = None):
        """
        parse_graph is the lark graph which contains is the result of parsing a single statement,
        term_graph is the combined tree of all statements so far, which describes the connection between relations.
        """

        if symbol_table is None:
            self._symbol_table: SymbolTableBase = SymbolTable()
            self._symbol_table.register_predefined_ie_functions(PREDEFINED_IE_FUNCS)

        else:
            self._symbol_table = symbol_table

        self._parse_graph = NetxStateGraph() if parse_graph is None else parse_graph
        self._term_graph: TermGraphBase = TermGraph() if term_graph is None else term_graph
        self._engine = rgxlog.engine.engine.SqliteEngine()
        self._execution = naive_execution

        self._pass_stack = [
            RemoveTokens,
            FixStrings,
            CheckReservedRelationNames,
            ConvertSpanNodesToSpanInstances,
            ConvertStatementsToStructuredNodes,
            CheckDefinedReferencedVariables,
            CheckReferencedRelationsExistenceAndArity,
            CheckReferencedIERelationsExistenceAndArity,
            CheckRuleSafety,
            TypeCheckAssignments,
            TypeCheckRelations,
            SaveDeclaredRelationsSchemas,
            ResolveVariablesReferences,
            ExecuteAssignments,
            AddStatementsToNetxParseGraph,
            AddRulesToComputationTermGraph
        ]

        grammar_file_path = Path(rgxlog.grammar.__file__).parent
        grammar_file_name = 'grammar.lark'
        with open(grammar_file_path / grammar_file_name, 'r') as grammar_file:
            self._grammar = grammar_file.read()

        self._parser = Lark(self._grammar, parser='lalr')

    def _run_passes(self, lark_tree: LarkNode, pass_list: list) -> None:
        """
        Runs the passes in pass_list on tree, one after another.
        """
        logger.debug(f"initial lark tree:\n{lark_tree.pretty()}")
        logger.debug(f"initial term graph:\n{self._term_graph}")

        for curr_pass in pass_list:
            curr_pass_object = curr_pass(parse_graph=self._parse_graph,
                                         symbol_table=self._symbol_table,
                                         term_graph=self._term_graph)
            new_tree = curr_pass_object.run_pass(tree=lark_tree)

            if new_tree is not None:
                lark_tree = new_tree
                logger.debug(f"lark tree after {curr_pass.__name__}:\n{lark_tree.pretty()}")

    def __repr__(self) -> str:
        return "\n".join([repr(self._symbol_table), repr(self._parse_graph)])

    def __str__(self) -> str:
        return f'Symbol Table:\n{str(self._symbol_table)}\n\nTerm Graph:\n{str(self._parse_graph)}'

    @no_type_check
    def run_commands(self, query: str, print_results: bool = True, format_results: bool = False) -> (
            Union[List[Union[List, List[Tuple], DataFrame]], List[Tuple[Query, List]]]):
        """
        Generates an AST and passes it through the pass stack.

        @param format_results: if this is true, return the formatted result instead of the `[Query, List]` pair.
        @param query: the user's input.
        @param print_results: whether to print the results to stdout or not.
        @return: the results of every query, in a list.
        """
        query_results = []
        parse_tree = self._parser.parse(query)

        for statement in parse_tree.children:
            self._run_passes(statement, self._pass_stack)
            query_result = self._execution(parse_graph=self._parse_graph,
                                           symbol_table=self._symbol_table,
                                           rgxlog_engine=self._engine,
                                           term_graph=self._term_graph)
            if query_result is not None:
                query_results.append(query_result)
                if print_results:
                    print(queries_to_string([query_result]))

        if format_results:
            return [format_query_results(*query_result) for query_result in query_results]
        else:
            return query_results

    def register(self, ie_function: Callable, ie_function_name: str, in_rel: List[DataTypes],
                 out_rel: Union[List[DataTypes], Callable[[int], Sequence[DataTypes]]]) -> None:
        """
        Registers an ie function.

        @see params in IEFunction's __init__.
        """
        self._symbol_table.register_ie_function(ie_function, ie_function_name, in_rel, out_rel)

    def get_pass_stack(self) -> List[str]:
        """
        @return: the current pass stack.
        """

        return [pass_.__name__ for pass_ in self._pass_stack]

    def set_pass_stack(self, user_stack: List[Type[GenericPass]]) -> List[str]:
        """
        Sets a new pass stack instead of the current one.

        @param user_stack: a user supplied pass stack.
        @return: success message with the new pass stack.
        """

        if type(user_stack) is not list:
            raise TypeError('user stack should be a list of passes')
        for pass_ in user_stack:
            if not issubclass(pass_, GenericPass):
                raise TypeError('user stack should be a subclass of `GenericPass`')

        self._pass_stack = user_stack.copy()
        return self.get_pass_stack()

    def _remove_rule_relation_from_symbols_and_engine(self, relation_name: str) -> None:
        """
        Removes the relation from the symbol table and the execution tables.

        @param relation_name: the name of the relation ot remove.
        """
        self._symbol_table.remove_rule_relation(relation_name)
        self._engine.remove_table(relation_name)

    def remove_rule(self, rule: str) -> None:
        """
        Remove a rule from the rgxlog's engine.

        @param rule: the rule to be removed.
        """
        is_last = self._term_graph.remove_rule(rule)
        if is_last:
            relation_name = rule_to_relation_name(rule)
            self._remove_rule_relation_from_symbols_and_engine(relation_name)

    def remove_all_rules(self, rule_head: Optional[str] = None) -> None:
        """
        Removes all rules from the engine.

        @param rule_head: if rule head is not none we remove all rules with rule_head.
        """

        if rule_head is None:
            self._term_graph = TermGraph()
            relations_names = self._symbol_table.remove_all_rule_relations()
            self._engine.remove_tables(relations_names)
        else:
            self._term_graph.remove_rules_with_head(rule_head)
            self._remove_rule_relation_from_symbols_and_engine(rule_head)

    @staticmethod
    def _unknown_task_type() -> str:
        return 'unknown task type'

    def _add_imported_relation_to_engine(self, relation_table: Iterable, relation_name: str, relation_types: Sequence[DataTypes]) -> None:
        symbol_table = self._symbol_table
        engine = self._engine
        # first make sure the types are legal, then we add them to the engine (to make sure
        #  we don't add them in case of an error)
        facts = []

        for row in relation_table:
            _verify_relation_types(row, relation_types)
            typed_line = _text_to_typed_data(row, relation_types)
            facts.append(AddFact(relation_name, typed_line, relation_types))

        # declare relation if it does not exist
        if not symbol_table.contains_relation(relation_name):
            engine.declare_relation_table(RelationDeclaration(relation_name, relation_types))
            symbol_table.add_relation_schema(relation_name, relation_types, False)

        for fact in facts:
            engine.add_fact(fact)

    def import_relation_from_csv(self, csv_file_name: Path, relation_name: str = None, delimiter: str = CSV_DELIMITER) -> None:
        if not Path(csv_file_name).is_file():
            raise IOError("csv file does not exist")

        if os.stat(csv_file_name).st_size == 0:
            raise IOError("csv file is empty")

        # the relation_name is either an argument or the file's name
        if relation_name is None:
            relation_name = Path(csv_file_name).stem

        with open(csv_file_name) as fh:
            reader = csv.reader(fh, delimiter=delimiter)

            # read first line and go back to start of file - make sure there is no empty line!
            relation_types = _infer_relation_type(next(reader))
            fh.seek(0)

            self._add_imported_relation_to_engine(reader, relation_name, relation_types)

    def import_relation_from_df(self, relation_df: DataFrame, relation_name: str) -> None:

        data = relation_df.values.tolist()

        if not isinstance(data, list):
            raise Exception("dataframe could not be converted to list")

        if len(data) < 1:
            raise Exception("dataframe is empty")

        relation_types = _infer_relation_type(data[0])

        self._add_imported_relation_to_engine(data, relation_name, relation_types)

    def send_commands_result_into_csv(self, commands: str, csv_file_name: Path, delimiter: str = CSV_DELIMITER) -> None:
        """
        run commands as usual and output their formatted results into a csv file (the commands should contain a query)
        @param commands: the commands to run
        @param csv_file_name: the file into which the output will be written
        @param delimiter: a csv separator between values
        @return: None
        """
        commands_results = self.run_commands(commands, print_results=False)
        if len(commands_results) != 1:
            raise Exception("the commands must have exactly one output")

        formatted_result = format_query_results(*commands_results[0])

        if isinstance(formatted_result, DataFrame):
            formatted_result.to_csv(csv_file_name, index=False, sep=delimiter)
        else:
            # true or false
            with open(csv_file_name, "w", newline="") as f:
                writer = csv.writer(f, delimiter=delimiter)
                writer.writerows(formatted_result)

    def send_commands_result_into_df(self, commands: str) -> Union[DataFrame, List]:
        """
        run commands as usual and output their formatted results into a dataframe (the commands should contain a query)
        @param commands: the commands to run
        @return: formatted results (possibly a dataframe)
        """
        commands_results = self.run_commands(commands, print_results=False)
        if len(commands_results) != 1:
            raise Exception("the commands must have exactly one output")

        return format_query_results(*commands_results[0])

    def _relation_name_to_query(self, relation_name: str) -> str:
        symbol_table = self._symbol_table
        relation_schema = symbol_table.get_relation_schema(relation_name)
        relation_arity = len(relation_schema)
        query = (f"?{relation_name}(" + ", ".join(f"{FREE_VAR_PREFIX}{i}" for i in range(relation_arity)) + ")")
        return query

    def export_relation_into_df(self, relation_name: str) -> Union[DataFrame, List]:
        query = self._relation_name_to_query(relation_name)
        return self.send_commands_result_into_df(query)

    def export_relation_into_csv(self, csv_file_name: Path, relation_name: str, delimiter: str = CSV_DELIMITER) -> None:
        query = self._relation_name_to_query(relation_name)
        self.send_commands_result_into_csv(query, csv_file_name, delimiter)

    def print_registered_ie_functions(self) -> None:
        """
        Prints information about the registered ie functions.
        """
        self._symbol_table.print_registered_ie_functions()

    def remove_ie_function(self, name: str) -> None:
        """
        Removes a function from the symbol table.

        @param name: the name of the ie function to remove.
        """
        self._symbol_table.remove_ie_function(name)

    def remove_all_ie_functions(self) -> None:
        """
        Removes all the ie functions from the symbol table.
        """
        self._symbol_table.remove_all_ie_functions()

    def print_all_rules(self, head: Optional[str] = None) -> None:
        """
        Prints all the rules that are registered.

        @param head: if specified it will print only rules with the given head relation name.
        """

        self._term_graph.print_all_rules(head)


if __name__ == "__main__":
    # this is for debugging. don't shadow variables like `query`, that's annoying
    logger = logging.getLogger()
    logger.setLevel(level=logging.DEBUG)
    # logging.basicConfig(level=logging.DEBUG)
    my_session = Session()
    my_session.register(lambda x: [(x,)], "ID", [DataTypes.integer], [DataTypes.integer])
    my_commands = """
            new A(int, int)
            new B(int, int, int)
            B(1, 1, 1)
            B(1, 2, 1)
            B(2, 3, 1)
            A(1, 2)
            A(1, 1)
            C(X, Y) <- A(X, Y), B(Y, X, Z)
            ?C(X,Y)
        """

    """
    relations = [a(X,Y), b(Y)] ->
    dict = {X:[(a(X,Y),0)], Y:[(a(X,Y),1),(b(Y),0)]
    """

    my_session.run_commands(my_commands)
