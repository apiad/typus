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
        lines.append(f"start: root")

        for name, symbol in grammar.rules.items():
            definition = symbol.accept(self)
            if not definition:
                definition = '""'
            lines.append(f"{name.lower()}: {definition}")

        return "\n".join(lines)

    def visit_terminal(self, node: Terminal) -> str:
        if node.is_regex:
            clean_val = node.value.replace("/", r"\/")
            return f"/{clean_val}/"

        clean_val = node.value.replace('"', r"\"")
        return f'"{clean_val}"'

    def visit_sequence(self, node: Sequence) -> str:
        parts = [child.accept(self) for child in node.items]
        clean_parts = [p for p in parts if p]

        if not clean_parts:
            return ""

        final_parts = []
        for child, part in zip(node.items, parts):
            if not part:
                continue

            # Wrap choices if they contain pipes to preserve precedence
            if isinstance(child, Choice) and len(child.options) > 1:
                if "|" in part:
                    part = f"({part})"

            final_parts.append(part)

        return " ".join(final_parts)

    def visit_choice(self, node: Choice) -> str:
        compiled_opts = []
        has_epsilon = False

        for child in node.options:
            if isinstance(child, Epsilon):
                has_epsilon = True
            else:
                res = child.accept(self)
                if not res:
                    has_epsilon = True
                else:
                    compiled_opts.append(res)

        if not compiled_opts:
            # If all options are epsilon, the choice is effectively empty
            return ""

        core = " | ".join(compiled_opts)

        if has_epsilon:
            if len(compiled_opts) == 1:
                # Choice(A, Epsilon) -> A?
                if " " in core and not (core.startswith("(") and core.endswith(")")):
                    return f"({core})?"
                return f"{core}?"
            else:
                # Choice(A, B, Epsilon) -> (A | B)?
                return f"({core})?"

        return core

    def visit_epsilon(self, node: Epsilon) -> str:
        return ""

    def visit_non_terminal(self, node: NonTerminal) -> str:
        return node.name.lower()
