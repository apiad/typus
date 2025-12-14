from abc import ABC, abstractmethod

class GrammarVisitor(ABC):
    """
    Abstract Base Class for all compilers (GBNF, JsonSchema, Lark).
    """

    @abstractmethod
    def visit_terminal(self, node):
        pass

    # We will add visit_sequence, visit_choice later
