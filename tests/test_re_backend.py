import pytest
import re
from typus import Grammar
from typus.core import Terminal


def test_regex_primitives():
    """Test that basic terminals and regex nodes compile correctly."""
    g = Grammar()
    # A mix of literal text (needs escaping) and regex (raw)
    g.root = g.regex(r"\d+") + Terminal(".") + "txt"

    pattern = g.compile("regex")

    # Should match "123.txt"
    assert re.fullmatch(pattern, "123.txt")

    # Should fail if dot matches anything else (proving it was escaped)
    assert not re.fullmatch(pattern, "123atxt")


def test_regex_choice_and_sequence():
    """Test standard operators + and |."""
    g = Grammar()
    # (a | b) + c
    g.root = (Terminal("a") | "b") + "c"

    pattern = g.compile("regex")

    assert re.fullmatch(pattern, "ac")
    assert re.fullmatch(pattern, "bc")

    # Should not match just "a" or "b" or "c"
    assert not re.fullmatch(pattern, "ab")
    assert not re.fullmatch(pattern, "c")


def test_regex_epsilon_maybe():
    """Test that maybe() generates a valid optional group."""
    g = Grammar()
    # "a" + maybe("b")
    g.root = "a" + g.maybe("b")

    pattern = g.compile("regex")

    assert re.fullmatch(pattern, "a")
    assert re.fullmatch(pattern, "ab")
    assert not re.fullmatch(pattern, "b")


def test_regex_recursion_default_error():
    """Ensure recursion raises ValueError by default."""
    g = Grammar()
    g.rule = "a" | ("b" + g.rule)
    g.root = g.rule

    # Without max_depth, this is infinite
    with pytest.raises(ValueError, match="Recursion detected"):
        g.compile("regex")


def test_regex_bounded_recursion():
    """
    Test the unrolling logic.
    Grammar: S ::= "a" | "b" S
    Logically matches: b*a
    """
    g = Grammar()
    g.root = "a" | ("b" + g.root)

    # Case 1: max_depth=1
    # We enter S once. Recursion is blocked immediately (returns "").
    # Logic: "a" | "b" + "" -> Matches "a" or "b"
    pattern_1 = g.compile("regex", max_depth=0)
    print(pattern_1)

    assert re.fullmatch(pattern_1, "a")
    assert re.fullmatch(pattern_1, "b")  # Artifact of pruning
    assert not re.fullmatch(pattern_1, "ba")  # Requires depth 2

    # Case 2: max_depth=2
    # We enter S, then recurse S once.
    # Logic: "a" | "b" ("a" | "b") -> Matches "a", "ba", "bb"
    pattern_2 = g.compile("regex", max_depth=1)
    assert re.fullmatch(pattern_2, "ba")
    assert re.fullmatch(pattern_2, "bb")
    assert not re.fullmatch(pattern_2, "bba")  # Requires depth 3

    # Case 3: max_depth=3
    # Matches "a", "ba", "bba", "bbb" (and artifacts like "bb")
    pattern_3 = g.compile("regex", max_depth=3)
    assert re.fullmatch(pattern_3, "bba")


def test_regex_list_unrolling():
    """Test a common use case: A comma-separated list."""
    g = Grammar()
    g.item = g.regex(r"\d")
    # List ::= item | item ", " List
    g.list = g.item | (g.item + ", " + g.list)
    g.root = g.list

    # Allow lists of up to 3 items
    # Depth 1: item (1)
    # Depth 2: item, item (2)
    # Depth 3: item, item, item (3)
    pattern = g.compile("regex", max_depth=3)

    assert re.fullmatch(pattern, "1")
    assert re.fullmatch(pattern, "1, 2")
    assert re.fullmatch(pattern, "1, 2, 3")

    # Should fail for 4 items
    assert not re.fullmatch(pattern, "1, 2, 3, 4")
