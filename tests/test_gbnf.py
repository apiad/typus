from typus import Grammar
from typus.core import Terminal, Sequence, Choice


def test_simple_gbnf():
    g = Grammar()
    g.root = Terminal("Hello")

    output = g.compile("gbnf")
    assert output.strip() == 'root ::= "Hello"'


def test_complex_rule():
    # root ::= "User" ( "Alice" | "Bob" )
    g = Grammar()
    g.names = Choice(Terminal("Alice"), Terminal("Bob"))
    g.root = Sequence(Terminal("User "), g.names)

    output = g.compile("gbnf")

    # We expect:
    # root ::= "User " names
    # names ::= ( "Alice" | "Bob" )
    assert 'root ::= "User " names' in output
    assert 'names ::= ( "Alice" | "Bob" )' in output


def test_recursion_gbnf():
    # list ::= "1" | "1" "," list
    g = Grammar()
    item = Terminal("1")
    g.list = Choice(item, Sequence(item, Terminal(","), g.list))

    output = g.compile("gbnf")
    assert 'list ::= ( "1" | "1" "," list )' in output
