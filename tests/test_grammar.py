from typing import cast
import pytest
from typus import Grammar
from typus.core import Terminal, Sequence, Choice, NonTerminal


def test_grammar_definition():
    g = Grammar()

    # Define a rule: name = "Alice" | "Bob"
    g.name = Choice(Terminal("Alice"), Terminal("Bob"))

    # Check it was stored
    assert "name" in g.rules
    assert isinstance(g.rules["name"], Choice)


def test_lazy_references():
    g = Grammar()

    # Use g.expr BEFORE defining it
    # This should return a NonTerminal("expr")
    ref = g.expr

    assert isinstance(ref, NonTerminal)
    assert ref.name == "expr"


def test_recursion_structure():
    """
    Test: list ::= item | item "," list
    """
    g = Grammar()
    g.item = Terminal("1")

    # Here we use g.list inside the definition of g.list
    g.list = Choice(g.item, Sequence(g.item, Terminal(","), g.list))

    assert "list" in g.rules
    # The structure should contain a NonTerminal pointing to "list"
    choice: Choice = cast(Choice, g.rules["list"])
    sequence: Sequence = cast(Sequence, choice.options[1])
    last_item = sequence.items[2]

    assert isinstance(last_item, NonTerminal)
    assert last_item.name == "list"
