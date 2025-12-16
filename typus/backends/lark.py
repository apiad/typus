from typus.core import Symbol, Terminal, NonTerminal, Sequence, Choice, Epsilon
from typus.backends.base import Compiler

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typus.grammar import Grammar


class LarkCompiler(Compiler[str]):
    """
    Compiles a Typus grammar into a Lark grammar string.
    Does not require 'lark' to be installed.
    """

    def compile(self, grammar: "Grammar") -> str:
        self.grammar = grammar

        lines = []

        # 1. Define 'start' rule (Lark entrypoint)

        lines.append(f"start: root")

        # 2. Other Rules
        for name, symbol in grammar.rules.items():
            definition = symbol.accept(self)
            # If a rule compiles to nothing (pure epsilon), Lark needs explicit empty
            if not definition:
                definition = '""'
            lines.append(f"{name.lower()}: {definition}")

        return "\n".join(lines)

    def visit_terminal(self, node: Terminal) -> str:
        # If it's a literal empty string, treat it effectively as Epsilon for Lark
        if not node.value:
            raise ValueError("Empty terminals not allowed")

        if node.is_regex:
            clean_val = node.value.replace("/", r"\/")
            return f"/{clean_val}/"

        clean_val = node.value.replace('"', r"\"")
        return f'"{clean_val}"'

    def visit_sequence(self, node: Sequence) -> str:
        # Filter out empty strings (Epsilons)
        parts = [child.accept(self) for child in node.items]
        # Remove empty strings resulting from Epsilon or Terminal("")
        clean_parts = [p for p in parts if p]

        if not clean_parts:
            raise Exception
            return ""  # Sequence of nothings is nothing

        # Join with space
        # Wrap Choices in parens if they are inside a sequence
        final_parts = []
        for child, part in zip(node.items, parts):
            if not part:
                continue

            # If child was a Choice and rendered to something containing pipes, wrap it
            # Simple heuristic: if unquoted '|' in output and not wrapped
            if isinstance(child, Choice) and len(child.options) > 1:
                # Check if the child choice collapsed to a single option (e.g. A?)
                # If it generated (A | B), we need parens: (A | B) C
                # If it generated A?, we don't strictly need extra parens: A? C
                # Safer to always wrap if it was a Choice node
                if "|" in part:
                    part = f"({part})"

            final_parts.append(part)

        return " ".join(final_parts)

    def visit_choice(self, node: Choice) -> str:
        # 1. Separate actual options from Epsilons
        # We consider Epsilon node OR empty string compilation as "Empty"
        compiled_opts = []
        has_epsilon = False

        for child in node.options:
            if isinstance(child, Epsilon):
                has_epsilon = True
            else:
                res = child.accept(self)
                if not res:  # It compiled to empty (e.g. Terminal(""))
                    has_epsilon = True
                else:
                    compiled_opts.append(res)

        # 2. Construct the core choice string "A | B"
        if not compiled_opts:
            raise Exception
            return ""  # All options were epsilon -> Empty

        core = " | ".join(compiled_opts)

        # 3. Handle Epsilon -> Convert to Optional (?)
        if has_epsilon:
            if len(compiled_opts) == 1:
                # Choice(A, Epsilon) -> A?
                # Check if A is already parenthesized or atomic
                # (Simple heuristic: wrap if it has spaces)
                if " " in core and not (core.startswith("(") and core.endswith(")")):
                    return f"({core})?"
                return f"{core}?"
            else:
                # Choice(A, B, Epsilon) -> (A | B)?
                return f"({core})?"

        return core

    def visit_epsilon(self, node: Epsilon) -> str:
        assert False, "we should have compiled this away"

    def visit_non_terminal(self, node: NonTerminal) -> str:
        return node.name.lower()
