from typing import Dict, Optional, Type
from typus.core import Epsilon, Symbol, Terminal, Sequence
from typus.languages.protocol import Language, RenderContext


class Python(Language):
    """
    Generates Python syntax rules.
    """

    def render_primitive(self, ctx, py_type: Type) -> Symbol:
        # 1. Integers: Standard regex
        if py_type is int:
            return ctx.grammar.regex(r"[0-9]+")

        # 2. Strings: Quoted string regex (simplified)
        if py_type is str:
            return ctx.grammar.regex(r'\"[^"]*\"')

        # 3. Booleans
        if py_type is bool:
            return Terminal("True") | Terminal("False")

        return Terminal(f"<{py_type.__name__}>")

    def render_head(
        self, ctx, name: str, args: Dict[str, Symbol], origin: Optional[Symbol] = None
    ) -> Symbol:
        # Build Argument List: "arg=val, arg2=val2"
        arg_seq = self._render_args(ctx, args)

        # Case A: Method call on another object (df.count())
        if origin:
            return origin + Terminal(f".{name}(") + arg_seq + Terminal(")")

        # Case B: Constructor or Function (DataFrame(...))
        return Terminal(f"{name}(") + arg_seq + Terminal(")")

    def render_tail(self, ctx, name: str, args: Dict[str, Symbol]) -> Symbol:
        # Fluent Chaining: .filter(...)
        arg_seq = self._render_args(ctx, args)
        return Terminal(f".{name}(") + arg_seq + Terminal(")")

    def _render_args(self, ctx, args: Dict[str, Symbol]) -> Symbol:
        """Helper to build 'k=v, k2=v2' sequence."""
        if not args:
            return Epsilon()

        items = []
        for i, (arg_name, arg_rule) in enumerate(args.items()):
            if i > 0:
                items.append(Terminal(", "))
            items.append(Terminal(f"{arg_name}="))
            items.append(arg_rule)

        return Sequence(*items)
