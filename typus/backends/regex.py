import re
from collections import defaultdict
from typing import TYPE_CHECKING, Dict
from typus.core import Symbol, Terminal, NonTerminal, Sequence, Choice, Epsilon
from typus.backends.base import Compiler

if TYPE_CHECKING:
    from typus import Grammar


class RegexCompiler(Compiler[str]):
    """
    Compiles a Grammar into a single Regular Expression string.

    Args:
        max_depth (int, optional): The maximum recursion depth for unrolling recursive rules.
                                   If None, recursion raises a ValueError.
                                   Default is None.
    """

    def __init__(self, max_depth: int | None = None):
        self.max_depth = max_depth
        # Tracks how deep we are in each rule: {rule_name: depth}
        self._depth_stack: Dict[str, int] = defaultdict(int)

    def compile(self, grammar: "Grammar") -> str:
        self.grammar = grammar

        if grammar.root is None:
            raise ValueError("Grammar has no root.")

        # Start visiting from the root
        # We wrap the final result in ^...$ to ensure full string matching if desired,
        # but usually compilers return the pattern itself. Let's return the raw pattern.
        return grammar["root"].accept(self)

    def visit_terminal(self, node: Terminal) -> str:
        if node.is_regex:
            # We wrap raw regex in a non-capturing group to prevent precedence issues
            # e.g., if node.value is "a|b", and it's in a sequence "c" + node
            # we want "c(?:a|b)" not "ca|b"
            return f"(?:{node.value})"

        # Literals are safely escaped
        return re.escape(node.value)

    def visit_sequence(self, node: Sequence) -> str:
        # Sequence is just concatenation in Regex
        # Sequence(A, B) -> AB
        parts = [child.accept(self) for child in node.items]
        return "".join(parts)

    def visit_choice(self, node: Choice) -> str:
        # Choice is alternation |
        # We MUST wrap in non-capturing group to localize the alternation
        # Choice(A, B) -> (?:A|B)
        options = [child.accept(self) for child in node.options]
        return f"(?:{'|'.join(options)})"

    def visit_epsilon(self, node: Epsilon) -> str:
        return ""

    def visit_non_terminal(self, node: NonTerminal) -> str:
        name = node.name
        current_depth = self._depth_stack[name]

        # 1. Check Recursion Bounds
        if self.max_depth is not None:
            if current_depth >= self.max_depth:
                # Recursion limit hit: Stop expanding this branch.
                # Returning empty string effectively prunes this recursive path.
                # e.g. list ::= item list | item
                # at depth limit, 'list' becomes "", so 'item list' becomes 'item'.
                return ""
        elif current_depth > 0:
            # Strict mode: No recursion allowed
            raise ValueError(
                f"Recursion detected in rule '{name}'. "
                "Regex backend generally does not support recursion. "
                "Pass 'max_depth=N' to unroll the loop N times."
            )

        # 2. Enter Rule
        self._depth_stack[name] += 1

        try:
            # Resolve the rule body from the grammar
            if name not in self.grammar.rules:
                raise ValueError(f"Rule '{name}' is undefined.")

            body = self.grammar.rules[name]
            result = body.accept(self)

            # Optimization:
            # If the result is already wrapped or atomic, we might not need parens,
            # but wrapping NonTerminal results is generally safer for debugging and precedence.
            return result

        finally:
            # 3. Exit Rule
            self._depth_stack[name] -= 1
