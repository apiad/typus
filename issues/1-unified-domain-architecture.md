---
number: 1
title: "Unified domain architecture"
state: open
labels:
---

# 🗺️ Roadmap: The Unified Domain Architecture

**Goal**: Enable users to define a "Semantic Schema" (Types + Functions) in pure Python and automatically compile it into strictly constrained grammars for various target languages (Python, SQL, HTML, Markdown).

**Core Concept**: `Grammar = Domain(Semantics) + Language(Syntax)`

-----

## 🏗️ Milestone 1: The Semantic Core (`typus.domain`)

We need a reflection engine that normalizes Python's complex type system into a clean graph of **Types** and **Functions**.

### 1.1. The Canonical Models

Define the intermediate representation (IR) that decouples Python implementation details from the domain logic.

  * **Task**: Create `typus.domain.models`.
  * **Models**:
      * `TypeSpec`: Represents a data holder (Noun).
          * Attributes: `name`, `fields: Dict[str, TypeSpec]`.
      * `FunctionSpec`: Represents an action (Verb).
          * Attributes: `name`, `params: Dict[str, TypeSpec]`, `return_type: TypeSpec`.
  * **Hints**: Support recursive types (e.g., `Node` containing `List[Node]`) using forward references or lazy evaluation.

### 1.2. The Reflector

The engine that traverses Python objects.

  * **Task**: Create `typus.domain.Domain`.
  * **API Design**:
    ```python
    class Domain:
        def __init__(self, *definitions, root: List[Callable] = None): ...
    ```
  * **Implementation Details**:
      * **Inspection**: Use `inspect.get_annotations()` (Python 3.10+) for reliable type hint extraction.
      * **Unwrapping**: Automatically unwrap `List[T]`, `Optional[T]`, and `Union[A, B]` into understandable flags on `TypeSpec`.
      * **Auto-Discovery**: If a Function is registered, automatically register its argument types and return types recursively.

-----

## 🔌 Milestone 2: The Language Protocol (`typus.languages.base`)

Define the contract for syntax generation. This layer translates the semantic graph into AST nodes (`Symbols`).

  * **Task**: Define the `Language` Protocol.
  * **API Design**:
    ```python
    class Language(Protocol):
        def render_primitive(self, py_type: type, grammar: Grammar) -> Symbol: ...
        def render_type(self, spec: TypeSpec, field_rules: Dict[str, Symbol]) -> Symbol: ...
        def render_call(self, spec: FunctionSpec, arg_rules: List[Symbol]) -> Symbol: ...
    ```
  * **The Builder**: Create `Language.build(domain: Domain) -> Grammar`.
      * This is the orchestration logic. It iterates over `domain.types`, calls `render_type`, handles the recursion cache (to prevent infinite loops on recursive types), and finally constructs the `root` rule.

-----

## 🐍 Milestone 3: Functional Domains (Code Generation)

Targets: **Python**, **JavaScript**, **Lisp**.
**Use Case**: Agent Tool Use, Code Synthesis.

### 3.1. Python Generator (`typus.languages.python`)

  * **Logic**:
      * **Types**: Render as constructor calls. `User(name="...", age=10)`.
      * **Functions**: Render as function calls. `find_user(id=5)`.
  * **Constraints**:
      * The grammar must *only* allow calls to registered functions.
      * It must enforce correct argument names (keyword arguments are safer for LLMs).
  * **Implementation Hint**: Use `g.sequence()` with explicit strings like `name=` to enforce kwargs.

### 3.2. JavaScript/JSON Generator

  * **Logic**:
      * **Types**: Render as JSON Objects or `new Class()`.
      * **Functions**: `func(...)`.
  * **Differentiation**: Demonstrates swapping syntax (`User(...)` vs `new User(...)`) without changing the Domain.

-----

## 📄 Milestone 4: Structural Domains (Document Generation)

Targets: **HTML**, **Markdown**, **LaTeX**.
**Use Case**: Report generation, UI mocking, Structured Output.

### 4.1. Heuristic Layout Engine

Instead of rigid schemas, use "Convention over Configuration".

  * **Heuristics**:
      * Field named `title` -\> **Header** / **Section**.
      * Field type `List[str]` -\> **List** (Bullet/Numbered).
      * Field type `str` (long) -\> **Paragraph**.
      * Other fields -\> **Concatenated sequence**.

### 4.2. Markdown Generator (`typus.languages.markdown`)

  * **Configuration**: `Markdown(bullet="-", section_style="#")`.
  * **State**: Needs to track `nesting_depth` to render `#` vs `##` vs `###`.
  * **Implementation Hint**: The `render_type` method should check `spec.fields` for the existence of `title` and increment an internal counter before rendering children.

### 4.3. HTML Generator (`typus.languages.html`)

  * **Logic**:
      * Map Class Name -\> Tag Name (`class Button` -\> `<button>`).
      * Map Primitives -\> Attributes (`label: str` -\> `label="..."`).
      * Map Complex Types -\> Children.
  * **Constraint**: The grammar ensures the closing tag matches the opening tag (`<User>...</User>`).

-----

## 🗄️ Milestone 5: Data Domains (Query Generation)

Targets: **SQL**, **Cypher**, **GraphQL**.
**Use Case**: RAG, Text-to-SQL.

### 5.1. SQL Generator (`typus.languages.sql`)

Instead of generating code *to create* objects, we generate code *to query* objects.

  * **Logic**:
      * **Function as Query**: A function `get_users_by_city(city: str) -> List[User]` becomes a specific SQL template.
      * **Return Type** -\> `FROM Table`.
      * **Function Name** -\> `SELECT` (or `DELETE`/`UPDATE` via prefixes).
      * **Arguments** -\> `WHERE` clauses.
  * **Argument Mapping**:
      * Exact match: `arg_name` matches column -\> `col = value`.
      * Operators: `min_age` -\> `age >= value`.
  * **Security**: This is the key selling point. The LLM strictly cannot generate `DROP TABLE` if no function maps to it.

-----

## 🛠 Implementation Guide & Hints

### Hint 1: Handling Recursion

When the `Language.build()` method encounters a type `Node` that refers to `Node`, it must not infinitely recurse.

  * **Solution**: Create the `NonTerminal("Node")` *before* generating its body. Store it in a cache `visited_types: Dict[Type, NonTerminal]`.

### Hint 2: Primitives are Language-Dependent

  * **Python**: `True` / `False` (Capitalized).
  * **JS/SQL**: `true` / `false` (Lowercase).
  * **Markdown**: "Yes" / "No" (Context dependent).
  * *Design*: The `Language` protocol must have granular primitive methods (`render_bool`, `render_int`, `render_str`).

### Hint 3: Lists are Tricky

A `List[T]` isn't just `T+`. It has syntax.

  * **Python**: `[` + `T` + ` ,  ` + `T` ... + `]`.
  * **Markdown**: ` -  ` + `T` + `\n` + ` -  ` + `T`.
  * **SQL**: `List` usually implies the result set, not syntax (unless `IN (...)`).
  * *Design*: Add `render_list(item_rule: Symbol)` to the Protocol.

### Hint 4: "Entrypoints" (The Root)

The `Domain` has a `root` parameter.

  * **Code Domain**: Root is usually a Choice of all top-level functions (`expr ::= func_a | func_b`).
  * **Document Domain**: Root is usually a specific container type (`Report`).
  * **SQL Domain**: Root is a Choice of all query templates.

### Proposed Timeline

1.  **v0.4**: `typus.domain` (Reflector) + `typus.languages.python`.
2.  **v0.5**: Structural Generators (Markdown/HTML) with Heuristics.
3.  **v0.6**: Data Generators (SQL) + "Prefix Inference" (min_, max_).