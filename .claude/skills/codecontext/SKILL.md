---
name: codecontext
description: Search codebases using hybrid semantic+keyword search. Returns JSON with code snippets, 12 relationship types (CALLS/CALLED_BY, EXTENDS/EXTENDED_BY, IMPLEMENTS/IMPLEMENTED_BY, REFERENCES/REFERENCED_BY, CONTAINS/CONTAINED_BY, IMPORTS/IMPORTED_BY), and impact analysis. Use for "find authentication flow", "API discovery", "dependency tracking", "architecture exploration" in Python, Java, Kotlin, TypeScript, JavaScript. Requires Qdrant running.
allowed-tools: Bash
---

# CodeContext CLI

Hybrid search combining semantic embeddings, keyword matching, AST parsing, and relationship graphs.

## Commands

```bash
# JSON format (recommended for AI)
codecontext search "authentication flow" --format json
codecontext search "payment" --format json --expand signature
codecontext search "payment" --format json --expand content,relationships
codecontext search "payment" --format json --expand all

# Filters
codecontext search "query" --language python --limit 20
codecontext search "config" --file src/config.py --type code
codecontext search "docs" --type document
```

## Expand Options

- **Default:** name, type, file, lines, language, score
- `signature`: Function/method signature with type hints
- `snippet`: 1-3 lines code preview
- `content`: Full code body
- `relationships`: Callers, callees, contains (with counts)
- `complexity`: Cyclomatic complexity, LOC
- `impact`: Recursive callers count
- `all`: All above

**Multiple:** `--expand content,relationships,impact`

## Filter Options

- `--language LANG` / `-l LANG`: Filter by language (python, java, kotlin, typescript, javascript)
- `--file PATH`: Filter by exact file path
- `--type TYPE` / `-t TYPE`: Filter by type (code, document)
- `--limit N` / `-n N`: Max results (1-100, default 10)
- `--format FORMAT` / `-f FORMAT`: Output format (text, json)

## Query Best Practices

**Use natural language, not code syntax:**
- ✅ "authentication flow" "payment processing" "database connection"
- ✅ "REST API user creation" "OAuth JWT implementation"
- ❌ `def process_payment(` `class UserService`

**Rationale:** Semantic search understands domain terms better than syntax.

## Common Errors

**No index found:**
```
Error: No index found for project
```
**Solution:** Run `codecontext index` to create search index

---

**See examples.md:** Progressive discovery, usage patterns

**See reference.md:** JSON schema, 12 relationship types (6 bidirectional pairs), field descriptions
