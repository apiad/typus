from abc import ABC, abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .backends.base import GrammarVisitor


class Symbol(ABC):
    """
    The atomic unit of a grammar.
    """

    @abstractmethod
    def accept[T](self, visitor: "GrammarVisitor[T]") -> T:
        pass


class Terminal(Symbol):
    """Represents a literal string or a regex pattern."""

    def __init__(self, value: str, is_regex: bool = False):
        self.value = value
        self.is_regex = is_regex

    def accept(self, visitor: "GrammarVisitor"):
        return visitor.visit_terminal(self)

    def __repr__(self):
        kind = "Regex" if self.is_regex else "Str"
        return f"{kind}({self.value!r})"


class Sequence(Symbol):
    """A sequence of symbols (A + B)."""

    def __init__(self, *items: Symbol):
        self.items = list(items)

    def accept(self, visitor: "GrammarVisitor"):
        return visitor.visit_sequence(self)


class Choice(Symbol):
    """A choice between symbols (A | B)."""

    def __init__(self, *options: Symbol):
        self.options = list(options)

    def accept(self, visitor: "GrammarVisitor"):
        return visitor.visit_choice(self)


class NonTerminal(Symbol):
    """A reference to another rule (e.g., 'expr' or 'statement')."""

    def __init__(self, name: str):
        self.name = name

    def accept(self, visitor: "GrammarVisitor"):
        return visitor.visit_non_terminal(self)

    def __repr__(self):
        return f"Ref({self.name})"
