from abc import ABC, abstractmethod


class Symbol(ABC):
    """
    The atomic unit of a grammar.
    Everything (Terminals, Sequences, Choices) will inherit from this.
    """

    @abstractmethod
    def accept(self, visitor):
        """Standard Visitor Pattern entry point."""
        pass
