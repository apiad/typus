from typing import Dict, Type, List
from typus.core import Symbol, Choice, NonTerminal, Terminal
from typus.grammar import Grammar
from typus.domain.models import TypeNode
from typus.domain.reflector import Reflector
from typus.languages.protocol import Language, RenderContext

class DomainGenerator:
    """
    Compiles a set of Python types into a Grammar using a specific Language strategy.
    Implements the 'Head + Any(Tail)' algorithm to handle method chaining.
    """
    def __init__(self, language: Language):
        self.language = language
        self.reflector = Reflector()
        self.grammar = Grammar()
        # Cache: Python Type -> NonTerminal
        self._cache: Dict[Type, NonTerminal] = {}

    def build(self, *entrypoints: Type) -> Grammar:
        """
        Main entrypoint.
        Reflects on the entrypoints and builds the grammar for the ENTIRE domain.
        """
        # 1. Build the Semantic Graph (Reflect on everything reachable)
        # This finds DF, load, AND int (because count returns it)
        nodes = self.reflector.reflect(*entrypoints)

        if not nodes:
            raise ValueError("No types found to generate.")

        # 2. Force generation of rules for ALL discovered types
        # This ensures 'int' rule is generated with 'count()' option
        # even if 'int' is not currently an input to anything.
        for node in nodes:
            self._resolve_type(node.py_type)

        # 3. Set the Root
        # We default to the first entrypoint, but the user can change this on the grammar
        root_type = nodes[0].py_type
        self.grammar.root = self._resolve_type(root_type)

        return self.grammar

    def _resolve_type(self, py_type: Type) -> Symbol:
        # 1. Get the Semantic Node to check for producers
        # We access the internal dictionary of the reflector
        # (In prod code, we might want a cleaner public API for this)
        node = self.reflector._get_or_create_node(py_type)

        # 2. Handle Primitives
        if py_type in (int, str, float, bool):
            # Only short-circuit if there are NO dynamic ways to produce this type
            # e.g. If 'df.count()' exists, node.producers will not be empty.
            if not node.producers:
                ctx = RenderContext(self.grammar, self._resolve_type)
                return self.language.render_primitive(ctx, py_type)

            # If it HAS producers, we fall through to the standard logic below
            # which builds a Choice(Literal | FunctionCalls)

        # 3. Check Cache
        if py_type in self._cache:
            return self._cache[py_type]

        # 4. Create Forward Reference
        name = getattr(py_type, "__name__", str(py_type))
        ref = NonTerminal(name)
        self._cache[py_type] = ref

        # 5. Build Rule Body
        self._build_rule_body(node, ref, is_primitive=(py_type in (int, str, float, bool)))

        return ref

    def _build_rule_body(self, node: TypeNode, ref: NonTerminal, is_primitive: bool = False):
        ctx = RenderContext(self.grammar, self._resolve_type)
        heads = []
        tails = []

        # If it is primitive, the "Literal" representation is one of the Heads
        if is_primitive:
            heads.append(self.language.render_primitive(ctx, node.py_type))

        for trans in node.producers:
            # Resolve Arguments
            arg_symbols = {
                k: self._resolve_type(v.py_type)
                for k, v in trans.params.items()
            }

            # Classification: Is it a Chain Link?
            # It is a chain link if it's a method AND it returns the same type it originated from.
            is_chain = trans.is_method and trans.origin_type == node

            if is_chain:
                sym = self.language.render_tail(ctx, trans.name, arg_symbols)
                tails.append(sym)
            else:
                sym = self.language.render_head(ctx, trans.name, arg_symbols)
                heads.append(sym)

        # 6. Assembly
        if not heads:
             # If no ways to create it, it's a dead end?
             # Or maybe it's abstract. For now, empty choice.
             head_rule = Choice()
        else:
             head_rule = Choice(*heads)

        if not tails:
            # Simple case: T ::= Head
            self.grammar.rules[ref.name] = head_rule
        else:
            # Fluent case: T ::= Head (Tail)*
            tail_choice = Choice(*tails)

            # We explicitly name the tail rule for cleaner GBNF
            tail_name = f"{ref.name}_Chain"
            self.grammar.rules[tail_name] = tail_choice

            # Structure: Head + Any(Tail)
            self.grammar.rules[ref.name] = head_rule + self.grammar.any(tail_name)
