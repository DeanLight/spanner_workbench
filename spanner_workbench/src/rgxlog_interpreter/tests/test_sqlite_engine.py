# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../../nbs/20_src.rgxlog_interpreter.tests.test_sqlite_engine.ipynb.

# %% auto 0
__all__ = ['test_add_fact_twice']

# %% ../../../../nbs/20_src.rgxlog_interpreter.tests.test_sqlite_engine.ipynb 4
import pytest

from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.datatypes.ast_node_types import RelationDeclaration, AddFact, Query
from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.datatypes.primitive_types import DataTypes
from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.engine import SqliteEngine

# %% ../../../../nbs/20_src.rgxlog_interpreter.tests.test_sqlite_engine.ipynb 5
@pytest.mark.engine
def test_add_fact_twice() -> None:
    expected_output = [(8, "hihi")]

    my_engine = SqliteEngine()
    print(my_engine)

    # add relation
    my_relation = RelationDeclaration("yoyo", [DataTypes.integer, DataTypes.string])
    my_engine.declare_relation_table(my_relation)

    # add fact
    my_fact = AddFact("yoyo", [8, "hihi"], [DataTypes.integer, DataTypes.string])
    my_engine.add_fact(my_fact)
    my_engine.add_fact(my_fact)

    my_query = Query("yoyo", ["X", "Y"], [DataTypes.free_var_name, DataTypes.free_var_name])

    my_result = my_engine.query(my_query)
    assert expected_output == my_result
