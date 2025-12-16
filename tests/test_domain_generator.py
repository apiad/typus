from typus.languages.protocol import Language, RenderContext
from typus.domain.generator import DomainGenerator
from typus.core import Terminal


class MockLang(Language):
    """A debug language that outputs [HEAD:name] and [TAIL:name]."""

    def render_primitive(self, ctx, py_type):
        return Terminal(f"<{py_type.__name__}>")

    def render_head(self, ctx, name, args, origin=None):
        # Format: [HEAD:name(arg1, arg2)]
        arg_str = ", ".join(args.keys())  # Just verify we saw args
        return Terminal(f"[HEAD:{name}({arg_str})]")

    def render_tail(self, ctx, name, args):
        arg_str = ", ".join(args.keys())
        return Terminal(f"[TAIL:{name}({arg_str})]")


# --- Domain ---
class DF:
    def __init__(self, path: str): ...
    def filter(self, q: str) -> "DF": ...
    def count(self) -> int: ...


def load() -> DF: ...


# --- Test ---
def test_generator_structure():
    gen = DomainGenerator(MockLang())
    g = gen.build(DF, load)

    # Compile to string (using GBNF backend internally) to check structure
    output = g.compile("gbnf")

    print(output)

    # 1. Check Heads (DF rule)
    # Should contain DF and load
    assert "[HEAD:DF(path)]" in output
    assert "[HEAD:load()]" in output

    # 2. Check Tails (DF_Chain rule)
    # Should contain filter
    assert "[TAIL:filter(q)]" in output

    # 3. Check Int Rule
    # Should contain count (which is a HEAD for int, derived from DF)
    # It renders as [HEAD:count()]
    assert "[HEAD:count()]" in output

    # 4. Check Recursion/Structure
    # DF ::= (Heads...) (DF_Chain)*
    # The generated GBNF usually looks like:
    # DF ::= ( ... ) | ( ... ) DF_Chain_rep
    assert "DF-Chain" in output
