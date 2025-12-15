from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union, List


if TYPE_CHECKING:
    from .backends.base import Compiler


class Symbol(ABC):
    """
    The atomic unit of a grammar.
    """

    @abstractmethod
    def accept[T](self, visitor: "Compiler[T]") -> T:
        pass

    # --- Operator Overloading ---

    def __add__(self, other: Union["Symbol", str]) -> "Sequence":
        # This calls Sequence(self, other), which will trigger flattening logic
        return Sequence(self, other)

    def __radd__(self, other: Union["Symbol", str]) -> "Sequence":
        return Sequence(other, self)

    def __or__(self, other: Union["Symbol", str]) -> "Choice":
        return Choice(self, other)

    def __ror__(self, other: Union["Symbol", str]) -> "Choice":
        return Choice(other, self)


class Terminal(Symbol):
    """Represents a literal string or a regex pattern."""

    def __init__(self, value: str, is_regex: bool = False):
        self.value = value
        self.is_regex = is_regex

    def accept(self, visitor: "Compiler"):
        return visitor.visit_terminal(self)

    def __repr__(self):
        kind = "Regex" if self.is_regex else "Str"
        return f"{kind}({self.value!r})"


class Epsilon(Symbol):
    """
    Represents the Empty String (ε).
    It produces no tokens and effectively disappears in Sequences.
    """

    def accept[T](self, visitor: "Compiler[T]") -> T:
        return visitor.visit_epsilon(self)

    def __repr__(self):
        return "Epsilon()"


class Sequence(Symbol):
    """A sequence of symbols (A + B)."""

    def __init__(self, *items: Union[Symbol, str]):
        self.items: List[Symbol] = []

        for item in items:
            if isinstance(item, Sequence):
                self.items.extend(item.items)
            elif isinstance(item, Epsilon):
                # Optimization: A + Epsilon -> A
                pass
            elif isinstance(item, str):
                self.items.append(Terminal(item))
            else:
                self.items.append(item)

    def accept(self, visitor: "Compiler"):
        return visitor.visit_sequence(self)


class Choice(Symbol):
    """A choice between symbols (A | B)."""

    def __init__(self, *options: Union[Symbol, str]):
        self.options: List[Symbol] = []

        for opt in options:
            if isinstance(opt, Choice):
                # FLATTENING: Choice(Choice(A, B), C) -> Choice(A, B, C)
                self.options.extend(opt.options)
            elif isinstance(opt, str):
                self.options.append(Terminal(opt))
            else:
                self.options.append(opt)

    def accept(self, visitor: "Compiler"):
        return visitor.visit_choice(self)


class NonTerminal(Symbol):
    """A reference to another rule (e.g., 'expr' or 'statement')."""

    def __init__(self, name: str):
        self.name = name

    def accept(self, visitor: "Compiler"):
        return visitor.visit_non_terminal(self)

    def __repr__(self):
        return f"Ref({self.name})"
