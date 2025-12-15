from typus import Grammar
from typus.core import Terminal


def test_regex_builder():
    g = Grammar()
    g.root = g.regex(r"[0-9]+")

    assert isinstance(g.root, Terminal)
    assert g.root.value == r"[0-9]+"
    assert g.root.is_regex is True


def test_regex_gbnf_compilation():
    g = Grammar()
    # Define a simple grammar: ID-1234
    # "ID-" is a string literal (quoted), [0-9]+ is a regex (unquoted)
    g.root = "ID-" + g.regex(r"[0-9]+")

    output = g.compile("gbnf")

    # Expected: root ::= "ID-" [0-9]+
    assert 'root ::= "ID-" [0-9]+' in output


def test_regex_in_quantifiers():
    g = Grammar()
    # List of digits: [0-9] ( , [0-9] )*
    g.root = g.some(g.regex("[0-9]"), sep=",")

    output = g.compile("gbnf")

    # The separator "," should be quoted
    # The regex [0-9] should NOT be quoted
    assert '","' in output
    assert "[0-9]" in output
    assert '"[0-9]"' not in output
