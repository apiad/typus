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

    @classmethod
    def register(cls, name: str, factory: VisitorFactory):
        cls._backends[name] = factory

    def __getattr__(self, name: str) -> NonTerminal:
        return NonTerminal(name)

    def __setattr__(self, name: str, value: Union[Symbol, str]):
        if name in ("rules", "_backends"):
            super().__setattr__(name, value)
            return

        if isinstance(value, str):
            value = Terminal(value)

        self.rules[name] = value

    def compile(self, backend: Union[str, Compiler] = "gbnf", **kwargs) -> str:
        if "root" not in self.rules:
            raise RuntimeError("No root symbol defined")

        if isinstance(backend, str):
            if backend not in self._backends:
                known = ", ".join(self._backends.keys())
                raise ValueError(f"Unknown backend: '{backend}'. Available: {known}")
            backend = self._backends[backend](**kwargs)

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

    def cleanup(self):
        """
        Removes rules that are effectively Epsilon and updates references.
        """
        # 1. Identify Epsilon Rules (Fixed Point Iteration)
        epsilon_rules = set()

        while True:
            changed = False
            for name, rule in self.rules.items():
                if name in epsilon_rules:
                    continue

                if self._is_symbol_epsilon(rule, epsilon_rules):
                    epsilon_rules.add(name)
                    changed = True

            if not changed:
                break

        # 2. Prune Epsilon Rules & Update References
        new_rules = {}
        for name, rule in self.rules.items():
            if name in epsilon_rules:
                continue  # Delete the rule

            # Update the rule body (replace Refs to empty rules with Epsilon)
            new_body = self._prune_symbol(rule, epsilon_rules)

            # If the rule became empty during pruning (e.g. it was Sequence(EmptyRef)), drop it too
            if isinstance(new_body, Epsilon):
                continue

            new_rules[name] = new_body

        self.rules = new_rules

        # 3. Update Root
        if self.root:
            self.root = self._prune_symbol(self.root, epsilon_rules)

    def _is_symbol_epsilon(self, sym: Symbol, eps_set: set[str]) -> bool:
        if isinstance(sym, Epsilon):
            return True
        if isinstance(sym, NonTerminal):
            return sym.name in eps_set

        if isinstance(sym, Sequence):
            # Sequence is empty if ALL items are empty
            return not sym.items or all(
                self._is_symbol_epsilon(i, eps_set) for i in sym.items
            )

        if isinstance(sym, Choice):
            # Choice is empty if ALL options are empty
            return not sym.options or all(
                self._is_symbol_epsilon(o, eps_set) for o in sym.options
            )

        return False

    def _prune_symbol(self, sym: Symbol, eps_set: set[str]) -> Symbol:
        if isinstance(sym, NonTerminal):
            if sym.name in eps_set:
                return Epsilon()
            return sym

        if isinstance(sym, Sequence):
            new_items = []
            for item in sym.items:
                pruned = self._prune_symbol(item, eps_set)
                if not isinstance(pruned, Epsilon):
                    new_items.append(pruned)

            if not new_items:
                return Epsilon()
            if len(new_items) == 1:
                return new_items[0]
            return Sequence(*new_items)

        if isinstance(sym, Choice):
            new_opts = []
            has_epsilon = False
            for opt in sym.options:
                pruned = self._prune_symbol(opt, eps_set)
                if isinstance(pruned, Epsilon):
                    has_epsilon = True
                else:
                    new_opts.append(pruned)

            if not new_opts:
                return Epsilon()

            if has_epsilon:
                # Deduplicate explicit Epsilon
                if not any(isinstance(o, Epsilon) for o in new_opts):
                    new_opts.append(Epsilon())

            if len(new_opts) == 1:
                return new_opts[0]
            return Choice(*new_opts)

        return sym
