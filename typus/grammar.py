from typing import Dict, Union, Optional, Type, Callable, Any, TYPE_CHECKING
from typus.core import Symbol, Terminal, NonTerminal


from .backends.base import Compiler

# A Factory is anything callable that returns a visitor (Class or Function)
VisitorFactory = Callable[..., Compiler]


class Grammar:
    """
    The main container for defining rules.
    """

    _backends: Dict[str, VisitorFactory] = {}

    def __init__(self):
        self.rules: Dict[str, Symbol] = {}
        self.root: Optional[Symbol] = None

    @classmethod
    def register(cls, name: str, factory: VisitorFactory):
        """
        Registers a new backend compiler.
        Args:
            name: The key to use in compile(backend=name)
            factory: A class or function that accepts **kwargs and returns a visitor instance.
        """
        cls._backends[name] = factory

    def __getattr__(self, name: str) -> NonTerminal:
        return NonTerminal(name)

    def __setattr__(self, name: str, value: Union[Symbol, str]):
        if name in ("rules", "root", "_backends"):
            super().__setattr__(name, value)
            return

        if isinstance(value, str):
            value = Terminal(value)

        if not self.rules:
            self.root = value

        self.rules[name] = value

    def compile(self, backend: str | Compiler = "gbnf", **kwargs) -> str:
        """
        Compiles the grammar using the requested backend.
        Any extra kwargs are passed to the backend constructor.
        """
        if backend not in self._backends:
            known = ", ".join(self._backends.keys())
            raise ValueError(f"Unknown backend: '{backend}'. Available: {known}")

        if isinstance(backend, str):
            backend = self._backends[backend](**kwargs)

        # Instantiate the compiler with user options (e.g., indent=2)

        if self.root is None:
            raise RuntimeError("No root symbol defined")

        return backend.compile(self)
