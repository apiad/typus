import pytest
from typus.domain.generator import DomainGenerator
from typus.languages.python import Python


# --- The Domain Definition ---
class DataFrame:
    def __init__(self, path: str): ...

    # Fluent Methods (Return DataFrame -> Keep chaining)
    def select(self, col: str) -> "DataFrame": ...
    def filter(self, q: str, limit: int) -> "DataFrame": ...

    # Exit Methods (Return int -> Stop chaining or switch type)
    def count(self) -> int: ...


def read_csv(path: str) -> DataFrame: ...


# --- The Tests ---


def test_parsing_valid_python_code():
    """
    Verifies that the generated grammar accepts valid Python code
    matching the domain structure.
    """
    # 1. Check for Lark (Dev dependency)
    try:
        from lark import Lark
    except ImportError:
        pytest.fail("Lark not installed. Run 'uv add --dev lark'")

    # 2. Build Grammar
    # We define 'DataFrame' and 'read_csv' as the valid starting points.
    gen = DomainGenerator(Python())
    grammar = gen.build(DataFrame, read_csv)

    # 3. Compile to Lark
    lark_source = grammar.compile("lark")

    print(lark_source)

    parser = Lark(lark_source, parser="lalr")

    # Case A: Simple Function Call (Head)
    # read_csv(path="data.csv")
    tree_a = parser.parse('read_csv(path="data.csv")')
    assert tree_a.data == "start"

    # Case B: Constructor + Fluent Chain
    # DataFrame(path="data").select(col="age")
    tree_b = parser.parse('DataFrame(path="data").select(col="age")')
    assert tree_b.data == "start"

    # Case C: Pipeline Transition (Exit)
    # The root rule allows us to 'walk away' from the starting type.
    # Start with DataFrame -> transition to int via .count()
    code_c = 'DataFrame(path="d").filter(q="a", limit=10).count()'
    tree_c = parser.parse(code_c)
    assert tree_c.data == "start"


def test_parsing_nested_expressions():
    """
    Verifies Type Composition: Using an expression of Type B
    as an argument for a function expecting Type B.
    """
    try:
        from lark import Lark
    except ImportError:
        return

    gen = DomainGenerator(Python())
    grammar = gen.build(DataFrame)
    parser = Lark(grammar.compile("lark"))

    # The 'limit' argument in 'filter' expects an 'int'.
    # 1. Simple Literal: limit=5
    parser.parse('DataFrame(path="a").filter(q="b", limit=5)')

    # 2. Complex Expression: limit=DataFrame(...).count()
    # Since 'df.count()' returns an int, it must be valid here.
    code_nested = 'DataFrame(path="a").filter(q="b", limit=DataFrame(path="b").count())'
    tree = parser.parse(code_nested)
    assert tree.data == "start"


def test_parsing_invalid_python_code():
    """
    Verifies that the grammar REJECTS code that violates the type system
    or the domain API.
    """
    try:
        from lark import Lark, UnexpectedToken
    except ImportError:
        return

    gen = DomainGenerator(Python())
    grammar = gen.build(DataFrame)
    parser = Lark(grammar.compile("lark"))

    # 1. Invalid Method Name (Hallucination)
    with pytest.raises(UnexpectedToken):
        parser.parse('DataFrame(path="a").halucinate()')

    # 2. Invalid Argument Name
    with pytest.raises(UnexpectedToken):
        parser.parse('DataFrame(wrong_arg="a")')

    # 3. Invalid Type (Type Error)
    # 'path' expects str, but we give it an int literal
    with pytest.raises(UnexpectedToken):
        parser.parse("DataFrame(path=123)")

    # 4. Invalid Type in Nested Expression
    # 'limit' expects int, but we give it a DataFrame expression (that doesn't exit to int)
    # i.e. we pass a DataFrame object where an int is needed.
    with pytest.raises(UnexpectedToken):
        parser.parse('DataFrame(path="a").filter(q="b", limit=DataFrame(path="b"))')
