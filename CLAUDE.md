# CodeContext AI Development Reference

---

## Stack

```yaml
python: 3.13 | uv | tree_sitter: 0.25.2
qdrant: Remote (Docker)
embeddings: jinaai/jina-code-embeddings-0.5b (896-dim)
config: Pydantic
```

---

## Search Pipeline (5 Stages)

**File:** `cli/search/retriever.py:27-115`

```
1. Query Embedding (line 35)
   → InstructionType.NL2CODE_QUERY → 896-dim

2. Hybrid Search (line 39, storage-qdrant/provider.py:342-410)
   → RRF (k=60): 70% semantic + 30% keyword
   → Prefetch: dense 7.0x, sparse 3.0x

3. Graph Expansion (line 108, optional)
   → 1-hop PPR, threshold 0.4

4. Type/Name Boosting + Score Weight (line 111, 117-153)
   → Additive boost: type (0.0-0.12) + name match (0.0-0.25)
   → Score weight: 0.1-1.2x (token-based, from metadata)
   → Formula: base * (1 + boost) * score_weight

5. Diversity Filter (line 113)
   → Max 2 chunks/file, preserve top 1
```

---

## Configuration

**File:** `cli/config/schema.py`

### Type Boosting (Additive)

```python
class_: 0.12 | method: 0.10 | function: 0.10 | enum: 0.08
interface: 0.06 | markdown: 0.07 | config: 0.05 | type: 0.04
field: 0.02 | variable: 0.0
```

### Field Weights (BM25F)

```python
name: 15 | qualified_name: 12 | signature: 10 | docstring: 8
content: 6 | filename: 4 | file_path: 2
k1: 1.2 | b: 0.75 | avg_dl: 100.0
```

### Hybrid Search

```python
fusion_method: "rrf"
prefetch_ratio_dense: 7.0   # 70%
prefetch_ratio_sparse: 3.0  # 30%
```

### Diversity

```python
max_chunks_per_file: 2
diversity_preserve_top_n: 1
```

---

## Storage (Qdrant)

**File:** `storage-qdrant/provider.py`

- Collection: `dense` (896-dim) + `sparse` (hash-based BM25F)
- BM25F: `core/bm25.py` (field weights + length norm)
- Tokenizer: `core/tokenizer.py` (camelCase/snake_case → cached `@lru_cache`)
- Sparse: SHA-256 hash for stable indices
- RRF: Combines dense/sparse with k=60

---

## Relationship Types

**File:** `core/models/core.py:59-72`

12 types (6 bidirectional pairs):
- CALLS/CALLED_BY, EXTENDS/EXTENDED_BY, IMPLEMENTS/IMPLEMENTED_BY
- REFERENCES/REFERENCED_BY, CONTAINS/CONTAINED_BY, IMPORTS/IMPORTED_BY

Used in graph expansion (1-hop PPR, threshold 0.4).

---

## Instruction-Based Embeddings

**File:** `embeddings-huggingface/provider.py:60-90`

7 types: NL2CODE_QUERY/PASSAGE, CODE2CODE_QUERY/PASSAGE, QA_QUERY/PASSAGE, DOCUMENT_PASSAGE

Enables asymmetric semantic matching.

---

## Package Structure

```
cli/            # Search, indexing, config, parsers
core/           # Interfaces, models
storage-qdrant/ # Qdrant hybrid search
embeddings-*    # HuggingFace, OpenAI
```

---

## Key Files

| Component | File:Line |
|-----------|-----------|
| Search pipeline | cli/search/retriever.py:27-115 |
| Type/Name boosting | cli/search/retriever.py:111-148 |
| Score weight | core/quality.py |
| Config schema | cli/config/schema.py:80-165 |
| BM25F encoder | core/bm25.py |
| Hybrid search | storage-qdrant/provider.py:342-410 |
| Tokenizer | core/tokenizer.py |
| RelationType | core/models/core.py:59-138 |

---

## Debugging Entry Points

**Search:**
1. Embedding: retriever.py:33
2. Hybrid: retriever.py:34
3. Graph: retriever.py:102
4. Boosting: retriever.py:111-148
5. Diversity: retriever.py:150-177

**Storage:**
1. Connection: provider.py:109-141
2. BM25F: bm25.py:30-68
3. Hybrid: provider.py:342-410

**Indexing:**
1. Full: indexer/sync/full.py
2. Incremental: indexer/sync/incremental.py
3. Relationships: indexer/extractor.py

---

**Version:** 0.5.0 | MIT | Python 3.13
