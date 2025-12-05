# CodeContext Development Guide

## Stack
Python 3.13 | uv | tree-sitter 0.25.2 | Qdrant | Jina Code Embeddings (896-dim)

## Package Structure
```
codecontext/           # CLI (search, indexing, config)
codecontext_core/      # Models, BM25, tokenizer
codecontext_storage_qdrant/
codecontext_embeddings_huggingface/
```

---

## Search Pipeline

`retriever.py:27-115`

```
Query → Embedding (NL2CODE_QUERY)
     → Hybrid Search (RRF: 70% dense + 30% sparse)
     → Graph Expansion (1-hop, threshold 0.4)
     → Type/Name Boosting
     → Diversity Filter (max 2/file)
```

### Boosting Formula
`final_score = base * (1 + type_boost + name_boost) * score_weight`

Type boosts: class 0.12, method/function 0.10, enum 0.08, interface 0.06

---

## Models

### CodeObject (`models/core.py`)
```python
name, object_type, file_path, relative_path, start_line, end_line
content, language, checksum, deterministic_id
```

### Relationship (`models/core.py:361-405`)
```python
source_id, source_name, source_type, source_file, source_line
target_id, target_name, target_type, target_file, target_line
relation_type: RelationType
```

### RelationType (6 bidirectional pairs)
CALLS/CALLED_BY, EXTENDS/EXTENDED_BY, IMPLEMENTS/IMPLEMENTED_BY
REFERENCES/REFERENCED_BY, CONTAINS/CONTAINED_BY, IMPORTS/IMPORTED_BY

---

## Key Entry Points

| Task | File |
|------|------|
| Search | `retriever.py:27-115` |
| Hybrid search | `storage_qdrant/provider.py:267-335` |
| BM25F encoding | `core/bm25.py:30-82` |
| Relationship extraction | `indexer/extractor.py` |
| AST parsing | `parsers/` (per language) |
| Config | `config/schema.py` |
| Project registry | `utils/project_registry.py` |
| CLI context | `utils/cli_context.py` |

---

## Storage

Qdrant collection: `dense` (896-dim) + `sparse` (BM25F hash)

Relationships stored bidirectionally:
- `outgoing_relationships`, `incoming_relationships` in CodeObject payload
- `get_relationships(id)` merges both with dedup

---

## Config Defaults (`schema.py`)

```python
# Hybrid
prefetch_ratio_dense: 7.0
prefetch_ratio_sparse: 3.0

# BM25F field weights
name: 15, qualified_name: 12, signature: 10, docstring: 8, content: 6

# Diversity
max_chunks_per_file: 2
```

---

## Common Tasks

**Add relationship type**: `models/core.py` RelationType → `relationship_utils.py` REVERSE_MAP → `extractor.py`

**Add language parser**: `parsers/languages/` → `parsers/factory.py`

**Modify search ranking**: `retriever.py` boosting section (117-153)

**Modify formatter output**: `formatters/base_formatter.py` extract_relationships()

**Add CLI error type**: `core/exceptions.py` → handle in command files

---

## Exceptions

| Exception | Use |
|-----------|-----|
| `ProjectNotFoundError` | Project name/ID not found (with suggestions) |
| `EmptyQueryError` | Search query is empty |
| `SearchError` | Search operation failed |
| `IndexingError` | Indexing operation failed |
