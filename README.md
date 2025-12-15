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

### 1. Basic Grammar with Regex

Define a grammar where a "User" has a name (Alice or Bob) and an ID (regex pattern).

```python
from typus import Grammar

g = Grammar()

# Define terminals and rules using Python operators
# | = Choice
# + = Sequence
g.name = "Alice" | "Bob"

# Use Regex for patterns
g.id   = "ID-" + g.regex(r"[0-9]{4}")

# Define the root rule
g.root = "User: " + g.name + " (" + g.id + ")"

# Compile to GBNF
print(g.compile("gbnf"))
```

### 2. Using High-Level Builders (`maybe`, `some`, `any`)

Typus handles the complex recursion logic for lists and optional items for you.

```python
from typus import Grammar

g = Grammar()

# 1. Optionality (?): maybe(x) -> x | ε
g.greeting = g.maybe("Hello, ")

# 2. One-or-More (+): some(x) -> x (sep x)*
g.numbers = g.some(g.regex(r"[0-9]+"), sep=",")

# 3. Zero-or-More (*): any(x) -> (x (sep x)*)?
g.json_list = "[" + g.any("value", sep=", ") + "]"

g.root = g.greeting + g.numbers + g.json_list

print(g.compile("gbnf"))
```

**Output (GBNF):**

```gbnf
root ::= ( "Hello, " | "" ) _some_1 "[" ( _some_2 | "" ) "]"
_some_1 ::= [0-9]+ | [0-9]+ "," _some_1
_some_2 ::= "value" | "value" ", " _some_2
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
