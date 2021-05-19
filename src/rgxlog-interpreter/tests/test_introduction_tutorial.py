from rgxlog.engine.datatypes.primitive_types import DataTypes
from tests.utils import run_test


def test_introduction():
    expected_result_intro = """printing results for query 'uncle(X, Y)':
          X  |  Y
        -----+------
         bob | greg
        """

    query = """
    new uncle(str, str)
    uncle("bob", "greg")
    ?uncle(X,Y)
    """

    run_test(query, expected_result_intro)


def test_basic_queries():
    expected_result = """printing results for query 'enrolled_in_chemistry("jordan")':
        [()]
        
        printing results for query 'enrolled_in_chemistry("gale")':
        []
        
        printing results for query 'enrolled_in_chemistry(X)':
            X
        ---------
         howard
         jordan
         abigail
        
        printing results for query 'enrolled_in_physics_and_chemistry(X)':
           X
        --------
         howard
        
        printing results for query 'lecturer_of(X, "abigail")':
           X
        --------
         linus
         walter
        """

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

    session = run_test(query, expected_result)
    expected_result2 = """printing results for query 'gpa_of_chemistry_students(X, "100")':
            X
        ---------
         abigail
        """

    query2 = (r"""gpa_str = "abigail 100 jordan 80 gale 79 howard 60"
            gpa_of_chemistry_students(Student, Grade) <- py_rgx_string(gpa_str, "(\w+).*?(\d+)")"""
              r"""->(Student, Grade), enrolled_in_chemistry(Student)
            ?gpa_of_chemistry_students(X, "100")""")

    run_test(query2, expected_result2, session=session)


def test_recursive():
    expected_result = """printing results for query 'ancestor("Liam", X)':
            X
        ----------
          Mason
          Oliver
         Benjamin
           Noah
        
        printing results for query 'ancestor(X, "Mason")':
            X
        ----------
           Noah
           Liam
         Benjamin
        
        printing results for query 'ancestor("Mason", X)':
        []
        """

    query = '''
        new parent(str, str)
        parent("Liam", "Noah")
        parent("Noah", "Oliver")
        parent("James", "Lucas")
        parent("Noah", "Benjamin")
        parent("Benjamin", "Mason")
        ancestor(X,Y) <- parent(X,Y)
        ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y)
        
        ?ancestor("Liam", X)
        ?ancestor(X, "Mason")
        ?ancestor("Mason", X)
        '''

    run_test(query, expected_result)


def test_json_path():
    expected_result = """printing results for query 'simple_1(X)':
           X
        -----
           2
           1
        
        printing results for query 'simple_2(X)':
             X
        ------------
         number two
         number one
        
        printing results for query 'advanced(X)':
                         X
        -----------------------------------
         {'foo': [{'baz': 1}, {'baz': 2}]}
                         1
        """

    query = """
            jsonpath_simple_1 = "foo[*].baz"
            json_ds_simple_1  = "{'foo': [{'baz': 1}, {'baz': 2}]}"
            simple_1(X) <- JsonPath(json_ds_simple_1, jsonpath_simple_1) -> (X)
            ?simple_1(X)

            jsonpath_simple_2 = "a.*.b.`parent`.c"
            json_ds_simple_2 = "{'a': {'x': {'b': 1, 'c': 'number one'}, 'y': {'b': 2, 'c': 'number two'}}}"

            simple_2(X) <- JsonPath(json_ds_simple_2, jsonpath_simple_2) -> (X)
            ?simple_2(X)

            json_ds_advanced  = "{'foo': [{'baz': 1}, {'baz': {'foo': [{'baz': 1}, {'baz': 2}]}}]}"
            advanced(X) <- JsonPath(json_ds_advanced, jsonpath_simple_1) -> (X)
            ?advanced(X)
        """

    run_test(query, expected_result)


def test_remove_rule():
    expected_result = """printing results for query 'ancestor(X, Y)':
          X  |  Y
        -----+-----
         Tom | Avi
        
        printing results for query 'tmp(X, Y)':
            X     |    Y
        ----------+----------
         Benjamin |  Mason
           Noah   | Benjamin
          James   |  Lucas
           Noah   |  Oliver
           Liam   |   Noah
           Tom    |   Avi
        """

    query = """
        new parent(str, str)
        new grandparent(str, str)
        parent("Liam", "Noah")
        parent("Noah", "Oliver")
        parent("James", "Lucas")
        parent("Noah", "Benjamin")
        parent("Benjamin", "Mason")
        grandparent("Tom", "Avi")
        ancestor(X,Y) <- parent(X,Y)
        ancestor(X,Y) <- grandparent(X,Y)
        ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y)

        tmp(X, Y) <- ancestor(X,Y)
        tmp(X, Y) <- parent(X,Y)
        """

    session = run_test(query)

    session.remove_rule("ancestor(X,Y) <- parent(X,Y)")
    query = """
            ?ancestor(X, Y)
            ?tmp(X, Y)
          """

    run_test(query, expected_result, session=session)


def test_string_len():
    def length(string):
        # here we append the input to the output inside the ie function!
        yield len(string), string

    Length = dict(ie_function=length,
                  ie_function_name='Length',
                  in_rel=[DataTypes.string],
                  out_rel=[DataTypes.integer, DataTypes.string],
                  )
    expected_result = """printing results for query 'string_length(Str, Len)':
          Str  |   Len
        -------+-------
           a   |     1
          ab   |     2
          abc  |     3
         abcd  |     4
        """
    query = """new string(str)
            string("a")
            string("ab")
            string("abc")
            string("abcd")
            
            string_length(Str, Len) <- string(Tmp), Length(Tmp) -> (Len, Str)
            ?string_length(Str, Len)
            """

    run_test(query, expected_result, [Length])


def test_neq():
    def neq(x, y):
        if x == y:
            # return false
            yield tuple()
        else:
            # return true
            yield x, y

    in_out_types = [DataTypes.string, DataTypes.string]
    NEQ = dict(ie_function=neq,
               ie_function_name='NEQ',
               in_rel=in_out_types,
               out_rel=in_out_types,
               )
    expected_result = """printing results for query 'unique_pair(X, Y)':
          X  |  Y
        -----+-----
         Dan | Tom
         Cat | Dog
         123 | 321
        """

    query = """new pair(str, str)
            pair("Dan", "Tom")
            pair("Cat", "Dog")
            pair("Apple", "Apple")
            pair("Cow", "Cow")
            pair("123", "321")
            
            unique_pair(X, Y) <- pair(First, Second), NEQ(First, Second) -> (X, Y)
            ?unique_pair(X, Y)
            """
    run_test(query, expected_result, [NEQ])
