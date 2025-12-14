from typing import Any
from typus.core import Terminal, Sequence, Choice, NonTerminal
from typus.backends.base import GrammarVisitor


class DebugVisitor(GrammarVisitor[str]):
    """A simple visitor to verify tree structure in tests."""

    def visit_terminal(self, node: Terminal):
        return f"Term({node.value})"

    def visit_sequence(self, node: Sequence):
        inner = ",".join(item.accept(self) for item in node.items)
        return f"Seq({inner})"

    def visit_choice(self, node: Choice):
        inner = "|".join(opt.accept(self) for opt in node.options)
        return f"Choice({inner})"

    def visit_non_terminal(self, node: NonTerminal):
        return f"NonTerm({node.name})"


def test_ast_structure():
    # Construct: "Start" + ("A" | "B")
    tree = Sequence(Terminal("start"), Choice(Terminal("a"), NonTerminal("B")))

    visitor = DebugVisitor()
    result = tree.accept(visitor)

    assert result == "Seq(Term(start),Choice(Term(a)|NonTerm(B)))"
