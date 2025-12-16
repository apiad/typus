from typing import List
from typus.domain.generator import DomainGenerator
from typus.languages.python import Python


# --- The "Pandas" Domain ---
class DataFrame:
    def __init__(self, path: str): ...

    # Fluent Methods
    def select(self, col: str) -> "DataFrame": ...
    def filter(self, q: str) -> "DataFrame": ...

    # Terminal Methods (Return int)
    def count(self) -> int: ...


def read_csv(path: str) -> DataFrame: ...


# --- The Test ---
def test_python_pandas_generation():
    # 1. Build the Grammar
    gen = DomainGenerator(Python())
    g = gen.build(DataFrame, read_csv)

    # ...
    # 2. Compile to GBNF
    gbnf = g.compile("gbnf")

    print("\n" + gbnf)

    # --- Assertions ---

    # 1. Check for the Rule Definition
    assert "DataFrame ::=" in gbnf

    # 2. Check for the Constructors (Order independent)
    # We just ensure ' "DataFrame(" ' appears somewhere in the output
    assert '"DataFrame("' in gbnf
    assert '"read_csv("' in gbnf

    # 3. Check for Chains
    assert '".select("' in gbnf
    assert '".filter("' in gbnf

    # 4. Check integer integration
    assert '".count("' in gbnf
