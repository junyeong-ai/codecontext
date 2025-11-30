---
name: codecontext
description: Semantic code search with call graph analysis. Use when asking "where is X?", "what calls this function?", exploring unfamiliar code, or analyzing dependencies. Finds code by natural language with callers/callees/imports relationships.
allowed-tools: Bash
---

# codecontext

Hybrid semantic+keyword search with relationship tracking.

## search

```bash
codecontext search "<query>" [options]
```

| Option | Description |
|--------|-------------|
| `-f json` | JSON output |
| `-n <1-100>` | Result limit (default: 10) |
| `-l <lang>` | Filter: python, kotlin, java, typescript, javascript |
| `-t <type>` | Filter: code, document |
| `-e <fields>` | Expand: relationships, content, signature, snippet, complexity, impact, all |
| `-i <mode>` | Instruction: nl2code (default), qa, code2code |
| `--file <path>` | Filter by file/directory path |

## Examples

```bash
# Find by concept
codecontext search "authentication flow" -f json

# Get call graph (who calls this, what it calls)
codecontext search "PaymentService" -f json -e relationships

# Full code with metadata
codecontext search "config parser" -f json -e all -l python

# Q&A mode
codecontext search "how does caching work" -f json -i qa

# Filter by path
codecontext search "validation" -f json --file src/services
```

## Relationships (-e relationships)

| Type | Description |
|------|-------------|
| callers / callees | Function/method call graph |
| extends / extended_by | Class inheritance |
| implements / implemented_by | Interface implementation |
| imports / imported_by | Module dependencies |

## Index Management

```bash
codecontext status              # Check index status
codecontext index               # Full index
codecontext index -i            # Incremental update
codecontext list-projects       # List indexed projects
```

## Setup

Requires Qdrant:
```bash
docker compose -f docker-compose.qdrant.yml up -d
```

Or use embedded mode: `codecontext config edit` → set `mode = "embedded"`

## Troubleshooting

**"No index found"**: Run `codecontext index` first.
