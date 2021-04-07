import csv
import os
import re
from pathlib import Path

import rgxlog
from lark.lark import Lark
from lark.visitors import Visitor_Recursive, Interpreter, Visitor, Transformer
from pandas import DataFrame
from rgxlog.engine import execution
from rgxlog.engine.execution import GenericExecution, ExecutionBase, AddFact, DataTypes, RelationDeclaration
from rgxlog.engine.passes.lark_passes import (RemoveTokens, FixStrings, CheckReservedRelationNames,
                                              ConvertSpanNodesToSpanInstances, ConvertStatementsToStructuredNodes,
                                              CheckDefinedReferencedVariables,
                                              CheckForRelationRedefinitions, CheckReferencedRelationsExistenceAndArity,
                                              CheckReferencedIERelationsExistenceAndArity, CheckRuleSafety,
                                              TypeCheckAssignments, TypeCheckRelations,
                                              SaveDeclaredRelationsSchemas, ReorderRuleBody, ResolveVariablesReferences,
                                              ExecuteAssignments,
                                              AddStatementsToNetxTermGraph)
from rgxlog.engine.message_definitions import Request, Response
from rgxlog.engine.state.symbol_table import SymbolTable
from rgxlog.engine.state.term_graph import NetxTermGraph

SPAN_PATTERN = re.compile(r"^\[\d+;\d+\]$")
STRING_PATTERN = re.compile(r"^[^\r\n]+$")


def _infer_relation_type(row: iter):
    # TODO: does not support tuples
    relation_types = []
    for cell in row:
        if cell.isdigit():
            relation_types.append(DataTypes.integer)
        elif re.match(SPAN_PATTERN, cell):
            relation_types.append(DataTypes.span)
        elif re.match(STRING_PATTERN, cell):
            # TODO: is this pattern correct?
            relation_types.append(DataTypes.string)
        else:
            raise Exception(f"illegal type in csv: {cell}")

    return relation_types


def _verify_relation_types(row, expected_types):
    if _infer_relation_type(row) != expected_types:
        raise Exception(f"row:\n{str(row)}\ndoes not match the relation's types:\n{str(expected_types)}")


class Session:
    def __init__(self, debug=False):
        self._symbol_table = SymbolTable()
        self._term_graph = NetxTermGraph()
        self._execution = execution.PydatalogEngine(debug)

        self._pass_stack = [
            RemoveTokens,
            FixStrings,
            CheckReservedRelationNames,
            ConvertSpanNodesToSpanInstances,
            ConvertStatementsToStructuredNodes,
            CheckDefinedReferencedVariables,
            # CheckForRelationRedefinitions,
            CheckReferencedRelationsExistenceAndArity,
            CheckReferencedIERelationsExistenceAndArity,
            CheckRuleSafety,
            TypeCheckAssignments,
            TypeCheckRelations,
            SaveDeclaredRelationsSchemas,
            ReorderRuleBody,
            ResolveVariablesReferences,
            ExecuteAssignments,
            AddStatementsToNetxTermGraph,
            GenericExecution
        ]

        grammar_file_path = os.path.dirname(rgxlog.grammar.__file__)
        grammar_file_name = 'grammar.lark'
        with open(f'{grammar_file_path}/{grammar_file_name}', 'r') as grammar_file:
            self._grammar = grammar_file.read()

        self._parser = Lark(self._grammar, parser='lalr', debug=True)

    def _run_passes(self, tree, pass_list):
        """
        Runs the passes in pass_list on tree, one after another.
        """
        for cur_pass in pass_list:
            if issubclass(cur_pass, Visitor) or issubclass(cur_pass, Visitor_Recursive) or \
                    issubclass(cur_pass, Interpreter):
                cur_pass(symbol_table=self._symbol_table, term_graph=self._term_graph).visit(tree)
            elif issubclass(cur_pass, Transformer):
                tree = cur_pass(symbol_table=self._symbol_table, term_graph=self._term_graph).transform(tree)
            elif issubclass(cur_pass, ExecutionBase):
                cur_pass(
                    term_graph=self._term_graph,
                    symbol_table=self._symbol_table,
                    rgxlog_engine=self._execution
                ).execute()
            else:
                raise Exception(f'invalid pass: {cur_pass}')
        return tree

    def __repr__(self):
        return [repr(self._symbol_table), repr(self._term_graph)]

    def __str__(self):
        return f'Symbol Table:\n{str(self._symbol_table)}\n\nTerm Graph:\n{str(self._term_graph)}'

    def run_query(self, query):
        """
        generates an AST and passes it through the pass stack
        Args:
            query: the query

        Returns: the query result or an error if the query failed
        """

        try:
            parse_tree = self._parser.parse(query)
        except Exception as e:
            return f'exception during parsing {e}'

        try:
            statements = [statement for statement in parse_tree.children]
            for statement in statements:
                self._run_passes(statement, self._pass_stack)
        except Exception as e:
            self._execution.flush_prints_buffer()  # clear the prints buffer as the execution failed
            raise

        return self._execution.flush_prints_buffer()

    def register(self, ie_function, ie_function_name, in_rel, out_rel, is_output_const=True):
        # if ie_function_name.startswith("__"):
        #     raise Exception(f'{ie_function_name} is a reserved name.')
        self._symbol_table.register_ie_function(ie_function, ie_function_name, in_rel, out_rel, is_output_const)

    def delete_rule(self, rule_head: str):
        pass

    def get_pass_stack(self):
        """
        Returns: the current pass stack
        """
        return [pass_.__name__ for pass_ in self._pass_stack]

    def set_pass_stack(self, user_stack):
        """
        sets a new pass stack instead of the current one
        Args:
            user_stack: a user supplied pass stack

        Returns: success message with the new pass stack
        """

        if type(user_stack) is not list:
            raise TypeError('user stack should be a list of pass names (strings)')
        for pass_ in user_stack:
            if type(pass_) is not str:
                raise TypeError('user stack should be a list of pass names (strings)')

        self._pass_stack = []
        for pass_ in user_stack:
            self._pass_stack.append(eval(pass_))
        return self.get_pass_stack()

    @staticmethod
    def _unknown_task_type():
        return 'unknown task type'

    def import_relation_from_csv(self, csv_file_name, relation_name=None, delimiter=","):
        if not os.path.isfile(csv_file_name):
            raise IOError("csv file does not exist")

        if os.stat(csv_file_name).st_size == 0:
            raise IOError("csv file is empty")

        # the relation_name is either an argument or the file's name
        if relation_name is None:
            relation_name = Path(csv_file_name).stem

        symbol_table = self._symbol_table
        engine = session._execution

        with open(csv_file_name) as fh:
            reader = csv.reader(fh, delimiter=delimiter)

            # read first line and go back to start of file
            relation_types = _infer_relation_type(next(reader))
            fh.seek(0)

            # first make sure the types are legal, then add them to the engine (to make sure
            #  we don't add them in case of error)
            facts = []
            for line in reader:
                _verify_relation_types(line, relation_types)
                facts.append(AddFact(relation_name, line, relation_types))

            # declare relation if it does not exist
            if not symbol_table.contains_relation(relation_name):
                engine.declare_relation(RelationDeclaration(relation_name, relation_types))
                symbol_table.add_relation_schema(relation_name, relation_types)

            for fact in facts:
                engine.add_fact(fact)

    def import_relation_from_df(self, relation_df: DataFrame, relation_name):
        symbol_table = self._symbol_table
        engine = session._execution

        data = relation_df.values.tolist()

        if not isinstance(data, list):
            raise Exception("dataframe could not be converted to list")

        if len(data) < 1:
            raise Exception("dataframe is empty")

        relation_types = _infer_relation_type(data[0])
        # first make sure the types are legal, then add them to the engine (to make sure
        #  we don't add them in case of error)
        facts = []
        for line in data:
            _verify_relation_types(line, relation_types)
            facts.append(AddFact(relation_name, line, relation_types))

        # declare relation if it does not exist
        if not symbol_table.contains_relation(relation_name):
            engine.declare_relation(RelationDeclaration(relation_name, relation_types))
            symbol_table.add_relation_schema(relation_name, relation_types)

        for fact in facts:
            engine.add_fact(fact)

    def export_relation_to_csv(self, csv_file_name, relation_name):
        # TODO
        """
        this will be implemented in a future version
        """
        raise NotImplementedError

    def export_relation_to_df(self, df, relation_name):
        # TODO
        """
        this will be implemented in a future version
        """
        raise NotImplementedError

    def query_into_csv(self, query, csv_file_name):
        # TODO: this is pseudo-code only
        #  we should have access to the session after deleting the server file
        #  (execution is imported from the engine)

        # run a query normally and get formatted results:
        free_vars, rows = execution.get_query_results(self._session.query(query))
        if not rows:
            rows = [free_vars]
        else:
            # add free_vars at start of csv
            rows.insert(0, free_vars)

        with open(csv_file_name,w) as f:
          writer = csv.writer(f)
          writer.writerows(rows)

        raise NotImplementedError

    def query_into_df(self, query) -> DataFrame:
        # TODO: this is pseudo-code only
        """
        should be similar to query_into_csv:
        free_vars, rows = execution.get_query_results(self._session.query(query))
        df = DataFrame(rows, columns=free_vars)
        """
        raise NotImplementedError


if __name__ == '__main__':
    session = Session()
    # TODO: @niv make tests
    # session.import_relation_from_csv(r"C:\Users\niviman\code\python\spanner_workbench\src\rgxlog-interpreter\tests\example_relation_two.csv",
    #                                  relation_name="rel")
    # df = DataFrame(["a", "b", "c"])
    # session.import_relation_from_df(df, "rel")
    # q = session.run_query('?rel(X)')
    # print(q)

    # TODO: @tom make tests
    # from rgxlog.engine.datatypes.primitive_types import DataTypes
    #
    #
    # def getCharAndWordNum(text):
    #     return len(text)
    #
    #     # return [(len(text), len(text.split(' '))), ]  # we should make this less ugly. perhaps we can pass flag wather the output is one tuple.
    #
    #
    # in_types = [DataTypes.string]
    #
    # out_types = [DataTypes.integer, DataTypes.integer]
    #
    # session.register(getCharAndWordNum, "GetCharAndWordNum", in_types, out_types)
    #
    # query = '''
    #         new sentence(str)
    #         sentence("One day there was a boy named Tony wandering around in the woods.")
    #         sentence("The boy was wearing his red hat.")
    #         sentence("He loved this hat so much he would protect it with his life.")
    #
    #         info(X, Y) <- GetCharAndWordNum(Z)->(X ,Y), sentence(Z)
    #         ?info(CHARS_NUM, WORDS_NUM)
    #         '''
    # print(session.run_query(query))

"""
    query = '''
    new parent(str, str)
    parent("a", "b")
    parent("d", "c")
    parent("d", "e")
    parent("b", "d")
    parent("a", "f")
    ancestor(X,Y) <- parent(X,Y)
    ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y)

    ?ancestor("b", X)
    '''
    result = session.run_query(query)
    print(result)

    query = '''
        new rel(str, str, str)
        ancestor(X,Y, Z) <- rel(X,Y, Z)
        '''
    result = session.run_query(query)
    print(result)
"""

"""
********************************************************************************************
"""

"""
    def getCharAndWordNum(text):
        return [(len(text), len(text.split(' '))),]  # we should make this less ugly. perhaps we can pass flag wather the output is one tuple.


    in_types = [DataTypes.string]

    out_types = [DataTypes.integer, DataTypes.integer]

    session.register(getCharAndWordNum, "GetCharAndWordNum", in_types, out_types)

    query = '''
            new sentence(str)
            sentence("One day there was a boy named Tony wandering around in the woods.")
            sentence("The boy was wearing his red hat.")
            sentence("He loved this hat so much he would protect it with his life.")
            
            info(X, Y) <- GetCharAndWordNum(Z)->(X ,Y), sentence(Z)
            ?info(CHARS_NUM, WORDS_NUM)
            '''
    print(session.run_query(query))

"""

"""
********************************************************************************************
"""

"""

    def length(text):
        return [len(text)]

    in_types = [DataTypes.string]

    out_types = [DataTypes.integer]

    session.register(length, "__Length", in_types, out_types)

    query = '''
        new name(str)
        name("walter")
        name("linus")
        name("rick")
        size(X) <- __Length(Y)->(X), name(Y)
        ?size(X)
        '''
    print(session.run_query(query))
"""

"""
********************************************************************************************
"""

"""
def copy(text):
    return [text]

in_types = [DataTypes.string]

out_types = [DataTypes.string]

session.register(copy, "Copy", in_types, out_types)

query = '''
    text = "ABCDEFG"
    copy(X) <- Copy(text)->(X)
    ?copy(X)
    '''
print(session.run_query(query))
"""

"""
    def split(text):
        return [str(c) for c in text]

    in_types = [DataTypes.string]

    out_types = [DataTypes.string]

    session.register(split, "Split", in_types, out_types)

    # should duplicates be deleted?
    query = '''
        text = "ABCDEFG"
        chars(X) <- Split(text)->(X)
        ?chars(X)
        '''
    print(session.run_query(query))

"""

"""
********************************************************************************************
"""

"""
import spacy
    sp = spacy.load('en_core_web_sm')

    def entities(text):
        ent = sp(text).ents
        return ((entity.text, spacy.explain(entity.label_)) for entity in ent)

    in_types = [DataTypes.string]

    def output_types(output_arity):
        return tuple([DataTypes.string] * output_arity)


    session.register(entities, "Entities", in_types, output_types, False)

    query = '''
    text = "You've been living in a dream world, Neo.\
            As in Baudrillard's vision, your whole life has been spent inside the map, not the territory.\
            This is the world as it exists today.\
            Welcome to the desert of the real."
    entities(Entity, Classification) <- Entities(text)->(Entity, Classification)
    ?entities(Entity, Classification)
    '''
    print(session.run_query(query))
"""

"""
********************************************************************************************
"""

"""
    def rgx_string(text, regex_formula):
        import re
        '''
        Args:
            text: The input text for the regex operation
            regex_formula: the formula of the regex operation

        Returns: tuples of strings that represents the results
        '''
        compiled_rgx = re.compile(regex_formula)
        num_groups = compiled_rgx.groups
        for match in re.finditer(compiled_rgx, text):
            if num_groups == 0:
                matched_strings = [match.group()]
            else:
                matched_strings = [group for group in match.groups()]
            yield matched_strings


    def rgx_string_out_types(output_arity):
        return tuple([DataTypes.string] * output_arity)


    rgx_string_in_type = [DataTypes.string, DataTypes.string]
    session.register(rgx_string, 'MYRGXString', rgx_string_in_type, rgx_string_out_types, False)
    query = '''
    new lecturer(str, str)
    lecturer("walter", "chemistry")
    lecturer("linus", "operation systems")
    lecturer("rick", "physics")

    new enrolled(str, str)
    enrolled("abigail", "chemistry")
    enrolled("abigail", "operation systems")
    enrolled("jordan", "chemistry")
    enrolled("gale", "operation systems")
    enrolled("howard", "chemistry")
    enrolled("howard", "physics")

    enrolled_in_chemistry(X) <- enrolled(X, "chemistry")
    ?enrolled_in_chemistry("jordan")
    ?enrolled_in_chemistry("gale")
    ?enrolled_in_chemistry(X)

    enrolled_in_physics_and_chemistry(X) <- enrolled(X, "chemistry"), enrolled(X, "physics")
    ?enrolled_in_physics_and_chemistry(X)

    lecturer_of(X, Z) <- lecturer(X, Y), enrolled(Z, Y)
    ?lecturer_of(X, "abigail")
    '''
    result = session.run_query(query)
    print(result)

    result2 = session.run_query('''
    gpa_str = "abigail 100 jordan 80 gale 79 howard 60"
    gpa_of_chemistry_students(Student, Grade) <- MYRGXString(gpa_str, "(\w+).*?(\d+)")->(Student, Grade), enrolled_in_chemistry(Student)
    ?gpa_of_chemistry_students(X, "100")''')
    print(result2)
"""

"""
********************************************************************************************
"""

"""
result = session.run_query('''
        new uncle(str, str)
        uncle("bob", "greg")
        ''')


print("result1:")
print(result)
result = session.run_query('''?uncle("bob",Y)''')
print("result2:")
print(result)
"""
