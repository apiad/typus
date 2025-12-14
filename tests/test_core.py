from typus.core import Terminal, Sequence, Choice
from typus.backends.base import GrammarVisitor


class DebugVisitor(GrammarVisitor):
    """A simple visitor to verify tree structure in tests."""

    def visit_terminal(self, node):
        return f"Term({node.value})"

    def visit_sequence(self, node):
        inner = ",".join(item.accept(self) for item in node.items)
        return f"Seq({inner})"

    def visit_choice(self, node):
        inner = "|".join(opt.accept(self) for opt in node.options)
        return f"Choice({inner})"


def test_ast_structure():
    # Construct: "Start" + ("A" | "B")
    tree = Sequence(Terminal("Start"), Choice(Terminal("A"), Terminal("B")))

    visitor = DebugVisitor()
    result = tree.accept(visitor)

    assert result == "Seq(Term(Start),Choice(Term(A)|Term(B)))"
