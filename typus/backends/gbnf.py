from typing import Dict
from typus.core import Epsilon, Symbol, Terminal, NonTerminal, Sequence, Choice
from typus.backends.base import Compiler
from typus.grammar import Grammar


class GBNFCompiler(Compiler[str]):
    """
    Compiles a Grammar into a GBNF string for Llama.cpp.
    """

    def visit_terminal(self, node: Terminal) -> str:
        if node.is_regex:
            return node.value
        # Escape backslashes and double quotes
        escaped = node.value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def visit_sequence(self, node: Sequence) -> str:
        if not node.items:
            return '""'
        # GBNF uses space for sequences: "A" "B"
        return " ".join(item.accept(self) for item in node.items)

    def visit_choice(self, node: Choice) -> str:
        if not node.options:
            return '""'
        # We wrap choices in parens for safety: ( "A" | "B" )
        inner = " | ".join(opt.accept(self) for opt in node.options)
        return f"( {inner} )"

    def visit_non_terminal(self, node: NonTerminal) -> str:
        # GBNF conventionally uses kebab-case
        return node.name.replace("_", "-")

    def visit_rule(self, head: NonTerminal, body: Symbol) -> str:
        return f"{head.name} ::= {body.accept(self)}"

    def visit_epsilon(self, node: Epsilon) -> str:
        return '""'

    def compile(self, grammar: Grammar) -> str:
        lines = []

        # 1. Generate the root rule
        # We implicitly define 'root' to point to the user's root symbol
        if "root" not in grammar.rules:
            raise ValueError("Grammar has no root defined.")

        lines.append(f"root ::= {grammar.rules['root'].accept(self)}")

        # 2. Generate all named rules
        for name, symbol in grammar.rules.items():
            # Skip if user manually defined 'root' in rules to avoid duplicate
            if name == "root" and grammar.root:
                continue

            rule_name = name.replace("_", "-")
            expression = symbol.accept(self)
            lines.append(f"{rule_name} ::= {expression}")

        return "\n".join(lines)
