import pytest
from typus.domain.core import Domain, VoidType

# --- Domain Fixtures ---


class DataFrame:
    def __init__(self, path: str): ...
    def filter(self, q: str) -> "DataFrame": ...
    def count(self) -> int: ...


def read_csv(path: str) -> DataFrame: ...


class Other:
    def do_nothing(self) -> None: ...


# --- Tests ---


def test_graph_registration():
    dom = Domain()

    # 1. Register a Function
    dom.register(read_csv)

    # Check Void -> DataFrame edge exists
    entrypoints = dom.get_entrypoints()
    assert len(entrypoints) == 1
    assert entrypoints[0].name == "read_csv"
    assert entrypoints[0].target.py_type == DataFrame

    # 2. Register a Class (Recursive)
    # This should find __init__, filter, and count
    dom.register(DataFrame)

    df_node = dom.get_node(DataFrame)
    assert df_node is not None

    # Check Outgoing (Methods)
    method_names = {e.name for e in df_node.outgoing}
    assert "filter" in method_names
    assert "count" in method_names

    # Check Incoming (Producers)
    # Should be: read_csv (from Void), __init__ (from Void), filter (from DF)
    producer_names = {e.name for e in df_node.incoming}
    assert "read_csv" in producer_names
    assert "DataFrame" in producer_names  # Constructor
    assert "filter" in producer_names


def test_parameter_recursion():
    dom = Domain()

    # Registration of DataFrame should implicitly scan 'int' and 'str'
    # (though they are primitives and stop recursion)
    dom.register(DataFrame)

    assert int in dom.nodes
    assert str in dom.nodes

    # 'count' produces int
    int_node = dom.get_node(int)
    assert any(e.name == "count" for e in int_node.incoming)


def test_query_api_paths():
    dom = Domain()
    dom.register(DataFrame)
    dom.register(read_csv)

    # 1. Path from Void to DataFrame (Creation)
    paths_to_df = dom.get_paths(VoidType, DataFrame, max_depth=2)
    # Should find: [read_csv], [DataFrame]
    path_names = [p[0].name for p in paths_to_df if len(p) == 1]
    assert "read_csv" in path_names
    assert "DataFrame" in path_names

    # 2. Path from DataFrame to int (Computation)
    paths_df_to_int = dom.get_paths(DataFrame, int, max_depth=2)
    # Should find: [count], [filter, count]

    # Direct: .count()
    assert any(len(p) == 1 and p[0].name == "count" for p in paths_df_to_int)

    # Chained: .filter().count()
    chained = [p for p in paths_df_to_int if len(p) == 2]
    assert any(p[0].name == "filter" and p[1].name == "count" for p in chained)


def test_query_api_connectivity():
    dom = Domain()
    dom.register(DataFrame)

    # Filter returns DataFrame -> DataFrame (Loop)
    paths = dom.get_paths(DataFrame, DataFrame, max_depth=1)
    assert any(p[0].name == "filter" for p in paths)

    # Count returns Int. Path DF -> Int exists. Path Int -> DF does NOT exist.
    assert dom.get_paths(DataFrame, int)
    assert not dom.get_paths(int, DataFrame)
