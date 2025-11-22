---
name: codecontext
description: Search codebases using CodeContext's hybrid search (70% semantic + 30% keyword). Architecture-first ranking (Class > Interface, LOC-based). Returns JSON with code snippets, 12 relationship types (6 bidirectional pairs CALLS/CALLED_BY, EXTENDS/EXTENDED_BY, IMPLEMENTS/IMPLEMENTED_BY, REFERENCES/REFERENCED_BY, CONTAINS/CONTAINED_BY, IMPORTS/IMPORTED_BY), impact analysis. Use for "find authentication flow", "API discovery", "dependency tracking", "architecture exploration" in Python, Java, Kotlin, TypeScript, JavaScript.
allowed-tools: Bash
---

# CodeContext CLI

Hybrid search combining semantic embeddings, AST parsing, and relationship graphs.

## Commands

```bash
# JSON format (recommended for AI)
codecontext search "authentication flow" --format=json
codecontext search "payment" --format=json --expand=signature
codecontext search "payment" --format=json --expand=content,relationships
codecontext search "payment" --format=json --expand=all

# Filters
codecontext search "query" --language python --limit 20
```

## Expand Options

- **Default:** name, type, file, lines, language, score
- `signature`: Function/method signature
- `snippet`: 1-3 lines code snippet
- `content`: Full code body
- `relationships`: Callers, callees, contains
- `complexity`: Cyclomatic complexity, LOC
- `impact`: Recursive callers count
- `all`: All above

**Multiple:** `--expand=content,relationships`

## Query Tips

Use natural language, not code syntax:
- ✅ "authentication flow" "payment processing" "database connection"
- ❌ `def process_payment(` `class UserService`

## Common Errors

**No index:**
```
Error: No index found
```
→ Run `codecontext index`

**Qdrant error:**
```
Error: Could not connect to Qdrant
```
→ Start: `docker compose -f docker-compose.qdrant.yml up -d`

---

**See examples.md:** Progressive discovery, usage patterns

**See reference.md:** JSON schema, 12 relationship types (6 bidirectional pairs), field descriptions
