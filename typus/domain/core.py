from __future__ import annotations
import inspect
from dataclasses import dataclass, field
from typing import Dict, List, Set, Type, Any, Callable, Optional, get_type_hints


class VoidType:
    """
    Sentinel type representing the start of an execution chain (The Root).
    It has no runtime value, but acts as the source for Constructors and Functions.
    """

    pass


class NoReturn:
    """
    Sentinel type to represent methods with no return type,
    so we can stop there.
    """

    pass


@dataclass
class Node:
    """
    A Vertex in the Type Graph, representing a Python Type.
    """

    py_type: Type
    name: str

    # Edges starting from this node (Methods)
    outgoing: List[Edge] = field(default_factory=list)

    # Edges ending at this node (Producers)
    incoming: List[Edge] = field(default_factory=list)

    # State tracking for incremental builds
    scanned: bool = False

    def __hash__(self):
        return hash(self.py_type)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return NotImplemented
        return self.py_type == other.py_type

    def __repr__(self):
        return f"<Node: {self.name}>"


@dataclass
class Edge:
    """
    A Directed Edge representing a Callable (Function, Method, Constructor).
    Connects source -> target.
    """

    name: str
    source: Node
    target: Node

    # Arguments required to traverse this edge
    params: Dict[str, Node] = field(default_factory=dict)

    def __repr__(self):
        args = ", ".join(f"{k}: {v.name}" for k, v in self.params.items())
        return (
            f"<Edge: {self.source.name} --[{self.name}({args})]--> {self.target.name}>"
        )


class Domain:
    """
    The Graph of Types.
    Manages Nodes (Types) and Edges (Transitions).
    Allows incremental growth via .register().
    """

    def __init__(self):
        self.nodes: Dict[Type, Node] = {}

        # Initialize the Graph with the Void Node
        self.void = self._get_or_create_node(VoidType)
        self.noret = self._get_or_create_node(NoReturn)

        # Primitives we generally don't want to scan recursively
        self.primitives = {int, str, float, bool, list, dict, set}

    def register(self, entity: Any, recursive: bool = False) -> Node:
        """
        Ingests a Python object (Class or Function) into the domain.

        Args:
            entity: The Class or Function to register.
            recursive: If True, recursively registers types found in signatures.
        """
        if inspect.isclass(entity):
            return self._register_class(entity, recursive)
        elif callable(entity):
            return self._register_function(entity, recursive)
        else:
            raise ValueError(f"Unsupported entity: {entity}")

    def _get_or_create_node(self, py_type: Type) -> Node:
        # Unwrap generic aliases (List[int] -> list)
        origin = getattr(py_type, "__origin__", py_type)

        if origin in self.nodes:
            return self.nodes[origin]

        name = getattr(origin, "__name__", str(origin))
        node = Node(py_type=origin, name=name)
        self.nodes[origin] = node
        return node

    def _register_class(self, cls: Type, recursive: bool) -> Node:
        node = self._get_or_create_node(cls)

        # Avoid re-scanning or scanning primitives
        if node.scanned or node.py_type in self.primitives:
            return node

        node.scanned = True

        # 1. Scan Members
        for name, member in inspect.getmembers(cls):
            if name.startswith("_") and name != "__init__":
                continue

            if inspect.isfunction(member) or inspect.ismethod(member):
                self._analyze_callable(member, owner=node, recursive=recursive)

        return node

    def _register_function(self, func: Callable, recursive: bool) -> Node:
        # Functions are edges from Void -> ReturnType
        # We don't return the "Function Node" (it doesn't exist),
        # we return the "Target Node" (the return type).
        edge = self._analyze_callable(func, owner=None, recursive=recursive)
        return edge.target if edge else self.void

    def _analyze_callable(
        self, func: Callable, owner: Optional[Node], recursive: bool
    ) -> Optional[Edge]:
        """
        Reflects on a callable, creates an Edge, and registers dependencies.
        """
        name = func.__name__

        # 1. Resolve Type Hints
        try:
            hints = get_type_hints(func)
        except Exception:
            return None

        # 2. Determine Source and Target
        if name == "__init__":
            # Constructor: Void -> Owner
            if not owner:
                return None
            source = self.void
            target = owner
            edge_name = owner.name  # Constructors are named after the class
        else:
            # Regular Method/Function

            # Infer target or use NoReturn
            rt = hints.pop("return", NoReturn)

            if rt is None or rt is type(None):
                target = self.noret
            else:
                target = self._get_or_create_node(rt)

            # Infer owner or use void
            if owner:
                source = owner
                edge_name = name
            else:
                source = self.void
                edge_name = name

        # 3. Analyze Parameters
        params: Dict[str, Node] = {}
        for param_name, param_type in hints.items():
            param_node = self._get_or_create_node(param_type)
            params[param_name] = param_node

            # Recursion: If we see a new type in params, register it?
            # Usually we want to know its structure to generate valid args.
            if recursive and not param_node.scanned:
                # We register it, but maybe as a class to populate its methods?
                if inspect.isclass(param_node.py_type):
                    self._register_class(param_node.py_type, recursive)

        # Recursion: Register the Return Type if new
        if recursive and not target.scanned:
            if inspect.isclass(target.py_type):
                self._register_class(target.py_type, recursive)

        # 4. Create and Attach Edge
        edge = Edge(name=edge_name, source=source, target=target, params=params)

        source.outgoing.append(edge)
        target.incoming.append(edge)

        return edge

    def get_node(self, py_type: Type) -> Node:
        origin = getattr(py_type, "__origin__", py_type)
        return self.nodes[origin]

    def get_entrypoints(self) -> List[Edge]:
        """Returns all edges starting from Void (Constructors/Functions)."""
        return self.void.outgoing

    def get_methods(self, py_type: Type) -> List[Edge]:
        """Returns all outgoing edges from a specific type."""
        return self.get_node(py_type).outgoing

    def get_producers(self, py_type: Type) -> List[Edge]:
        """Returns all edges leading TO a specific type."""
        return self.get_node(py_type).incoming

    def get_paths(self, start: Type, end: Type, max_depth: int = 5) -> List[List[Edge]]:
        """
        Finds all paths from Start Type to End Type within max_depth.
        Uses BFS.
        """
        start_node = self.get_node(start)
        end_node = self.get_node(end)
        if not start_node or not end_node:
            return []

        results = []
        queue = [(start_node, [])]  # (Current, Path)

        while queue:
            current, path = queue.pop(0)

            if current == end_node and path:
                results.append(path)

            if len(path) >= max_depth:
                continue

            for edge in current.outgoing:
                # Simple cycle prevention for this path
                if edge in path:
                    continue

                queue.append((edge.target, path + [edge]))

        return results
