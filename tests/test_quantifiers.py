from typing import cast
from typus import Grammar
from typus.core import Terminal, Sequence, Choice, Epsilon, NonTerminal


def test_maybe_structure():
    g = Grammar()
    # root ::= "A" | ""
    g.root = g.maybe("A")

    assert isinstance(g.root, Choice)
    assert len(g.root.options) == 2
    assert isinstance(g.root.options[0], Terminal)
    assert isinstance(g.root.options[1], Epsilon)


def test_some_recursion():
    g = Grammar()
    # root ::= some("A")
    # Should create: _some_1 ::= "A" | "A" _some_1
    g.root = g.some("A")

    assert isinstance(g.root, NonTerminal)
    generated_name = g.root.name
    assert generated_name in g.rules

    rule = g.rules[generated_name]
    assert isinstance(rule, Choice)

    # Check recursion structure: A | A + Ref
    recurse = rule.options[1]
    assert isinstance(recurse, Sequence)
    assert cast(NonTerminal, recurse.items[1]).name == generated_name


def test_any_structure():
    g = Grammar()
    # root ::= any("A", sep=",")
    # Should be maybe(some("A", sep=","))
    g.root = g.any("A", sep=",")

    # Outer layer is maybe (Choice)
    assert isinstance(g.root, Choice)
    assert isinstance(g.root.options[1], Epsilon)

    # Inner layer is some (NonTerminal ref)
    ref = g.root.options[0]
    assert isinstance(ref, NonTerminal)


def test_gbnf_output_quantifiers():
    g = Grammar()
    # "A" zero or more times separated by comma
    g.root = g.any("A", sep=",")

    output = g.compile("gbnf")

    # Check for empty string (epsilon)
    assert '""' in output
    # Check for recursion
    assert '::= ( "A" | "A" ","' in output
