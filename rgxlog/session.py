# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/04a_session.ipynb.

# %% auto 0
__all__ = ['CSV_DELIMITER', 'PREDEFINED_IE_FUNCS', 'STRING_PATTERN', 'logger', 'GRAMMAR_FILE_NAME', 'format_query_results',
           'tabulate_result', 'queries_to_string', 'Session']

# %% ../nbs/04a_session.ipynb 4
import csv
import logging
import os
import re
from pathlib import Path
from typing import Tuple, List, Union, Optional, Callable, Type, Iterable, no_type_check, Sequence

# %% ../nbs/04a_session.ipynb 5
from lark.lark import Lark
from pandas import DataFrame
from tabulate import tabulate
import os

# %% ../nbs/04a_session.ipynb 6
#| output: false
from .utils import get_base_file_path
from .engine import SqliteEngine
from .ast_node_types import AddFact, RelationDeclaration
from .primitive_types import Span, DataTypes, DataTypeMapping
from .engine import FALSE_VALUE, TRUE_VALUE
from .execution import (Query, FREE_VAR_PREFIX, naive_execution)
from .adding_inference_rules_to_term_graph import AddRulesToTermGraph
from .optimizations_passes import RemoveUselessRelationsFromRule
from .lark_passes import (RemoveTokens, FixStrings, CheckReservedRelationNames,
                                              ConvertSpanNodesToSpanInstances, ConvertStatementsToStructuredNodes,
                                              CheckDefinedReferencedVariables,
                                              CheckReferencedRelationsExistenceAndArity,
                                              CheckReferencedIERelationsExistenceAndArity, CheckRuleSafety,
                                              TypeCheckAssignments, TypeCheckRelations,
                                              SaveDeclaredRelationsSchemas, ResolveVariablesReferences,
                                              ExecuteAssignments, AddStatementsToNetxParseGraph, GenericPass)
from .graphs import TermGraph, NetxStateGraph, GraphBase, TermGraphBase
from .symbol_table import SymbolTable, SymbolTableBase
from .general_utils import rule_to_relation_name, string_to_span, SPAN_PATTERN, QUERY_RESULT_PREFIX
from .passes_utils import LarkNode
from .ie_func.json_path import JsonPath, JsonPathFull
from .ie_func.nlp import (Tokenize, SSplit, POS, Lemma, NER, EntityMentions, CleanXML, Parse, DepParse, Coref, OpenIE, KBP, Quote, Sentiment, TrueCase)
from .ie_func.python_regex import PYRGX, PYRGX_STRING
from .ie_func.rust_spanner_regex import RGX, RGX_STRING, RGX_FROM_FILE, RGX_STRING_FROM_FILE
from .utils import patch_method

# %% ../nbs/04a_session.ipynb 7
CSV_DELIMITER = ";"

# ordered by rgx, json, nlp, etc.
PREDEFINED_IE_FUNCS = [PYRGX, PYRGX_STRING, RGX, RGX_STRING, RGX_FROM_FILE, RGX_STRING_FROM_FILE,
                       JsonPath, JsonPathFull,
                       Tokenize, SSplit, POS, Lemma, NER, EntityMentions, CleanXML, Parse, DepParse, Coref, OpenIE, KBP, Quote, Sentiment,
                       TrueCase]

STRING_PATTERN = re.compile(r"^[^\r\n]+$")

logger = logging.getLogger(__name__)

GRAMMAR_FILE_NAME = 'grammar.lark'

# %% ../nbs/04a_session.ipynb 8
def _infer_relation_type(row: Iterable # an iterable of values, extracted from a csv file or a dataframe
                        ) -> Sequence[DataTypes]: # Inferred tpye list of the given relation
    """
    Guess the relation type based on the data.
    We support both the actual types (e.g. 'Span'), and their string representation ( e.g. `"[0,8)"`).

    **@raise** ValueError: if there is a cell inside `row` of an illegal type.
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

# %% ../nbs/04a_session.ipynb 9
def _verify_relation_types(row: Iterable, expected_types: Iterable[DataTypes]) -> None:
    if _infer_relation_type(row) != expected_types:
        raise Exception(f"row:\n{str(row)}\ndoes not match the relation's types:\n{str(expected_types)}")

# %% ../nbs/04a_session.ipynb 10
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

# %% ../nbs/04a_session.ipynb 11
def format_query_results(query: Query, # the query that was executed, and outputted `query_results`
                         query_results: List # the results after executing the aforementioned query
                         ) -> Union[DataFrame, List]: # a false value, a true value, or a dataframe representing the query + its results
    """
    Formats a single result from the engine into a usable format.
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


# %% ../nbs/04a_session.ipynb 12
def tabulate_result(result: Union[DataFrame, List] # the query result (free variable names are the dataframe's column names)
                    ) -> str: # a tabulated string
    """
    Organizes a query result in a table <br>
    for example: <br>
    ```prolog
    {QUERY_RESULT_PREFIX}'lecturer_of(X, "abigail")':
       X
    -------
     linus
     walter
    ```
    There are two cases in which a table won't be printed:

    1. **Query returned no results**: This will result in an output of `[]`.

    2. **Query returned a single empty tuple**: The output will be `[()]`.
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


# %% ../nbs/04a_session.ipynb 13
def queries_to_string(query_results: List[Tuple[Query, List]] # List[the Query object used in execution, the execution's results (from engine)]
                      ) -> str: # a tabulated string
    """
    Takes in a list of results from the engine and converts them into a single string, which contains
    either a table, a false value (=`[]`), or a true value (=`[tuple()]`), for each result.

    for example:

    ```prolog
    {QUERY_RESULT_PREFIX}'lecturer_of(X, "abigail")':
       X
    -------
     linus
     walter
    ```
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


# %% ../nbs/04a_session.ipynb 14
class Session:
    def __init__(self, 
                 symbol_table: Optional[SymbolTableBase] = None, # symbol table to help with all semantic checks
                 parse_graph: Optional[GraphBase] = None, # an AST that contains nodes which represent commands
                 term_graph: Optional[TermGraphBase] = None): # a graph that holds all the connection between the relations
        """
        A class that serves as the central connection point between various modules in the system.

        This class takes input data and coordinates communication between different modules by sending the relevant parts
        of the input to each module. It also orchestrates the execution of micro passes and handles engine-related tasks. <br>
        Finally, it formats the results before presenting them to the user.

        """
        if symbol_table is None:
            self._symbol_table: SymbolTableBase = SymbolTable()
            self._symbol_table.register_predefined_ie_functions(PREDEFINED_IE_FUNCS)

        else:
            self._symbol_table = symbol_table

        self._parse_graph = NetxStateGraph() if parse_graph is None else parse_graph
        self._term_graph: TermGraphBase = TermGraph() if term_graph is None else term_graph
        self._engine = SqliteEngine()
        self._execution = naive_execution

        self._pass_stack: List[Type[GenericPass]] = [
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
            AddRulesToTermGraph
        ]

        self._grammar = Session._get_grammar_from_file()

        self._parser = Lark(self._grammar, parser='lalr')
    
    @staticmethod
    def _get_grammar_from_file() -> str:
        """
        @return: Grammar from grammar file in string format.
        """

        # Make the grammar_file_path generic no matter if running from notebook or from exported python file
        current_dir = get_base_file_path()

        grammar_file_path = current_dir / 'spanner_workbench'
        with open(grammar_file_path / GRAMMAR_FILE_NAME, 'r') as grammar_file:
            return grammar_file.read()

    def __repr__(self) -> str:
        return "\n".join([repr(self._symbol_table), repr(self._parse_graph)])
    
    def __str__(self) -> str:
        return f'Symbol Table:\n{str(self._symbol_table)}\n\nTerm Graph:\n{str(self._parse_graph)}'

# %% ../nbs/04a_session.ipynb 15
@patch_method
def _run_passes(self: Session, lark_tree: LarkNode, pass_list: list) -> None:
    """
    Runs the passes in pass_list on tree, one after another.
    """
    #logger.debug(f"initial lark tree:\n{lark_tree.pretty()}")
    #logger.debug(f"initial term graph:\n{self._term_graph}")

    for curr_pass in pass_list:
        curr_pass_object = curr_pass(parse_graph=self._parse_graph,
                                        symbol_table=self._symbol_table,
                                        term_graph=self._term_graph)
        new_tree = curr_pass_object.run_pass(tree=lark_tree)
        if new_tree is not None:
            lark_tree = new_tree
            #logger.debug(f"lark tree after {curr_pass.__name__}:\n{lark_tree.pretty()}")

# %% ../nbs/04a_session.ipynb 16
@patch_method
def get_pass_stack(self: Session) -> List[Type[GenericPass]]:
    """
    @return: the current pass stack.
    """

    return self._pass_stack.copy()

# %% ../nbs/04a_session.ipynb 18
@patch_method
def set_pass_stack(self: Session, user_stack: List[Type[GenericPass]] #  a user supplied pass stack
                    ) -> List[Type[GenericPass]]: # success message with the new pass stack
    """
    Sets a new pass stack instead of the current one.
    """

    if type(user_stack) is not list:
        raise TypeError('user stack should be a list of passes')
    for pass_ in user_stack:
        if not issubclass(pass_, GenericPass):
            raise TypeError('user stack should be a subclass of `GenericPass`')

    self._pass_stack = user_stack.copy()
    return self.get_pass_stack()

# %% ../nbs/04a_session.ipynb 20
@patch_method
def print_all_rules(self: Session, head: Optional[str] = None # if specified it will print only rules with the given head relation name
                    ) -> None:
    """
    Prints all the rules that are registered.
    """

    self._term_graph.print_all_rules(head)

# %% ../nbs/04a_session.ipynb 21
@patch_method
def _remove_rule_relation_from_symbols_and_engine(self: Session, relation_name: str) -> None:
    """
    Removes the relation from the symbol table and the execution tables.

    @param relation_name: the name of the relation ot remove.
    """
    self._symbol_table.remove_rule_relation(relation_name)
    self._engine.remove_table(relation_name)

# %% ../nbs/04a_session.ipynb 22
@patch_method
def _add_imported_relation_to_engine(self: Session, relation_table: Iterable, relation_name: str, relation_types: Sequence[DataTypes]) -> None:
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

# %% ../nbs/04a_session.ipynb 23
@patch_method
def import_relation_from_df(self: Session, relation_df: DataFrame, #The DataFrame containing the data to be imported
                            relation_name: str #The name to be assigned to the relation. It can be an existing relation or a new one
                            ) -> None:
    data = relation_df.values.tolist()

    if not isinstance(data, list):
        raise Exception("dataframe could not be converted to list")

    if len(data) < 1:
        raise Exception("dataframe is empty")

    relation_types = _infer_relation_type(data[0])

    self._add_imported_relation_to_engine(data, relation_name, relation_types)

# %% ../nbs/04a_session.ipynb 24
@patch_method
def send_commands_result_into_df(self: Session, commands: str # the commands to run
                                    ) -> Union[DataFrame, List]: # formatted results (possibly a dataframe)
    """
    run commands as usual and output their formatted results into a dataframe (the commands should contain a query)
    """
    commands_results = self.run_commands(commands, print_results=False)
    if len(commands_results) != 1:
        raise Exception("the commands must have exactly one output")

    return format_query_results(*commands_results[0])

# %% ../nbs/04a_session.ipynb 25
@patch_method
def _relation_name_to_query(self: Session, relation_name: str) -> str:
    symbol_table = self._symbol_table
    relation_schema = symbol_table.get_relation_schema(relation_name)
    relation_arity = len(relation_schema)
    query = (f"?{relation_name}(" + ", ".join(f"{FREE_VAR_PREFIX}{i}" for i in range(relation_arity)) + ")")
    return query

# %% ../nbs/04a_session.ipynb 26
@patch_method
def export_relation_into_df(self: Session, relation_name: str) -> Union[DataFrame, List]:
    query = self._relation_name_to_query(relation_name)
    return self.send_commands_result_into_df(query)

# %% ../nbs/04a_session.ipynb 27
@patch_method
def export_relation_into_csv(self: Session, csv_file_name: Path, relation_name: str, delimiter: str = CSV_DELIMITER) -> None:
    query = self._relation_name_to_query(relation_name)
    self.send_commands_result_into_csv(query, csv_file_name, delimiter)

# %% ../nbs/04a_session.ipynb 28
@patch_method
def run_commands(self: Session, query: str, # The user's input
                    print_results: bool = True, # whether to print the results to stdout or not
                    format_results: bool = False # if this is true, return the formatted result instead of the `[Query, List]` pair
                    ) -> (Union[List[Union[List, List[Tuple], DataFrame]], List[Tuple[Query, List]]]): # the results of every query, in a list
    """
    Generates an AST and passes it through the pass stack.
    """
    query_results = []
    parse_tree = self._parser.parse(query)
    for statement in parse_tree.children:
        self._run_passes(statement, self._pass_stack)
        query_result = self._execution(parse_graph=self._parse_graph,
                                        symbol_table=self._symbol_table,
                                        spanner_workbench_engine=self._engine,
                                        term_graph=self._term_graph)
        if query_result is not None:
            query_results.append(query_result)
            if print_results:
                print(queries_to_string([query_result]))

    if format_results:
        return [format_query_results(*query_result) for query_result in query_results]
    else:
        return query_results

# %% ../nbs/04a_session.ipynb 33
@patch_method
def register(self: Session, ie_function: Callable, ie_function_name: str, in_rel: List[DataTypes],
            out_rel: Union[List[DataTypes], Callable[[int], Sequence[DataTypes]]]) -> None:
    """
    Registers an ie function.

    @see params in `IEFunction`'s __init__.
    """
    self._symbol_table.register_ie_function(ie_function, ie_function_name, in_rel, out_rel)

# %% ../nbs/04a_session.ipynb 38
@patch_method
def remove_rule(self: Session, rule: str # The rule to be removed
                ) -> None:
    """
    Remove a rule from the spanner_workbench's engine.
    """
    is_last = self._term_graph.remove_rule(rule)
    if is_last:
        relation_name = rule_to_relation_name(rule)
        self._remove_rule_relation_from_symbols_and_engine(relation_name)

# %% ../nbs/04a_session.ipynb 45
@patch_method
def remove_all_rules(self: Session, rule_head: Optional[str] = None # if rule head is not none we remove all rules with rule_head
                        ) -> None:
    """
    Removes all rules from the engine.
    """

    if rule_head is None:
        self._term_graph = TermGraph()
        relations_names = self._symbol_table.remove_all_rule_relations()
        self._engine.remove_tables(relations_names)
    else:
        self._term_graph.remove_rules_with_head(rule_head)
        self._remove_rule_relation_from_symbols_and_engine(rule_head)

# %% ../nbs/04a_session.ipynb 52
@patch_method
def clear_relation(self: Session, relation_name: str # The name of the relation to clear
                    ) -> None:
    # @raises: Exception if relation does not exist
    if not self._engine.is_table_exists(relation_name):
        raise Exception(f"Relation {relation_name} does not exist")

    self._engine.clear_relation(relation_name)

# %% ../nbs/04a_session.ipynb 59
@patch_method
def send_commands_result_into_csv(self: Session, commands: str, # the commands to run
                                    csv_file_name: Path, # the file into which the output will be written
                                    delimiter: str = CSV_DELIMITER # a csv separator between values
                                    ) -> None:
    """
    run commands as usual and output their formatted results into a csv file (the commands should contain a query)
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

# %% ../nbs/04a_session.ipynb 61
@patch_method
def print_registered_ie_functions(self: Session) -> None:
    """
    Prints information about the registered ie functions.
    """
    self._symbol_table.print_registered_ie_functions()

# %% ../nbs/04a_session.ipynb 63
@patch_method
def remove_ie_function(self: Session, name: str # the name of the ie function to remove
                        ) -> None:
    """
    Removes a function from the symbol table.
    """
    self._symbol_table.remove_ie_function(name)

# %% ../nbs/04a_session.ipynb 65
@patch_method
def remove_all_ie_functions(self: Session) -> None:
    """
    Removes all the ie functions from the symbol table.
    """
    self._symbol_table.remove_all_ie_functions()

# %% ../nbs/04a_session.ipynb 67
@patch_method
def print_all_rules(self: Session, head: Optional[str] = None # if specified it will print only rules with the given head relation name
                    ) -> None:
    """
    Prints all the rules that are registered.
    """

    self._term_graph.print_all_rules(head)

# %% ../nbs/04a_session.ipynb 72
@patch_method
def import_relation_from_csv(self: Session, csv_file_name: Path, #The path to the CSV file that is being imported
                             relation_name: str = None, #The name of the relation. If not provided, it will be derived from the CSV file name
                             delimiter: str = CSV_DELIMITER #The delimiter used in the CSV file
                             )-> None: 
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

# %% ../nbs/04a_session.ipynb 77
@patch_method
def import_relation_from_df(self: Session, relation_df: DataFrame, #The DataFrame containing the data to be imported
                            relation_name: str #The name to be assigned to the relation. It can be an existing relation or a new one
                            ) -> None:
    data = relation_df.values.tolist()

    if not isinstance(data, list):
        raise Exception("dataframe could not be converted to list")

    if len(data) < 1:
        raise Exception("dataframe is empty")

    relation_types = _infer_relation_type(data[0])

    self._add_imported_relation_to_engine(data, relation_name, relation_types)
