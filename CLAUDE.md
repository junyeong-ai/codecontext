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

**File:** `codecontext/search/retriever.py:27-115`

```
1. Query Embedding (line 35-37)
   → InstructionType.NL2CODE_QUERY → 896-dim

2. Hybrid Search (line 39-41, codecontext_storage_qdrant/provider.py:267-335)
   → RRF (k=60): 70% semantic + 30% keyword
   → Prefetch: dense 7.0x, sparse 3.0x

3. Graph Expansion (line 108-109, optional)
   → 1-hop PPR, threshold 0.4

4. Type/Name Boosting + Score Weight (line 111, 117-153)
   → Additive boost: type (0.0-0.12) + name match (0.0-0.25)
   → Score weight: 0.1-1.2x (token-based, from metadata)
   → Formula: base * (1 + boost) * score_weight

5. Diversity Filter (line 113, 155-182)
   → Max 2 chunks/file, preserve top 1
```

---

## Configuration

**File:** `codecontext/config/schema.py`

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

**File:** `codecontext_storage_qdrant/provider.py`

- Collection: `dense` (896-dim) + `sparse` (hash-based BM25F)
- BM25F: `codecontext_core/bm25.py` (field weights + length norm)
- Tokenizer: `codecontext_core/tokenizer.py` (camelCase/snake_case → cached `@lru_cache`)
- Sparse: SHA-256 hash for stable indices (bm25.py:10-12)
- RRF: Combines dense/sparse with k=60 (provider.py:303)

---

## Relationship Types

**File:** `codecontext_core/models/core.py:59-71`

12 types (6 bidirectional pairs):
- CALLS/CALLED_BY, EXTENDS/EXTENDED_BY, IMPLEMENTS/IMPLEMENTED_BY
- REFERENCES/REFERENCED_BY, CONTAINS/CONTAINED_BY, IMPORTS/IMPORTED_BY

Used in graph expansion (1-hop PPR, threshold 0.4).

---

## Instruction-Based Embeddings

**File:** `codecontext_core/interfaces.py:9-17`

6 types: NL2CODE_QUERY/PASSAGE, CODE2CODE_QUERY/PASSAGE, QA_QUERY/PASSAGE

Enables asymmetric query/passage encoding (Jina Code Embeddings).
Pooling: last-token | Padding: left

---

## Package Structure

```
codecontext/                         # CLI package (search, indexing, config)
codecontext_core/                    # Core interfaces, models, BM25, tokenizer
codecontext_storage_qdrant/          # Qdrant hybrid search
codecontext_embeddings_huggingface/  # HuggingFace embeddings
codecontext_embeddings_openai/       # OpenAI embeddings
codecontext_translation_nllb/        # NLLB translation
```

---

## Key Files

| Component | File:Line |
|-----------|-----------|
| Search pipeline | codecontext/search/retriever.py:27-115 |
| Type/Name boosting | codecontext/search/retriever.py:117-153 |
| Diversity filter | codecontext/search/retriever.py:155-182 |
| Score weight | codecontext_core/quality.py:4-36 |
| Config schema | codecontext/config/schema.py:1-210 |
| BM25F encoder | codecontext_core/bm25.py:15-82 |
| Hybrid search | codecontext_storage_qdrant/provider.py:267-335 |
| Tokenizer | codecontext_core/tokenizer.py:42-162 |
| RelationType | codecontext_core/models/core.py:59-71 |
| InstructionType | codecontext_core/interfaces.py:9-22 |

---

## Debugging Entry Points

**Search:**
1. Embedding: retriever.py:35-37
2. Hybrid: retriever.py:39-41
3. Graph: retriever.py:108-109
4. Boosting: retriever.py:117-153
5. Diversity: retriever.py:155-182

**Storage:**
1. Connection: provider.py:109-141
2. BM25F: bm25.py:30-68 (encode), 70-81 (encode_query)
3. Hybrid: provider.py:267-335 (_search_hybrid)
4. Prefetch: provider.py:300-301 (dense/sparse ratios)

**Indexing:**
1. Full: codecontext/indexer/sync/full.py
2. Incremental: codecontext/indexer/sync/incremental.py
3. Relationships: codecontext/indexer/extractor.py

---

**Version:** 0.5.0 | MIT | Python 3.13
