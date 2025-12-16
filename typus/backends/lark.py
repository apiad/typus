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

        # 2. Define all other rules
        for name, symbol in grammar.rules.items():
            # Lark rules must be lowercase to be tree nodes
            # (Uppercase are Terminals/Tokens, usually leaves)
            # For simplicity in this backend, we treat defined rules as lowercase Rules.
            clean_name = name.lower()
            definition = symbol.accept(self)
            lines.append(f"{clean_name}: {definition}")

        return "\n".join(lines)

    def visit_terminal(self, node: Terminal) -> str:
        if node.is_regex:
            # Lark regex syntax: /pattern/
            # We must escape forward slashes if present
            clean_val = node.value.replace("/", r"\/")
            return f"/{clean_val}/"

        # String literal: "value"
        # Escape quotes
        clean_val = node.value.replace('"', r"\"")
        return f'"{clean_val}"'

    def visit_sequence(self, node: Sequence) -> str:
        # Lark sequence: item1 item2 item3
        parts = []
        for child in node.items:
            part = child.accept(self)
            # If a child is a Choice, we must wrap it in parens to preserve precedence
            # Sequence(Choice(a,b), c) -> (a|b) c
            if isinstance(child, Choice):
                part = f"({part})"
            parts.append(part)
        return " ".join(parts)

    def visit_choice(self, node: Choice) -> str:
        # Lark choice: opt1 | opt2
        options = [child.accept(self) for child in node.options]
        return " | ".join(options)

    def visit_epsilon(self, node: Epsilon) -> str:
        # Lark represents empty as empty string literal "" or simply nothing in a choice
        # explicit "" is safer
        return '""'

    def visit_non_terminal(self, node: NonTerminal) -> str:
        # Reference to another rule
        return node.name.lower()
