from typing import cast
import pytest
from typus import Grammar
from typus.core import Terminal

# Import Lark inside test (dev dependency only)
try:
    from lark import Lark, Token
except ImportError:
    pytest.fail("Lark not installed. Run 'uv add --dev lark'")


def test_lark_basic_structure():
    """Test generating a simple sequence."""
    g = Grammar()
    g.word = g.regex(r"\w+")
    g.root = "Hello " + g.word

    # 1. Compile
    lark_grammar = g.compile("lark")
    print(f"\nGrammar:\n{lark_grammar}")

    # 2. Verify Syntax (by initializing parser)
    parser = Lark(lark_grammar)

    # 3. Verify Parsing
    tree = parser.parse("Hello World")

    # Structure check: start -> root definition
    # The tree should contain a child matching 'word' rule
    assert tree.data == "start"
    # Depending on how Lark parses inline rules, we look for the regex content
    # Since 'word' is a named rule, it should appear in the tree
    # Note: Lark handles anonymous definitions vs named rules differently.
    # Our compiler maps 'g.word' -> 'word: ...', so it should be a node.

    # Traverse children to find 'word'
    def found(tree):
        if cast(Token, tree).data == "word":
            return True

        for child in tree.children:
            if found(child):
                return True

        return False

    assert found(tree), "The parse tree should contain the 'word' rule node"


def test_lark_choice_precedence():
    """Test that choices inside sequences are parenthesized correctly."""
    g = Grammar()
    # a (b | c)
    g.root = "a " + (Terminal("b") | "c")

    lark_grammar = g.compile("lark")
    # Expected: start: "a " ("b" | "c")
    assert '("b" | "c")' in lark_grammar

    parser = Lark(lark_grammar)
    parser.parse("a b")
    parser.parse("a c")


def test_lark_recursion():
    """Test standard list recursion."""
    g = Grammar()
    g.num = g.regex(r"\d")
    # list: num | num "," list
    g.list = g.num | (g.num + "," + g.list)
    g.root = g.list

    lark_grammar = g.compile("lark")
    parser = Lark(lark_grammar)

    tree = parser.parse("1,2,3")
    assert tree.data == "start"


def test_lark_template_integration():
    """Test that Templates compile to valid Lark."""
    g = Grammar()
    g.key = g.regex(r"\w+")
    g.val = g.regex(r"\d+")

    # JSON-like property: "key": val
    g.root = g.template('"{k}": {v}', k=g.key, v=g.val)

    lark_grammar = g.compile("lark")
    parser = Lark(lark_grammar)

    tree = parser.parse('"age": 42')
    assert tree.data == "start"
