import inspect
from typing import Callable, Dict, Type, List
from typus.core import Epsilon, Symbol, Choice, NonTerminal, Terminal
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
        self._build_rule_body(
            node, ref, is_primitive=(py_type in (int, str, float, bool))
        )

        return ref

    def _build_rule_body(
        self, node: TypeNode, ref: NonTerminal, is_primitive: bool = False
    ):
        ctx = RenderContext(self.grammar, self._resolve_type)
        heads = []
        fluents = []  # Methods returning T (Fluent)
        exits = []  # Methods returning U != T (Exit)

        # 1. Classify Producers
        if is_primitive:
            heads.append(self.language.render_primitive(ctx, node.py_type))

        for trans in node.producers:
            arg_symbols = {
                k: self._resolve_type(v.py_type) for k, v in trans.params.items()
            }

            # Is it a method on this type?
            if trans.is_method and trans.origin_type == node:
                sym = self.language.render_tail(ctx, trans.name, arg_symbols)
                if trans.return_type == node:
                    fluents.append(sym)
                else:
                    # It's an Exit Transition (e.g. .count() -> int)
                    # We store the transition symbol AND the target type
                    exits.append((sym, trans.return_type))
            else:
                # It's a Head (Constructor/Function)
                origin_sym = None
                if trans.is_method and trans.origin_type:
                    origin_sym = self._resolve_type(trans.origin_type.py_type)

                sym = self.language.render_head(
                    ctx, trans.name, arg_symbols, origin=origin_sym
                )
                heads.append(sym)

        # 2. Build Strict Rule (T ::= Head + FluentChain)
        # This preserves the existing "Type Safe" logic for arguments
        head_rule = Choice(*heads) if heads else Choice()
        fluent_choice = Choice(*fluents) if fluents else Choice()

        # Define Strict Chain Rule: (Fluent)*
        strict_chain_name = f"{ref.name}_Chain"
        self.grammar.rules[strict_chain_name] = fluent_choice
        strict_chain_ref = self.grammar.any(strict_chain_name)

        # T ::= Head + StrictChain
        self.grammar.rules[ref.name] = head_rule + strict_chain_ref

        # 3. Build Open Pipeline Rule (Pipeline_T)
        # Pipeline_T ::= StrictChain + ( Exit_U Pipeline_U | Exit_V Pipeline_V | epsilon )
        # This allows the Root to transition out.

        pipeline_name = f"{ref.name}_Pipeline"

        # The 'Next Step' is a choice of all possible exits
        exit_options = []
        for sym, target_node in exits:
            # Recursively refer to the TARGET's pipeline
            # This links Pipeline_DF -> .count() -> Pipeline_int
            target_pipeline_name = f"{target_node.name}_Pipeline"

            # We must ensure the target pipeline exists (Forward Ref logic)
            # We can just use NonTerminal string reference, GBNF resolves it later
            exit_options.append(sym + NonTerminal(target_pipeline_name))

            # Trigger resolution of the target to ensure its rules are built
            self._resolve_type(target_node.py_type)

        if exit_options:
            # FIX: Use maybe() logic instead of Choice(..., Epsilon()) directly
            # to be friendlier to EBNF generators
            pipeline_rule = strict_chain_ref + self.grammar.maybe(Choice(*exit_options))
        else:
            pipeline_rule = strict_chain_ref

        self.grammar.rules[pipeline_name] = pipeline_rule

    def build(self, *entrypoints: Type) -> Grammar:
        nodes = self.reflector.reflect(*entrypoints)
        if not nodes:
            raise ValueError("No types found.")

        # 1. Build all rules (Types and Pipelines)
        for node in nodes:
            self._resolve_type(node.py_type)

        # 2. Construct Root from Entrypoints
        root_options = []

        for entry in entrypoints:
            # Case A: Entry is a Class (e.g. DataFrame)
            if inspect.isclass(entry):
                node = self.reflector._get_or_create_node(entry)
                # Find all Constructors for this class
                heads = self._render_entrypoint_heads(node, target_node=node)
                pipeline_ref = NonTerminal(f"{node.name}_Pipeline")

                if heads:
                    root_options.append(Choice(*heads) + pipeline_ref)

            # Case B: Entry is a Function (e.g. read_csv)
            elif callable(entry):
                # We need to find the node that this function *returns*
                # The Reflector has analyzed it. We find the transition in the graph.
                # It will be a producer on some node.

                target_node = None
                target_trans = None

                # Scan all nodes to find which one has this function as a producer
                for n in nodes:
                    for t in n.producers:
                        # Match by name is weak, but sufficient for v0.4 given typical usage
                        # Ideally Reflector returns a map of entrypoint -> transition
                        if t.name == entry.__name__:
                            target_node = n
                            target_trans = t
                            break
                    if target_node:
                        break

                if target_node:
                    # Head is the function call
                    # Pipeline is the Return Type's pipeline
                    ctx = RenderContext(self.grammar, self._resolve_type)
                    arg_syms = {
                        k: self._resolve_type(v.py_type)
                        for k, v in target_trans.params.items()
                    }

                    head = self.language.render_head(ctx, target_trans.name, arg_syms)
                    pipeline_ref = NonTerminal(f"{target_node.name}_Pipeline")

                    root_options.append(head + pipeline_ref)

        if not root_options:
            # Fallback: just allow all defined pipelines (loose mode)
            # This handles cases where entrypoints weren't found or mapped correctly
            root_options = [NonTerminal(f"{n.name}_Pipeline") for n in nodes]

        self.grammar.root = Choice(*root_options)
        return self.grammar

    def _render_entrypoint_heads(
        self, node: TypeNode, target_node: TypeNode
    ) -> List[Symbol]:
        """Helper to render constructors/static factories for a class node."""
        heads = []
        ctx = RenderContext(self.grammar, self._resolve_type)

        for trans in node.producers:
            # Entrypoints are only Heads (not chains)
            if not (trans.is_method and trans.origin_type == node):
                origin_sym = None
                if trans.is_method and trans.origin_type:
                    origin_sym = self._resolve_type(trans.origin_type.py_type)

                arg_syms = {
                    k: self._resolve_type(v.py_type) for k, v in trans.params.items()
                }
                heads.append(
                    self.language.render_head(
                        ctx, trans.name, arg_syms, origin=origin_sym
                    )
                )
        return heads
