# AST Node Type Reference

**Purpose**: Quick reference for Tree-sitter AST patterns across supported languages
**Extracted from**: Multi-Language Relationship Analysis (Feature 004)
**Last Updated**: 2025-10-12

This document provides AST node type patterns for relationship extraction (CALLS and REFERENCES) across all five supported languages.

---

## Kotlin

| Pattern | Node Types |
|---------|-----------|
| Method call | `call_expression` → `navigation_expression` → `simple_identifier` |
| Function call | `call_expression` → `simple_identifier` |
| Inheritance | `class_declaration` → `delegation_specifier` → `user_type` → `type_identifier` |

---

## Java

| Pattern | Node Types |
|---------|-----------|
| Method call | `method_invocation` → `identifier` . `identifier` |
| Static call | `method_invocation` → `identifier` . `identifier` |
| Inheritance | `superclass` → `type_identifier`, `super_interfaces` → `type_list` → `type_identifier` |

---

## TypeScript

| Pattern | Node Types |
|---------|-----------|
| Method call | `call_expression` → `member_expression` → `property_identifier` |
| Function call | `call_expression` → `identifier` |
| Inheritance | `class_heritage` → `extends_clause` / `implements_clause` → `type_identifier` |

---

## JavaScript

| Pattern | Node Types |
|---------|-----------|
| Method call | `call_expression` → `member_expression` → `property_identifier` |
| Function call | `call_expression` → `identifier` |
| Inheritance | `class_heritage` → `identifier` |

---

## Python

| Pattern | Node Types |
|---------|-----------|
| Method call | `call` → `attribute` → `identifier` |
| Function call | `call` → `identifier` |
| Inheritance | Regex-based (class definition parsing) |

---

## Usage Notes

- **Call Expressions**: All languages use `call_expression` except Java (`method_invocation`) and Python (`call`)
- **Member Access**: Patterns vary - `navigation_expression` (Kotlin), `member_expression` (TS/JS), `attribute` (Python), `identifier` (Java)
- **Inheritance**: Each language has unique AST structure for class/interface inheritance

## References

- Tree-sitter Documentation: https://tree-sitter.github.io/tree-sitter/
- Tree-sitter Kotlin Grammar: https://github.com/fwcd/tree-sitter-kotlin
- Tree-sitter Java Grammar: https://github.com/tree-sitter/tree-sitter-java
- Tree-sitter TypeScript Grammar: https://github.com/tree-sitter/tree-sitter-typescript
- Tree-sitter JavaScript Grammar: https://github.com/tree-sitter/tree-sitter-javascript
- Python Tree-sitter: https://github.com/tree-sitter/tree-sitter-python
