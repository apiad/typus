from abc import ABC, abstractmethod
from typing import Any


class GrammarVisitor(ABC):
    """
    Abstract Base Class for all compilers (GBNF, JsonSchema, Lark).
    """

    @abstractmethod
    def visit_terminal(self, node) -> Any:
        pass

    @abstractmethod
    def visit_sequence(self, node) -> Any:
        pass

    @abstractmethod
    def visit_choice(self, node) -> Any:
        pass

    # visit_non_terminal will come in Step 3
    # We will add visit_sequence, visit_choice later
