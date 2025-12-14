from typus.symbol import Symbol
from typus.backends.base import GrammarVisitor


def test_imports_work():
    """Confirms the project structure is valid."""
    assert issubclass(Symbol, object)
    assert issubclass(GrammarVisitor, object)
