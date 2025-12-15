from typus.core import Symbol
from typus.backends.base import Compiler


def test_imports_work():
    """Confirms the project structure is valid."""
    assert issubclass(Symbol, object)
    assert issubclass(Compiler, object)
