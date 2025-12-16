# Typus (`typus-dsl`)

**Strict typing for loose models.**

![PyPI - Version](https://img.shields.io/pypi/v/typus-dsl)
![PyPi - Python Version](https://img.shields.io/pypi/pyversions/typus-dsl)
![Github - Open Issues](https://img.shields.io/github/issues-raw/apiad/typus)
![PyPi - Downloads (Monthly)](https://img.shields.io/pypi/dm/typus-dsl)
![Github - Commits](https://img.shields.io/github/commit-activity/m/apiad/typus)

**Typus** is a Python library for **Grammar Constrained Decoding (GCD)**.

Large Language Models (LLMs) are powerful but chaotic. They hallucinate invalid syntax, invent non-existent functions, and break JSON formatting. **Typus** solves this by generating strict **Context-Free Grammars (CFGs)** that constrain the LLM's token generation process.

Instead of writing complex EBNF strings by hand, you use a **Pythonic Interface** to define your constraints—from simple regex patterns to entire semantic domains.

## 🌟 Why Typus?

  * **🚫 No More Hallucinations**: Force the LLM to output *exactly* what you need (valid JSON, SQL, Python, or CSV).
  * **🐍 Python-First**: Define grammars using standard Python operators (`|`, `+`) and types (`dataclasses`, `int`, `str`).
  * **🧩 Universal**: Define your grammar *once* and compile it for any target:
      * **Llama.cpp / GGUF**: Compiles to GBNF.
      * **Validators**: Compiles to Regex.
      * **Parsers**: Compiles to Lark (EBNF).
  * **🧠 Cognitive Control**: Use **Templates** to force "Chain of Thought" reasoning before actions.

## 📦 Installation

```bash
pip install typus-dsl
# or with uv
uv add typus-dsl
```

## 🏗 The Stack: From Low-Level to High-Level

Typus offers three layers of abstraction depending on your needs.

### 1. The Grammar DSL (Low Level)

*For when you need pixel-perfect control over every character.*

Use standard Python operators to define rules.

```python
from typus import Grammar

g = Grammar()
# Define primitives
g.digit = g.regex(r"[0-9]")
g.number = g.digit + g.maybe("." + g.some(g.digit))

# Define structure
g.coordinate = "(" + g.number + ", " + g.number + ")"
g.root = "Point: " + g.coordinate
```

### 2. Templates (Mid Level)

*For when you want to structure the LLM's thought process.*

Mix static prompts with dynamic grammar constraints using Python f-string syntax.

```python
# Force the model to think before it answers
g.root = g.template(
    "Thought: {thought}\nAction: {action}",
    thought=g.some(g.regex(r"[^\n]+"), sep="\n"),
    action="SEARCH" | "CALCULATE"
)
```

### 3. The Domain Engine (High Level)

*For when you want to project a "Problem Domain" into a target language.*

Define your types and functions in Python, and Typus generates the grammar that enforces them in JSON, SQL, HTML, or Python.

```python
# Define the domain once
@dataclass
class User: ...

# Generate a JSON Schema grammar
Json().build(Domain(User))

# Generate a SQL Query grammar
SQLQuery().build(Domain(User))
```

## ⚡ Use Cases & Examples

### Use Case 1: Semantic Versioning (Regex Validation)

Ensure the model generates valid SemVer strings like `v1.0.2` or `v2.10.0-rc1`.

```python
from typus import Grammar

g = Grammar()
g.digits = g.regex(r"(0|[1-9][0-9]*)")
g.version = g.digits + "." + g.digits + "." + g.digits
g.tag = g.maybe("-" + g.regex(r"[0-9a-z-]+"))

g.root = "v" + g.version + g.tag

print(g.compile("gbnf"))
```

### Use Case 2: Structured Reasoning (Templates)

Force an Agent to provide a reasoning trace before emitting a final JSON answer. This prevents "blind" answering.

```python
from typus import Grammar

g = Grammar()
g.thought = g.some(g.regex(r"[^\n]+"), sep="\n")
g.json_blob = g.regex(r"\{.*\}") # Simplified JSON regex

# The template constrains the structure
g.root = g.template(
    "Reasoning:\n{steps}\n\nFinal Answer:\n{result}",
    steps=g.thought,
    result=g.json_blob
)
```

### Use Case 3: Type-Safe JSON Generation (Domain + JSON)

Define your data schema using Pydantic or Dataclasses, and get a grammar that guarantees the output matches that schema.

```python
from dataclasses import dataclass
from typing import List
from typus.languages import Json

@dataclass
class Product:
    id: int
    name: str
    tags: List[str]

# Generate a strict GBNF grammar for this schema
# The LLM cannot miss a comma, quote, or bracket.
g = Json().build(Product)
print(g.compile("gbnf"))
```

### Use Case 4: Safe SQL Querying (Domain + SQL)

Expose a specific set of "Allowed Queries" to the LLM. The grammar ensures the model can *only* generate valid `SELECT` statements for your specific table columns, preventing SQL Injection and hallucinations.

```python
from typus import Grammar, Domain
from typus.languages import SQLQuery

# 1. Define the Schema
@dataclass
class Users:
    name: str
    age: int

# 2. Define allowed access patterns
def get_users_by_name(name: str) -> Users: ...
def get_users_by_age(min_age: int) -> Users: ...

# 3. Build the Grammar
# The LLM can generate: "SELECT name, age FROM Users WHERE name = '...'"
# It CANNOT generate: "DROP TABLE Users"
g = SQLQuery().build(
    Domain(Users, entrypoints=[get_users_by_name, get_users_by_age])
)
```

## 🔧 Supported Backends

Typus is compiler-agnostic. You build the AST once, and export it to:

| Backend | Command | Use Case |
| :--- | :--- | :--- |
| **GBNF** | `g.compile("gbnf")` | **Llama.cpp**, `llama-python`, local GGUF models. |
| **Regex** | `g.compile("regex", max_depth=3)` | **Guidance**, **Outlines**, Standard API validators. Supports bounded recursion. |
| **Lark** | `g.compile("lark")` | **Python Parsing**. Use Typus to parse the string the LLM just generated. |
| **JSON Schema** | *(Via `Json` language)* | **OpenAI / Anthropic** structured output APIs. |

## 🛣 Roadmap

  * [x] **v0.1**: Core DSL (`Sequence`, `Choice`, `Regex`), GBNF Compiler.
  * [x] **v0.2**: Templates (`g.template`), Regex Compiler with unrolling.
  * [ ] **v0.3**: Lark Compiler (Round-trip parsing).
  * [ ] **v0.4**: The Domain Engine (`typus.domain` reflection).
  * [ ] **v0.5**: Language Strategies (`Json`, `SQLQuery`, `Markdown`, `Python`).

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.