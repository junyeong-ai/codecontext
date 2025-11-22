# Hybrid Search System

CodeContext's search pipeline: Qdrant native hybrid search (sparse + dense vectors) with optional graph expansion and diversity ranking.

---

## Overview

**5-Stage Search Pipeline**:
1. **Query Embedding** - 896-dim vector (jina-code-embeddings-0.5b)
2. **Qdrant Hybrid Search** - BM25F sparse + Dense (semantic) with RRF fusion
3. **Graph Expansion** - Optional 1-hop PPR traversal
4. **Type/Name Boosting + Score Weight** - Additive boost × score weight (max 1.37x × 1.2x)
5. **Diversity Filter** - Max 2 chunks/file, preserve top N

---

## 5-Stage Search Pipeline

```
User Query (Natural Language)
    ↓
┌──────────────────────────────────────────┐
│  Stage 1: Query Embedding                │
│  embedding_provider.embed_text(query)    │
│  → 896-dim vector                        │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│  Stage 2: Qdrant Hybrid Search           │
├──────────────────────────────────────────┤
│  Sparse Vector (BM25F)                   │
│  • camelCase/snake_case/kebab-case split │
│  • SHA-256 hash (stable encoding)        │
│  • Field weighting (name=15, k1=1.2)     │
│  • Length normalization (b=0.75)         │
│                                           │
│  Dense Vector (Semantic Embeddings)      │
│  • jina-code-embeddings-0.5b (896-dim)   │
│  • Cosine similarity                     │
│                                           │
│  Fusion (Qdrant native RRF)              │
│  • k=60                                   │
│  • Dense prefetch 7x, Sparse 3x          │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│  Stage 3: Graph Expansion (Optional)     │
│  1-hop PPR traversal, threshold=0.4      │
│  Relationship types: CALLS, CONTAINS...  │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│  Stage 4: Type/Name Boosting + Weight    │
│  Type: class +0.12, method +0.10         │
│  Name match: exact +0.25, partial +0.15  │
│  Score weight: 0.1-1.2x (from metadata)  │
│  Final = base * (1 + boost) * weight     │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│  Stage 5: Diversity Filter & Top-K       │
│  Max 2 chunks per file                   │
│  Preserve top N results                  │
│  Return final results (limit=10)         │
└──────────────────────────────────────────┘
```

---

## Stage 1: Query Embedding

### Implementation

**File:** `packages/codecontext-cli/src/codecontext/search/retriever.py:33`

**Provider:** HuggingFace (jina-code-embeddings-0.5b) or OpenAI

### Process

```python
query_embedding = self.embedding_provider.embed_text(query)
# Returns: 896-dim vector (jina) or 1536-dim (OpenAI)
```

### Configuration

```toml
[embeddings.huggingface]
model_name = "jinaai/jina-code-embeddings-0.5b"
device = "auto"  # auto | cpu | cuda | mps
batch_size = null  # null = auto
```

---

## Stage 2: Qdrant Hybrid Search

Qdrant native hybrid search combining sparse (code-aware BM25) and dense (semantic) vectors.

### 2.1 Sparse Vector: Code-Aware Tokenization

**File:** `packages/codecontext-storage-qdrant/src/codecontext_storage_qdrant/provider.py:42-68,164-185`

**Pattern:** Hash-based sparse encoding with code-aware tokenization

#### Tokenization Process

```python
# Tokenize identifiers (camelCase/snake_case/kebab-case)
def _tokenize_identifier(identifier: str) -> tuple[str, ...]:
    # getUserById → (get, user, by, id)
    # get_user_by_id → (get, user, by, id)
    # user-profile-view → (user, profile, view)

# Hash-based stable encoding
def _stable_hash(token: str) -> int:
    return int(hashlib.sha256(token.encode()).hexdigest()[:8], 16)
```

#### BM25F Field Weighting

```python
name: 15           # Symbol name (highest priority)
qualified_name: 12 # Full path
signature: 10      # Function intent
docstring: 8       # Natural language descriptions
content: 6         # Implementation logic
filename: 4        # File name
file_path: 2       # Full path

k1: 1.2            # TF saturation
b: 0.75            # Document length normalization
avg_dl: 100.0      # Average document length
```

**Effect:** Length normalization prevents short documents from over-scoring.

### 2.2 Dense Vector: Semantic Embeddings

**Model:** jina-code-embeddings-0.5b (896-dim)
**Distance:** Cosine similarity
**Storage:** Named vector `dense` in Qdrant collection

### 2.3 Fusion Methods

**File:** `storage-qdrant/provider.py`

#### RRF (Reciprocal Rank Fusion)

```python
fusion_type = Fusion.RRF  # Default for RRF/DBSF modes
# Score: 1 / (k + rank), k=60
```

#### DBSF (Distribution-Based Score Fusion)

```python
fusion_type = Fusion.DBSF
# Normalizes scores by distribution
```

#### Weighted Fusion

```python
# Parallel dense/sparse queries
final_score = alpha * dense_score + (1-alpha) * sparse_score
# alpha=0.75: 75% dense + 25% sparse
```

### 2.4 Prefetch Configuration

```python
dense_prefetch = limit * 7.0   # 70% emphasis on semantic
sparse_prefetch = limit * 3.0  # 30% emphasis on keyword
```

### Configuration

```toml
[storage.qdrant]
mode = "remote"
url = "http://localhost:6333"
fusion_method = "rrf"  # rrf (default) | dbsf
```

---

## Stage 3: Graph Expansion

**File:** `search/graph_expander.py`

**Optional** 1-hop PPR traversal (threshold=0.4)

```toml
[search]
enable_graph_expansion = true
graph_max_hops = 1
graph_ppr_threshold = 0.4
```

---

## Stage 4: Type/Name Boosting + Score Weight

**File:** `search/retriever.py:111-153`

```python
# Type boost (additive: 0.0-0.12)
type_boost = {class: 0.12, method: 0.10, function: 0.10, ...}

# Name match boost (0.0-0.25)
if exact_name_match:
    boost += 0.25
elif name_tokens.issubset(query_tokens):
    boost += 0.15

# Score weight from metadata (0.1-1.2x)
weight = result.metadata.get("score_weight", 1.0)

# Final formula (applied together in one stage)
final_score = base * (1 + boost) * weight
```

**Key Design**:
- Type/name boost: Additive (0.0~0.37), max 1.37x
- Score weight: 0.1-1.2x based on token count (from metadata, calculated during indexing)
- Max combined: 1.37x × 1.2x = 1.644x

**Score weight calculation** (`core/quality.py`):
- < 10 tokens: 0.1-0.6 (filter low-information)
- 10-20 tokens: 0.5-1.0 (borderline)
- ≥ 20 tokens: 1.0-1.2 (normal, capped)

---

## Stage 5: Diversity Filter & Top-K

**File:** `search/retriever.py:119-140`

**Purpose:** Prevent file monopolization and select final results

```python
# Diversity filter
max_chunks_per_file = 2  # Max results from same file
diversity_preserve_top_n = 1  # Always preserve top result

# Top-K selection
return results[:limit]  # Default limit=10
```

**Configuration:**

```toml
[search]
default_limit = 10
max_chunks_per_file = 2
diversity_preserve_top_n = 1
```

---

## Complete Configuration

```toml
[storage.qdrant]
mode = "remote"
url = "http://localhost:6333"
fusion_method = "rrf"
prefetch_ratio_dense = 7.0
prefetch_ratio_sparse = 3.0

[indexing.field_weights]
name = 15
qualified_name = 12
signature = 10
docstring = 8
content = 6
filename = 4
file_path = 2
k1 = 1.2
b = 0.75
avg_dl = 100.0

[search]
default_limit = 10
enable_graph_expansion = true
graph_max_hops = 1
graph_ppr_threshold = 0.4
graph_score_weight = 0.3
max_chunks_per_file = 2
diversity_preserve_top_n = 1

[search.type_boosting]
class = 0.12
method = 0.10
function = 0.10
enum = 0.08
interface = 0.06
markdown = 0.07
config = 0.05
type = 0.04
field = 0.02
variable = 0.0
```

---

## Performance

| Stage | Latency |
|-------|---------|
| Query Embedding | ~10-20ms |
| Qdrant Hybrid Search | ~100-200ms |
| Graph Expansion | ~50-100ms (optional) |
| Type Boosting + Diversity | ~5-10ms |
| **Total** | **<400ms** |

---

## Troubleshooting

### Poor Keyword Matching

Increase field weights for qualified_name/name

### File Monopolization

Reduce max chunks per file:

```toml
[search]
max_chunks_per_file = 1  # Stricter diversity
diversity_preserve_top_n = 0  # No guaranteed preservations
```

---

**Last Updated:** 2025-11-19
