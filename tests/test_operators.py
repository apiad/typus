from typus import Grammar
from typus.core import Terminal, Sequence, Choice, NonTerminal


def test_sequence_flattening():
    # Test explicitly: Sequence(Sequence(A, B), C)
    t1, t2, t3 = Terminal("A"), Terminal("B"), Terminal("C")

    seq = Sequence(Sequence(t1, t2), t3)

    # Should be [A, B, C], NOT [[A, B], C]
    assert len(seq.items) == 3
    assert seq.items == [t1, t2, t3]


def test_sequence_operator_chain():
    # Test A + B + C
    t1, t2, t3 = Terminal("A"), Terminal("B"), Terminal("C")

    # (A + B) -> Seq(A,B)
    # Seq(A,B) + C -> Seq(A,B,C)
    seq = t1 + t2 + t3

    assert isinstance(seq, Sequence)
    assert len(seq.items) == 3
    assert seq.items == [t1, t2, t3]


def test_choice_flattening():
    # Test A | (B | C)
    t1, t2, t3 = Terminal("A"), Terminal("B"), Terminal("C")

    choice = t1 | (t2 | t3)

    assert isinstance(choice, Choice)
    assert len(choice.options) == 3
    assert choice.options == [t1, t2, t3]


def test_mixed_types_and_promotion():
    # Test "User: " + g.name
    g = Grammar()

    # String on left (requires __radd__)
    expr = "User: " + g.name

    assert isinstance(expr, Sequence)
    assert len(expr.items) == 2
    assert isinstance(expr.items[0], Terminal)
    assert expr.items[0].value == "User: "
    assert isinstance(expr.items[1], NonTerminal)


def test_operator_precedence():
    # A + B | C -> (A + B) | C
    a, b, c = Terminal("A"), Terminal("B"), Terminal("C")

    expr = a + b | c

    assert isinstance(expr, Choice)
    assert len(expr.options) == 2
    assert isinstance(expr.options[0], Sequence)  # (A + B)
    assert expr.options[1] == c
