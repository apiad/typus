from typing import cast
import pytest
from typus import Grammar
from typus.core import Terminal, Sequence, NonTerminal


def test_template_literal_only():
    """Test a template with no variables."""
    g = Grammar()
    # Should result in a Sequence containing one Terminal
    rule = g.template("Hello World")

    assert isinstance(rule, Sequence)
    assert len(rule.items) == 1
    assert isinstance(rule.items[0], Terminal)
    assert rule.items[0].value == "Hello World"


def test_template_explicit_kwargs():
    """Test passing rules via kwargs."""
    g = Grammar()
    g.name = "Alice"

    # Note: we pass the Rule Object, but could pass string too
    rule = g.template("Hello {user}", user=g.name)

    assert len(rule.items) == 2
    assert cast(Terminal, rule.items[0]).value == "Hello "
    assert isinstance(rule.items[1], NonTerminal)
    assert rule.items[1].name == "name"


def test_template_implicit_lookup():
    """Test finding rules directly in the grammar."""
    g = Grammar()
    g.mood = "happy"

    # Should find 'mood' in g.rules
    rule = g.template("I am {mood}")

    assert len(rule.items) == 2
    assert cast(NonTerminal, rule.items[1]).name == "mood"


def test_template_complex_mix():
    """Test multiple variables and literals."""
    g = Grammar()
    g.action = "run"
    g.object = "home"

    # "I will {action} back {object}."
    rule = g.template("I will {action} back {object}.", action=g.action)

    # Structure: "I will " + action + " back " + object + "."
    assert len(rule.items) == 5
    assert cast(Terminal, rule.items[0]).value == "I will "
    assert cast(NonTerminal, rule.items[1]).name == "action"
    assert cast(Terminal, rule.items[2]).value == " back "
    # Implicit lookup for object
    assert cast(NonTerminal, rule.items[3]).name == "object"


def test_template_gbnf_output():
    """End-to-end test compiling to GBNF."""
    g = Grammar()
    g.fn = "print"
    g.arg = g.regex("[0-9]+")

    g.root = g.template("Call: {fn}({arg})")

    output = g.compile("gbnf")

    # root ::= "Call: " fn "(" arg ")"
    assert 'root ::= "Call: " fn "(" arg ")"' in output
    assert 'fn ::= "print"' in output
