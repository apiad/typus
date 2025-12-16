from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class TypeNode:
    """
    Represents a Node in the Type Graph (a Python Type).
    It collects all known ways to produce an instance of this type.
    """
    py_type: type
    name: str

    # Edges pointing to this node (Ways to create this type)
    # This includes Constructors, Functions, and Fluent Methods.
    producers: list[Transition] = field(default_factory=list)

    def __hash__(self):
        return hash(self.py_type)

    def __eq__(self, other):
        if not isinstance(other, TypeNode):
            return NotImplemented
        return self.py_type == other.py_type

    def __repr__(self):
        return f"<TypeNode: {self.name}>"


@dataclass
class Transition:
    """
    Represents an Edge in the Type Graph (A Function or Method).
    It transforms a set of inputs (params) into a generic output (return_type).
    """
    name: str

    # The return type of this function
    return_type: TypeNode

    # Map of argument name -> TypeNode
    params: dict[str, TypeNode] = field(default_factory=dict)

    # Metadata for Method Chaining
    is_method: bool = False

    # If is_method is True, this is the 'self' type
    origin_type: TypeNode | None = None

    def __repr__(self):
        args = ", ".join(f"{k}: {v.name}" for k, v in self.params.items())
        prefix = f"{self.origin_type.name}." if self.origin_type else ""
        return f"<Transition: {prefix}{self.name}({args}) -> {self.return_type.name}>"
