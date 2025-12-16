from typing import Protocol, Dict, Any, Type
from typus.core import Symbol
from typus.grammar import Grammar


class RenderContext:
    """
    Data passed to language renderers to allow recursive resolution.
    """

    def __init__(self, grammar: Grammar, resolver):
        self.grammar = grammar
        self._resolver = resolver

    def resolve(self, py_type: Type) -> Symbol:
        """Get the grammar symbol for a dependent type."""
        return self._resolver(py_type)


class Language(Protocol):
    def render_head(
        self,
        ctx: RenderContext,
        name: str,
        args: Dict[str, Symbol],
        origin: Symbol | None = None,
    ) -> Symbol:
        """
        Render a 'Head' (Source).
        - If origin is None: "func(args)"
        - If origin is set:  "origin.method(args)"
        """
        ...

    def render_tail(
        self, ctx: RenderContext, name: str, args: Dict[str, Symbol]
    ) -> Symbol:
        """
        Render a 'Tail' (Link) in a chain.
        e.g. '.filter(...)'
        """
        ...

    def render_primitive(self, ctx: RenderContext, py_type: Type) -> Symbol:
        """
        Render a primitive type (int, str, bool).
        """
        ...
