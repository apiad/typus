from typing import Dict, Union
from typus.core import Symbol, Terminal, NonTerminal, Sequence, Choice

class Grammar:
    """
    The main container for defining rules.
    Usage:
        g = Grammar()
        g.start = Terminal("Hello")
    """
    def __init__(self):
        # We store the actual rule definitions here
        self.rules: Dict[str, Symbol] = {}
        self.root: Symbol | None = None

    def __getattr__(self, name: str) -> NonTerminal:
        """
        Allows forward references: g.expr usage creates a NonTerminal('expr').
        """
        return NonTerminal(name)

    def __setattr__(self, name: str, value: Union[Symbol, str]):
        """
        Defining a rule: g.rule = ...
        """
        if name in ("rules", "root"):
            super().__setattr__(name, value)
            return

        # Auto-convert string literals to Terminals
        if isinstance(value, str):
            value = Terminal(value)

        # Determine the root automatically (first rule defined is root by default)
        if not self.rules:
            self.root = value

        self.rules[name] = value
