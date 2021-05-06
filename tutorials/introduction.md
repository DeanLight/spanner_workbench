# Spanner Workbench Introduction
In this tutorial you will learn the basics of spanner workbench:
* [how to install, import and use RGXLog](#use_rgxlog)
* [local and free variables](#local_and_free_vars)
* [local variable assignment](#local_var_assignment)
* [reading from a file](#read_a_file)
* [declaring a relation](#declare_relations)
* [adding facts](#facts)
* [adding rules](#rules)
* [queries](#queries)
* [using RGXLog's primitive information extractor: functional regex formulas](#RGX_ie)
* [using custom information extractors](#custom_ie)
* [additional small features](#small_features)

At the end of this tutorial there is also an [example for a small RGXLog program.](#example_program)

# Using RGXLog<a class="anchor" id="use_rgxlog"></a>

prerequisites:

* Have [Python](https://www.python.org/downloads/) version 3.8 or above installed

To install RGXLog run the following command in your terminal:

```bash
$ python3 -m pip install --upgrade --index-url https://test.pypi.org/simple/ --no-deps my-pkg-coldfear-rgxlog-interpreter
```

(This command is likely to change in the future)

* If this command doesn't work, try calling python instead of python3 (or whatever name you have for your python installation)

You can also install RGXLog in the current Jupyter kernel:


```python
import sys
current_python=sys.executable
```


```python
! {current_python} -m pip install --upgrade --index-url https://test.pypi.org/simple/ --no-deps my-pkg-coldfear-rgxlog-interpreter
```

    Looking in indexes: https://test.pypi.org/simple/
    Collecting my-pkg-coldfear-rgxlog-interpreter
    [31m  Could not find a version that satisfies the requirement my-pkg-coldfear-rgxlog-interpreter (from versions: )[0m
    [31mNo matching distribution found for my-pkg-coldfear-rgxlog-interpreter[0m


In order to use RGXLog in jupyter notebooks, you must first import it:



```python
import rgxlog
```

Importing the RGXLog library automatically loads the `%%spanner` cell magic which accepts RGXLog queries as shown below.



```python
%%spanner
new uncle(str, str)
uncle("bob", "greg")
```

    start
      relation_declaration
        relation_name	uncle
        decl_term_list
          decl_string
          decl_string
      fact
        relation_name	uncle
        fact_term_list
          string	bob
          string	greg
    


# Local and free variables<a class="anchor" id="local_and_free_vars"></a>

RGXLog distinguishes two kinds of variables.

The first kind are local variables. These are variables that store a single value (e.g. string). They work similarly to variables in python. A local variable must be defined via assignment before being used.

A local variable name must begin with a lowercase letter or with an underscore (_), and can be continued with letters, digits and underscores

Here are some examples for legal local variable names:
* `a`
* `a_name123`
* `_Some_STRING`

And here are some illegal local variable names:
* `A`
* `A_name`
* `1_a`


The second kind of variables are free variables. Free variables do not hold any value and are used to define relations inside [queries](#queries) and [rules](#rules). Free variables do not need to be declared or defined before being used.

A free variable name must begin with an uppercase letter and can be continued with letters, digits and underscores

Here are some examples for legal free variable names:
* `A`
* `A_name`

And here are some illegal free variable names:
* `a`
* `a_name`
* `_Some_STRING`
* `1A`


# Local variable assignment<a class="anchor" id="local_var_assignment"></a>
RGXLog allows you to use three types of variables: strings, integers and spans.
The assignment of a string is intuitive:


```python
%%spanner
b = "bob"
b2 = b # b2's value is "bob"
# you can write multiline strings using a line overflow escape like in python
b3 = "this is a multiline " \
"string"
b4 = "this is a multiline string" # b4 holds the same value as b3
```

    start
      assign_literal_string
        var_name	b
        string	bob
      assign_var
        var_name	b2
        var_name	b
      assign_literal_string
        var_name	b3
        string	this is a multiline string
      assign_literal_string
        var_name	b4
        string	this is a multiline string
    


The assignment of integers is also very simple:


```python
%%spanner
n = 4
n2 = n # n2 = 4
```

    start
      assign_int
        var_name	n
        integer	4
      assign_var
        var_name	n2
        var_name	n
    


 A span identifies a substring of a string by specifying its bounding indices. It is constructed from two integers.
 You can assign a span value like this:


```python
%%spanner
span1 = [3,7)
span2 = span1 # span2 value is [3,7)
```

    start
      assign_span
        var_name	span1
        span
          integer	3
          integer	7
      assign_var
        var_name	span2
        var_name	span1
    


# Reading from a file<a class="anchor" id="read_a_file"></a>
You can also perform a string assignment by reading from a file. You will need to provide a path to a file by either using a string literal or a string variable:


```python
%%spanner
a = read("path/to/file")
b = "path/to/file" 
c = read(b) # c holds the same string value as a
```

    start
      assign_string_from_file_string_param
        var_name	a
        string	path/to/file
      assign_literal_string
        var_name	b
        string	path/to/file
      assign_string_from_file_var_param
        var_name	c
        var_name	b
    


# Derclaring a relation<a class="anchor" id="declare_relations"></a>
RGXLog allows you to define and query relations.
You have to declare a relation before you can use it (unless you define it with a rule as we'll see in the "rules" chapter). Each term in a relation could be a string, an integer or a span. Here are some examples for declaring relations:


```python
%%spanner
# 'brothers' is a relation with two string terms.
new brothers(str, str)
# 'confused' is a relation with one string term.
new confused(str)
# 'animal' is a relation with one string term and one span term 
new animal(str, spn)
# 'scores' is a relation with one string term and one int term
new scores(str, int)
```

    start
      relation_declaration
        relation_name	brothers
        decl_term_list
          decl_string
          decl_string
      relation_declaration
        relation_name	confused
        decl_term_list
          decl_string
      relation_declaration
        relation_name	animal
        decl_term_list
          decl_string
          decl_span
      relation_declaration
        relation_name	scores
        decl_term_list
          decl_string
          decl_int
    


# Facts<a class="anchor" id="facts"></a>
RGXLog is an extension of Datalog, a declarative logic programming language. In Datalog you can declare "facts", essentially adding tuples to a relation. To do it you use the following syntax:

```
relation_name(term_1,term_2,...term_3)
```

where each `term` is either a constant or a local variable that is from the same variable type that was declared for `relation_name` at the same location.

For example:


```python
%%spanner
# first declare the relation that you want to use
new noun(str, spn)
# now you can add facts (tuples) to that relation
# this span indicates that a noun "Life" can be found at indexes 0 to 3
noun("Life finds a way", [0,4)) 
# another example
new sisters(str, str)
sisters("alice", "rin")
# sisters([0,4), "rin") # illegal as [0,4) is not a string
# example with int
new goals(str, int)
goals("kronovi", 10)                          
```

    start
      relation_declaration
        relation_name	noun
        decl_term_list
          decl_string
          decl_span
      fact
        relation_name	noun
        fact_term_list
          string	Life finds a way
          span
            integer	0
            integer	4
      relation_declaration
        relation_name	sisters
        decl_term_list
          decl_string
          decl_string
      fact
        relation_name	sisters
        fact_term_list
          string	alice
          string	rin
      relation_declaration
        relation_name	goals
        decl_term_list
          decl_string
          decl_int
      fact
        relation_name	goals
        fact_term_list
          string	kronovi
          integer	10
    


# Rules<a class="anchor" id="rules"></a>
Datalog allows you to deduce new tuples for a relation.
RGXLog includes this feature as well:


```python
%%spanner
new parent(str ,str)
parent("bob", "greg")
parent("greg", "alice")
# now add a rule that deduces that bob is a grandparent of alice
grandparent(X,Z) <- parent(X,Y), parent(Y,Z) # ',' is a short hand to the 'and' operator
```

    start
      relation_declaration
        relation_name	parent
        decl_term_list
          decl_string
          decl_string
      fact
        relation_name	parent
        fact_term_list
          string	bob
          string	greg
      fact
        relation_name	parent
        fact_term_list
          string	greg
          string	alice
      rule
        rule_head
          relation_name	grandparent
          free_var_name_list
            free_var_name	X
            free_var_name	Z
        rule_body
          relation
            relation_name	parent
            term_list
              free_var_name	X
              free_var_name	Y
          relation
            relation_name	parent
            term_list
              free_var_name	Y
              free_var_name	Z
    


# Queries<a class="anchor" id="queries"></a>
Querying is very simple in RGXLog. You can query by using constant values, local variables and free variables:


```python
%%spanner
# first create a relation with some facts for the example
new grandfather(str, str)
# bob and george are the grandfathers of alice and rin
grandfather("bob", "alice")
grandfather("bob", "rin")
grandfather("george", "alice")
grandfather("george", "rin")
# edward is the grandfather of john
grandfather("edward", "john")

# now for the queries
?grandfather("bob", "alice") # returns an empty tuple () as alice is bob's grandchild
?grandfather("edward", "alice") # returns nothing as alice is not edward's grandchild
?grandfather("george", X) # returns "rin" and "alice" as both rin
# and alice are george's grandchildren
?grandfather(X, "rin") # returns "bob" and "george" (rin's grandfathers)
?grandfather(X, Y) # returns all the tuples in the 'grandfather' relation

new verb(str, spn)
verb("Ron eats quickly.", [4,8))
verb("You write neatly.", [4,9))
?verb("Ron eats quickly.", X) # returns [4,8)
?verb(X,[4,9)) # returns "You write neatly."
         
new orders(str, int)
orders("pie", 4)
orders("pizza", 4)
orders("cake", 0)
?orders(X, 4) # retutns "pie" and "pizza"         
```

    start
      relation_declaration
        relation_name	grandfather
        decl_term_list
          decl_string
          decl_string
      fact
        relation_name	grandfather
        fact_term_list
          string	bob
          string	alice
      fact
        relation_name	grandfather
        fact_term_list
          string	bob
          string	rin
      fact
        relation_name	grandfather
        fact_term_list
          string	george
          string	alice
      fact
        relation_name	grandfather
        fact_term_list
          string	george
          string	rin
      fact
        relation_name	grandfather
        fact_term_list
          string	edward
          string	john
      query
        relation
          relation_name	grandfather
          term_list
            string	bob
            string	alice
      query
        relation
          relation_name	grandfather
          term_list
            string	edward
            string	alice
      query
        relation
          relation_name	grandfather
          term_list
            string	george
            free_var_name	X
      query
        relation
          relation_name	grandfather
          term_list
            free_var_name	X
            string	rin
      query
        relation
          relation_name	grandfather
          term_list
            free_var_name	X
            free_var_name	Y
      relation_declaration
        relation_name	verb
        decl_term_list
          decl_string
          decl_span
      fact
        relation_name	verb
        fact_term_list
          string	Ron eats quickly.
          span
            integer	4
            integer	8
      fact
        relation_name	verb
        fact_term_list
          string	You write neatly.
          span
            integer	4
            integer	9
      query
        relation
          relation_name	verb
          term_list
            string	Ron eats quickly.
            free_var_name	X
      query
        relation
          relation_name	verb
          term_list
            free_var_name	X
            span
              integer	4
              integer	9
      relation_declaration
        relation_name	orders
        decl_term_list
          decl_string
          decl_int
      fact
        relation_name	orders
        fact_term_list
          string	pie
          integer	4
      fact
        relation_name	orders
        fact_term_list
          string	pizza
          integer	4
      fact
        relation_name	orders
        fact_term_list
          string	cake
          integer	0
      query
        relation
          relation_name	orders
          term_list
            free_var_name	X
            integer	4
    


You may have noticed that the query

```
?grandfather("bob", "alice")
```

returns an empty tuple. This is because of the fact that bob is alice's grandfather is true,
but we did not use any free variables to construct the tuple of the query's relation, that is why we get a single empty tuple as a result

A good example for using free variables to construct a relation is the query:

```
?grandfather("george", X)
```

which finds all of george's grandchildren (`X`) and constructs a tuple for each one.

# Functional regex formulas<a class="anchor" id="RGX_ie"></a>
RGXLog supports information extraction using a regular expressions and named capture groups (for now in rule bodies only).
You will first need to define a string variable either by using a literal or a load from a file, and then you can use the following syntax in a rule body:

```
extract RGX<regex_formula>(x_1, x_2, ...,x_n) from s
```

where:
* `regex_formula` is either a string literal or a string variable that represents your regular expression.
* `x_1`, `x_2`, ... `x_n` can be any terms including capture groups that appear in the regular expressions. They're used to construct the tuples of the resulting relation. the number of terms has to be the same as the number of capture groups used in `regex_formula`.
* `s` is a string variable that the information will be extracted from.

For example:


```python
%%spanner
report = "In 2019 we earned 2000 EUR"
# you can use line overflow escape to separate your statement (like in python)
annual_earning(Year,Amount) <- extract RGX<".*(?<Year>\d\d\d\d).*(?<Amount>\d+)\sEUR"> \
(Year, Amount) from report
?annual_earning(X,Y) # returns ("2019", "2000")
```

    start
      assign_literal_string
        var_name	report
        string	In 2019 we earned 2000 EUR
      rule
        rule_head
          relation_name	annual_earning
          free_var_name_list
            free_var_name	Year
            free_var_name	Amount
        rule_body
          rgx_ie_relation
            term_list
              string	.*(?<Year>\d\d\d\d).*(?<Amount>\d+)\sEUR
            term_list
              free_var_name	Year
              free_var_name	Amount
            var_name	report
      query
        relation
          relation_name	annual_earning
          term_list
            free_var_name	X
            free_var_name	Y
    


# Custom information extractors<a class="anchor" id="custom_ie"></a>
RGXLog allows you to define and use your own information extractors. You can use them only in rule bodies (TBD). The following is the syntax for custom information extractors:

```
func<term_1,term_2,...term_n>(x_1, x_2, ..., x_n)
```

where:
* `func` is a IE function that was previously defined (TBD where it was defined)     
* `term_1`,`term_2`,...,`term_n` are the parameters for func
* `x_1`, ... `x_n` could be any type of terms, and are used to construct tuples of the resulting relation

For example:


```python
%%spanner
new grandmother(str, str)
grandmother("rin", "alice")
grandmother("denna", "joel")
sentence = "rin is happy, denna is sad."
happy_grandmother(X) <- grandmother(X,Z),get_happy<sentence>(X)
?happy_grandmother(X) # assuming get_happy returned "rin", also returns "rin"
```

    start
      relation_declaration
        relation_name	grandmother
        decl_term_list
          decl_string
          decl_string
      fact
        relation_name	grandmother
        fact_term_list
          string	rin
          string	alice
      fact
        relation_name	grandmother
        fact_term_list
          string	denna
          string	joel
      assign_literal_string
        var_name	sentence
        string	rin is happy, denna is sad.
      rule
        rule_head
          relation_name	happy_grandmother
          free_var_name_list
            free_var_name	X
        rule_body
          relation
            relation_name	grandmother
            term_list
              free_var_name	X
              free_var_name	Z
          func_ie_relation
            function_name	get_happy
            term_list
              var_name	sentence
            term_list
              free_var_name	X
      query
        relation
          relation_name	happy_grandmother
          term_list
            free_var_name	X
    


# Additional small features<a class="anchor" id="small_features"></a>
You can use line overflow escapes if you want to split your statements into multiple lines


```python
%%spanner
k \
= "some " \
"string"
```

    start
      assign_literal_string
        var_name	k
        string	some string
    


# RGXLog program example<a class="anchor" id="example_program"></a>


```python
%%spanner
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
?enrolled_in_chemistry("jordan") # returns empty tuple ()
?enrolled_in_chemistry("gale") # returns nothing
?enrolled_in_chemistry(X) # returns "abigail", "jordan" and "howard"

enrolled_in_physics_and_chemistry(X) <- enrolled(X, "chemistry"), enrolled(X, "physics")
?enrolled_in_physics_and_chemistry(X) # returns "howard"

lecturer_of(X,Z) <- lecturer(X,Y), enrolled(Z,Y)
?lecturer_of(X,"abigail") # returns "walter" and "linus"

gpa_str = "\n abigail 100\n jordan 80\n gale 79\n howard 60\n"
gpa_of_chemistry_students(Student, Grade) <- extract \
RGX<".*[\n](?<Student>[a-z]+).*(?<Grade>\d+).*[\n]">(Student, Grade) from gpa_str, \
enrolled_in_chemistry(Student)
?gpa_of_chemistry_students(X, "100") # returns "abigail"
```

    start
      relation_declaration
        relation_name	lecturer
        decl_term_list
          decl_string
          decl_string
      fact
        relation_name	lecturer
        fact_term_list
          string	walter
          string	chemistry
      fact
        relation_name	lecturer
        fact_term_list
          string	linus
          string	operation systems
      fact
        relation_name	lecturer
        fact_term_list
          string	rick
          string	physics
      relation_declaration
        relation_name	enrolled
        decl_term_list
          decl_string
          decl_string
      fact
        relation_name	enrolled
        fact_term_list
          string	abigail
          string	chemistry
      fact
        relation_name	enrolled
        fact_term_list
          string	abigail
          string	operation systems
      fact
        relation_name	enrolled
        fact_term_list
          string	jordan
          string	chemistry
      fact
        relation_name	enrolled
        fact_term_list
          string	gale
          string	operation systems
      fact
        relation_name	enrolled
        fact_term_list
          string	howard
          string	chemistry
      fact
        relation_name	enrolled
        fact_term_list
          string	howard
          string	physics
      rule
        rule_head
          relation_name	enrolled_in_chemistry
          free_var_name_list
            free_var_name	X
        rule_body
          relation
            relation_name	enrolled
            term_list
              free_var_name	X
              string	chemistry
      query
        relation
          relation_name	enrolled_in_chemistry
          term_list
            string	jordan
      query
        relation
          relation_name	enrolled_in_chemistry
          term_list
            string	gale
      query
        relation
          relation_name	enrolled_in_chemistry
          term_list
            free_var_name	X
      rule
        rule_head
          relation_name	enrolled_in_physics_and_chemistry
          free_var_name_list
            free_var_name	X
        rule_body
          relation
            relation_name	enrolled
            term_list
              free_var_name	X
              string	chemistry
          relation
            relation_name	enrolled
            term_list
              free_var_name	X
              string	physics
      query
        relation
          relation_name	enrolled_in_physics_and_chemistry
          term_list
            free_var_name	X
      rule
        rule_head
          relation_name	lecturer_of
          free_var_name_list
            free_var_name	X
            free_var_name	Z
        rule_body
          relation
            relation_name	lecturer
            term_list
              free_var_name	X
              free_var_name	Y
          relation
            relation_name	enrolled
            term_list
              free_var_name	Z
              free_var_name	Y
      query
        relation
          relation_name	lecturer_of
          term_list
            free_var_name	X
            string	abigail
      assign_literal_string
        var_name	gpa_str
        string	\n abigail 100\n jordan 80\n gale 79\n howard 60\n
      rule
        rule_head
          relation_name	gpa_of_chemistry_students
          free_var_name_list
            free_var_name	Student
            free_var_name	Grade
        rule_body
          rgx_ie_relation
            term_list
              string	.*[\n](?<Student>[a-z]+).*(?<Grade>\d+).*[\n]
            term_list
              free_var_name	Student
              free_var_name	Grade
            var_name	gpa_str
          relation
            relation_name	enrolled_in_chemistry
            term_list
              free_var_name	Student
      query
        relation
          relation_name	gpa_of_chemistry_students
          term_list
            free_var_name	X
            string	100
    
    
