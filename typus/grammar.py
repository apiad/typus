from typing import Dict, Union, Optional, Callable
from typus.core import Symbol, Terminal, NonTerminal, Sequence, Choice, Epsilon
from .backends.base import Compiler

VisitorFactory = Callable[..., Compiler]


class Grammar:
    """
    The main container for defining rules.
    """

    _backends: Dict[str, VisitorFactory] = {}

    def __init__(self):
        self.rules: Dict[str, Symbol] = {}
        self.root: Optional[Symbol] = None
        self._anon_count = 0

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
        if name in ("rules", "root", "_backends", "_anon_count"):
            super().__setattr__(name, value)
            return

        if isinstance(value, str):
            value = Terminal(value)

        if not self.rules:
            self.root = value

        self.rules[name] = value

    def regex(self, pattern: str) -> Terminal:
        """
        Creates a Terminal that is treated as a raw regex pattern.
        Note: The pattern syntax depends on the backend (e.g. GBNF).
        """
        return Terminal(pattern, is_regex=True)

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

    # --- High-Level Builders ---

    def _gen_name(self, prefix: str) -> str:
        self._anon_count += 1
        return f"_{prefix}_{self._anon_count}"

    def maybe(self, symbol: Union[Symbol, str]) -> Choice:
        """
        Optional: symbol | ε
        """
        if isinstance(symbol, str):
            symbol = Terminal(symbol)
        return Choice(symbol, Epsilon())

    def some(
        self, symbol: Union[Symbol, str], sep: Union[Symbol, str, None] = None
    ) -> NonTerminal:
        """
        OneOrMore: symbol (sep symbol)*
        Implemented as recursive rule:
            R ::= symbol | symbol sep R
        """
        if isinstance(symbol, str):
            symbol = Terminal(symbol)

        name = self._gen_name("some")
        ref = NonTerminal(name)

        if sep:
            if isinstance(sep, str):
                sep = Terminal(sep)
            # R ::= symbol | symbol + sep + R
            self.rules[name] = symbol | symbol + sep + ref
        else:
            # R ::= symbol | symbol + R
            self.rules[name] = symbol | symbol + ref

        return ref

    def any(
        self, symbol: Union[Symbol, str], sep: Union[Symbol, str, None] = None
    ) -> Choice:
        """
        ZeroOrMore: (symbol (sep symbol)*)?
        Implemented as:
            maybe(some(symbol, sep))
        """
        return self.maybe(self.some(symbol, sep))
