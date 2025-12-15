# Typus (`typus-dsl`)

**Strict typing for loose models.**

**Typus** is a Python library for defining Context-Free Grammars (CFGs) programmatically and compiling them into generation constraints for Large Language Models (LLMs).

It solves the **Backend Fragmentation** problem. Define your grammar *once* in Python, and compile it to **GBNF** (for Llama.cpp), **JSON Schema**, or **Regex**.

## 🚀 Features

  * **🐍 Pythonic DSL**: Define grammars using standard Python operators (`+`, `|`) and attribute access (`g.rule`).
  * **🛡️ Type-Safe Core**: A robust AST (`Symbol`, `Terminal`, `Sequence`) that prevents invalid states by construction.
  * **⚡ Regex Support**: First-class support for Regular Expressions using `g.regex()`.
  * **🏗️ High-Level Builders**: Helpers like `maybe()`, `some()`, and `any()` that handle recursion automatically.
  * **⚙️ GBNF Backend**: Out-of-the-box support for `llama.cpp` grammars.
  * **🔌 Plugin Architecture**: Easily register custom backends without modifying the core.

## 📦 Installation

```bash
pip install typus-dsl
# or with uv
uv add typus-dsl
```

## ⚡ Quick Start

### 1\. Basic: Semantic Versioning (SemVer)

Define a grammar to validate version strings like `v1.0.2` or `v2.10.0-rc1`.

```python
from typus import Grammar

g = Grammar()

# 1. Define atomic components with Regex
# "0" or "1-9" followed by digits (no leading zeros allowed)
g.digits = g.regex(r"(0|[1-9][0-9]*)")

# 2. Structure the version core: X.Y.Z
g.version_core = g.digits + "." + g.digits + "." + g.digits

# 3. Handle optional pre-release tag (e.g. "-alpha", "-rc1")
# maybe(x) -> x | ε
g.prerelease = g.maybe("-" + g.regex(r"[0-9A-Za-z-]+"))

# 4. Assemble the root rule
g.root = "v" + g.version_core + g.prerelease

print(g.compile("gbnf"))
```

### 2\. Advanced: Structured Function Calling

Define a grammar for an Agent tool call, like `search_tool(query="foo", limit=5)`.
This demonstrates handling **recursion** and **lists** automatically.

```python
from typus import Grammar

g = Grammar()

# 1. Define primitives
g.identifier = g.regex(r"[a-zA-Z_][a-zA-Z0-9_]*")
g.string_lit = '"' + g.regex(r'[^"]*') + '"'
g.number_lit = g.regex(r"[0-9]+")

# 2. Define a generic "Value" (String or Number)
g.value = g.string_lit | g.number_lit

# 3. Define a named argument: name=value
g.arg = g.identifier + "=" + g.value

# 4. Define the Argument List
# any(x, sep) -> (x (sep x)*)?  <-- Handles the recursion/separation logic
g.arg_list = g.any(g.arg, sep=", ")

# 5. Root: name(args)
g.root = g.identifier + "(" + g.arg_list + ")"

print(g.compile("gbnf"))
```

**Output (GBNF):**

```gbnf
root ::= [a-zA-Z_][a-zA-Z0-9_]* "(" ( _some_1 | "" ) ")"
identifier ::= [a-zA-Z_][a-zA-Z0-9_]*
value ::= ( string-lit | number-lit )
string-lit ::= "\"" [^"]* "\""
number-lit ::= [0-9]+
arg ::= identifier "=" value
_some_1 ::= arg | arg ", " _some_1
```

## 🏗 Architecture

Typus follows a strict **Layered Architecture** to ensure security and flexibility.

### Layer 1: The Core (`typus.core`)

The atomic units of the grammar. These are pure data structures.

  * **Terminal**: A string literal or regex.
  * **Sequence (`+`)**: `A + B`. Optimized to flatten automatically (`(A+B)+C` -> `A+B+C`).
  * **Choice (`|`)**: `A | B`.
  * **Epsilon**: The empty string ($\epsilon$).
  * **NonTerminal**: A reference to another rule (allowing recursion).

### Layer 2: The Engine (`typus.grammar`)

The `Grammar` class manages the state. It handles:

  * **Lazy Evaluation**: You can use `g.my_rule` before defining it.
  * **Recursion Management**: Generates unique anonymous rules for `some()` and `any()`.
  * **Backend Dispatch**: Delegates compilation to registered visitors.

### Layer 3: The Backends (`typus.backends`)

Typus is agnostic to the output format.

  * **GBNF**: Included by default. Handles escaping and rule naming conventions.
  * *(Planned)* **JSON Schema**: For OpenAI/Anthropic structured outputs.
  * *(Planned)* **Lark**: For validation and parsing.

## 🛣 Roadmap

  * [x] **v0.1**: Core AST, Operators, GBNF Backend.
  * [x] **v0.2**: Regex support (`g.regex("[0-9]+")`).
  * [ ] **v0.3**: JSON Schema Backend.
  * [ ] **v0.4**: `typus.data` (SQL generators & DB reflection).
  * [ ] **v0.5**: `typus.structure` (XML & Structure generators).
  * [ ] **v0.6**: `typus.functional` (Python & S-expression generators).

## 📄 License

MIT License. See [LICENSE](https://www.google.com/search?q=LICENSE) for details.
