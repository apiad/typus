from typing import List
from typus.domain.reflector import Reflector

# --- Domain Definition ---
class DataFrame:
    def __init__(self, path: str): ...

    def filter(self, q: str) -> "DataFrame": ...
    def count(self) -> int: ...

def load_csv(path: str) -> DataFrame: ...

# --- Test ---
def test_reflection_pandas_graph():
    reflector = Reflector()

    # We pass explicit entrypoints: The class and the helper function
    nodes = reflector.reflect(DataFrame, load_csv)

    # Helper to find a node by name
    def get(name):
        return next(n for n in nodes if n.name == name)

    df_node = get("DataFrame")
    int_node = get("int")

    # --- Check DataFrame Producers ---
    # Should have 3 ways to be created:
    # 1. __init__ (Constructor)
    # 2. filter (Method on itself)
    # 3. load_csv (Function)

    producer_names = {t.name for t in df_node.producers}
    assert "__init__" in producer_names
    assert "filter" in producer_names
    assert "load_csv" in producer_names

    # --- Check Int Producers ---
    # Should have 1 way:
    # 1. DataFrame.count

    int_producers = {t.name for t in int_node.producers}
    assert "count" in int_producers

    # Verify metadata on 'filter'
    filter_trans = next(t for t in df_node.producers if t.name == "filter")
    assert filter_trans.is_method
    assert filter_trans.origin_type == df_node # It comes from DataFrame
    assert "q" in filter_trans.params # It takes 'q'
