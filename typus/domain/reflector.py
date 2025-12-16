import inspect
from typing import Any, Callable, get_type_hints
from collections import deque
from typus.domain.models import TypeNode, Transition


class Reflector:
    """
    Analyzes Python objects to build a Semantic Type Graph.
    Uses Breadth-First Search (BFS) to discover types reachable from entrypoints.
    """

    def __init__(self):
        # Cache: Map Python Type -> Semantic TypeNode
        self._nodes: dict[type, TypeNode] = {}
        # Queue: Types discovered but not yet scanned for methods
        self._queue: deque[TypeNode] = deque()

    def reflect(self, *entrypoints: Any) -> list[TypeNode]:
        """
        Main entrypoint. Pass a list of Classes or Functions to analyze.
        Returns the list of all discovered TypeNodes.
        """
        # 1. Seed the graph with entrypoints
        for obj in entrypoints:
            if inspect.isclass(obj):
                self._get_or_create_node(obj)
            elif callable(obj):
                self._analyze_function(obj)
            else:
                raise ValueError(f"Unsupported entrypoint: {obj}")

        # 2. BFS: Process types until we exhaust the graph
        while self._queue:
            node = self._queue.popleft()
            self._analyze_class(node)

        return list(self._nodes.values())

    def _get_or_create_node(self, py_type: type) -> TypeNode:
        """
        Returns an existing TypeNode or creates a new one and queues it for analysis.
        """
        # Unwrap generic aliases (e.g., List[int] -> int? or keep List?)
        # For v0.4, we treat the origin as the type (simplification)
        origin = getattr(py_type, "__origin__", py_type)

        if origin in self._nodes:
            return self._nodes[origin]

        name = getattr(origin, "__name__", str(origin))
        node = TypeNode(py_type=origin, name=name)
        self._nodes[origin] = node

        # Only queue complex types (classes) for method analysis
        # Primitives (int, str) don't have methods we care about for the grammar
        if inspect.isclass(origin) and origin not in (str, int, float, bool, list, dict):
            self._queue.append(node)

        return node

    def _analyze_function(self, func: Callable, owner_node: TypeNode | None = None):
        """
        Analyzes a single function/method and registers it as a Transition.
        """
        name = func.__name__

        # Skip private methods and magic methods (except __init__)
        if name.startswith("_") and name != "__init__":
            return

        # 1. Resolve Types using standard Python introspection
        try:
            # get_type_hints automatically resolves string forward references!
            hints = get_type_hints(func)
        except Exception:
            # Fallback for when hints fail (e.g. lambdas or partials)
            return

        is_init = (name == "__init__")

        # 2. Determine Semantics
        if is_init:
            # __init__ is a Constructor.
            # It belongs to the class, but it does NOT consume an instance (no 'self' in DSL).
            # So is_method = False (semantically).
            if not owner_node: return
            return_type = owner_node
            is_method_call = False # Treat as static factory
            origin_type = None     # No origin (created from void/args)
        else:
            # Regular function or method
            if "return" not in hints: return
            rt = hints.pop("return")
            if rt is None or rt is type(None): return
            return_type = self._get_or_create_node(rt)

            is_method_call = (owner_node is not None)
            origin_type = owner_node

        # 3. Analyze Parameters
        params: dict[str, TypeNode] = {}
        sig = inspect.signature(func)

        for param_name, _ in sig.parameters.items():
            if param_name == "self":
                continue

            if param_name in hints:
                param_type = hints[param_name]
                params[param_name] = self._get_or_create_node(param_type)
            else:
                # Untyped parameters are ignored or default to str?
                # Strict mode: ignore
                pass

        # 4. Create Transition
        transition = Transition(
            name=name,
            return_type=return_type,
            params=params,
            is_method=is_method_call,
            origin_type=origin_type,
        )

        # 5. Register the Transition on the *Return Type*
        # (Because this function implies "Here is a way to make a [Return Type]")
        return_type.producers.append(transition)

    def _analyze_class(self, node: TypeNode):
        """
        Scans a class for methods and __init__.
        """
        cls = node.py_type

        # Iterate over all members
        for name, member in inspect.getmembers(cls):
            if inspect.isfunction(member) or inspect.ismethod(member):
                # Analyze the method, marking 'node' as the owner/origin
                self._analyze_function(member, owner_node=node)
