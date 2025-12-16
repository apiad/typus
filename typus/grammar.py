from string import Formatter
from typing import Dict, Union, Optional, Callable
import re
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

    @classmethod
    def register(cls, name: str, factory: VisitorFactory):
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

    def compile(self, backend: Union[str, Compiler] = "gbnf", **kwargs) -> str:
        if isinstance(backend, str):
            if backend not in self._backends:
                known = ", ".join(self._backends.keys())
                raise ValueError(f"Unknown backend: '{backend}'. Available: {known}")
            backend = self._backends[backend](**kwargs)

        if self.root is None:
            raise RuntimeError("No root symbol defined")

        return backend.compile(self)

    # --- High-Level Builders ---

    def regex(self, pattern: str) -> Terminal:
        return Terminal(pattern, is_regex=True)

    def maybe(self, symbol: Union[Symbol, str]) -> Choice:
        """Optional: symbol | ε"""
        if isinstance(symbol, str):
            symbol = Terminal(symbol)
        return Choice(symbol, Epsilon())

    def _sanitize(self, text: str) -> str:
        """Converts arbitrary text into a valid GBNF-friendly identifier part."""
        # Replace non-alphanumeric chars with underscore
        clean = re.sub(r"[^a-zA-Z0-9]", "_", text)
        # Collapse multiple underscores
        clean = re.sub(r"__+", "_", clean)
        return clean.strip("_")

    def _get_name(self, symbol: Symbol) -> str:
        """Derives a stable, readable name for a symbol."""
        if isinstance(symbol, NonTerminal):
            return symbol.name
        if isinstance(symbol, Terminal):
            if symbol.is_regex:
                return "regex"
            return self._sanitize(symbol.value)
        if isinstance(symbol, Choice):
            # Try to name Choice(A, B) as "A_or_B"
            parts = [self._get_name(opt) for opt in symbol.options]
            return "_or_".join(parts)
        return "item"

    def some(
        self,
        symbol: Union[Symbol, str],
        sep: Union[Symbol, str, None] = None,
        name: Optional[str] = None,
    ) -> NonTerminal:
        """
        OneOrMore: symbol (sep symbol)*

        Args:
            name: Explicit rule name. If None, derives 'some_{symbol}[_sep_{sep}]'.

        Raises:
            ValueError: If a rule with the target name already exists.
        """
        if isinstance(symbol, str):
            symbol = Terminal(symbol)

        # 1. Determine Name
        if name is None:
            sym_name = self._get_name(symbol)
            name = f"some_{sym_name}"

            if sep:
                if isinstance(sep, str):
                    sep = Terminal(sep)
                sep_name = self._get_name(sep)
                if sep_name:
                    name += f"_sep_{sep_name}"

        # 2. Strict Uniqueness Check
        if name in self.rules:
            raise ValueError(f"Rule '{name}' already exists.")

        # 3. Define the Recursive Rule
        ref = NonTerminal(name)
        if sep:
            # R ::= symbol | symbol + sep + R
            self.rules[name] = Choice(symbol, symbol + sep + ref)
        else:
            # R ::= symbol | symbol + R
            self.rules[name] = Choice(symbol, symbol + ref)

        return ref

    def any(
        self,
        symbol: Union[Symbol, str],
        sep: Union[Symbol, str, None] = None,
        name: Optional[str] = None,
    ) -> Choice:
        """ZeroOrMore: (symbol (sep symbol)*)?"""
        # We pass the explicit name to some(), which will enforce the uniqueness check
        return self.maybe(self.some(symbol, sep, name=name))

    def template(self, fmt: str, **kwargs) -> Sequence:
        """
        Helper method to quickly add a sequence of symbols
        by interpolating rules in a template (f-string like) text.

        Usage example:

        >>> g.article = g.template("# {title} \n\n {content}")

        This creates a rule `g.article` which is a sequence of terminals
        like "# " and " \n\n " interpolating the rules `g.title` and `g.content`.

        Interpolated rules are resolved by name in the current grammar,
        but can be overriden using **kwargs.
        """
        symbols = []

        # Iterate over the parsed structure
        for literal, field_name, spec, conversion in Formatter().parse(fmt):

            # 1. Add the static text constraint
            if literal:
                symbols.append(Terminal(literal))

            # 2. Add the dynamic grammar rule
            if field_name:
                # Look up the rule in the passed kwargs or the grammar itself
                rule = kwargs.get(field_name) or getattr(self, field_name)
                symbols.append(rule)

        return Sequence(*symbols)
