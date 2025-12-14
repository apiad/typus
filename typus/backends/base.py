from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core import Terminal, NonTerminal, Sequence, Choice


class GrammarVisitor[T](ABC):
    """
    Abstract Base Class for all compilers (GBNF, JsonSchema, Lark).
    """

    @abstractmethod
    def visit_terminal(self, node: "Terminal") -> T:
        pass

    @abstractmethod
    def visit_sequence(self, node: "Sequence") -> T:
        pass

    @abstractmethod
    def visit_choice(self, node: "Choice") -> T:
        pass

    @abstractmethod
    def visit_non_terminal(self, node: "NonTerminal") -> T:
        pass
