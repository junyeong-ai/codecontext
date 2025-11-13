# Hybrid Search System

Comprehensive guide to CodeContext's 8-stage hybrid search pipeline combining translation, keyword matching, semantic search, graph expansion, and diversity ranking.

---

## Overview

CodeContext implements an **8-stage search pipeline** that combines:
1. **Translation** - 200 languages auto-translation (Korean → English)
2. **Query Expansion** - Synonyms, abbreviations, case variants
3. **BM25 Search** - Keyword matching with TF-IDF ranking
4. **Vector Search** - Dense embeddings with cosine similarity
5. **Adaptive Fusion** - Normalized linear combination (NOT RRF)
6. **Graph Expansion** - 1-hop relationship traversal (GraphRAG, PPR)
7. **MMR Reranking** - Maximal Marginal Relevance for diversity
8. **File Diversity** - Prevent single-file monopolization

---

## Search Pipeline

```
User Query (Korean/English/etc)
    ↓
┌──────────────────────────────────────┐
│  Stage 1: Translation (Optional)     │
│  Auto-detect language → English      │
│  200 languages supported              │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│  Stage 2: Query Expansion            │
│  - Case variants (camelCase, etc)    │
│  - Abbreviations                      │
│  - Synonyms                           │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│  Parallel Retrieval (5x over)        │
├──────────────────────────────────────┤
│  [Stage 3: BM25]  [Stage 4: Vector]  │
│       ↓                    ↓          │
│   BM25 Results      Vector Results   │
└──────────────────────────────────────┘
    ↓                    ↓
    └──────────┬──────────┘
               ↓
    ┌──────────────────┐
    │  Stage 5: Fusion │
    │  (Adaptive)      │
    │  40% + 60%       │
    └──────────────────┘
               ↓
    ┌──────────────────┐
    │  Stage 6: Graph  │
    │  Expansion (PPR) │
    │  1-hop traversal │
    └──────────────────┘
               ↓
    ┌──────────────────┐
    │  Stage 7: MMR    │
    │  Reranking       │
    │  (λ=0.75)        │
    └──────────────────┘
               ↓
    ┌──────────────────┐
    │  Stage 8: File   │
    │  Diversity       │
    │  Max 2/file      │
    └──────────────────┘
               ↓
    ┌──────────────────┐
    │  Final Results   │
    │  (Top-K)         │
    └──────────────────┘
```

---

## Stage 1: Translation (v0.5.0)

### Implementation

**File:** `packages/codecontext-cli/src/codecontext/search/retriever.py:315-321`

**Provider:** NLLB (No Language Left Behind) - 200 languages

### Process

1. **Language Detection:**
   ```python
   lang = language_detector.detect(query_text)
   # Returns: ISO 639-3 code (e.g., 'kor', 'jpn', 'zho')
   ```

2. **Translation (if non-English):**
   ```python
   if lang != "en":
       query_text = translation_provider.translate_text(
           query_text, source_lang=lang, target_lang="en"
       )
   ```

3. **Example:**
   ```
   Input:  "드라이버 활성화 로직" (Korean)
   Detect: kor
   Translate: "driver activation logic" (English)
   ```

### Configuration

```yaml
translation:
  enabled: true              # Enable multilingual search
  provider: nllb
  nllb:
    model_name: "facebook/nllb-200-distilled-600M"
    device: cpu              # cpu | cuda | mps
    batch_size: 16
    device_threads: 0        # 0 = auto
    max_length: 512
```

---

## Stage 2: Query Expansion

### Implementation

**File:** `packages/codecontext-cli/src/codecontext/search/query_expander.py`

**Class:** `QueryExpander`

### Process

1. **Case Variants:**
   ```python
   Input:  "getUserById"
   Output: ["getUserById", "get_user_by_id", "getuserbyid"]
   ```

2. **Abbreviations:**
   ```python
   Input:  "auth"
   Output: ["auth", "authentication", "authorize"]
   ```

3. **Synonyms:**
   ```python
   Input:  "delete"
   Output: ["delete", "remove", "destroy"]
   ```

**Code Location:** `packages/codecontext-cli/src/codecontext/search/retriever.py:323`
```python
expanded_queries = self.query_expander.expand(query_text)
```

---

## Stage 3: BM25 Keyword Search

### Implementation

**File:** `packages/codecontext-cli/src/codecontext/search/bm25_index.py`

**Class:** `BM25Index`

**Algorithm:** BM25 (Best Matching 25) with field-based weighting

### BM25 Scoring Formula

```
score(D,Q) = Σ IDF(qi) × (f(qi,D) × (k1 + 1)) / (f(qi,D) + k1 × (1 - b + b × |D|/avgdl))

where:
- D: document
- Q: query
- qi: query term i
- f(qi,D): frequency of qi in D
- |D|: document length
- avgdl: average document length
- k1: term frequency saturation (1.5)
- b: length normalization (0.75)
```

### Field-Based Weighting

```python
field_weights = {
    "name": 3.0,           # Code object name (class, method, function)
    "qualified_name": 2.5, # Full qualified name
    "docstring": 2.0,      # Documentation strings
    "signature": 1.5,      # Function signatures
    "content": 1.0,        # Code content
}
```

### Over-Retrieval

**Code Location:** `packages/codecontext-cli/src/codecontext/search/retriever.py:325-330`
```python
bm25_limit = query.limit * self.config.search.bm25_retrieval_multiplier  # 5x
bm25_results = self.bm25_index.search_multi(
    queries=expanded_queries,
    limit=bm25_limit,
)
```

**Configuration:**
```yaml
search:
  bm25_retrieval_multiplier: 5   # Retrieve 5x more for better recall
```

---

## Stage 4: Vector Semantic Search

### Implementation

**File:** `packages/codecontext-cli/src/codecontext/search/retriever.py:332`

**Method:** `SearchRetriever._vector_search()`

**Embedding Model:** jinaai/jina-code-embeddings-0.5b (768-dimensional vectors)

### Similarity Metric

**Cosine Similarity:**
```
similarity(A,B) = (A · B) / (||A|| × ||B||)

Range: -1 to 1 (normalized to 0-1 in practice)
```

### Process

1. **Query Embedding:**
   ```python
   query_embedding = embedding_provider.embed_text(query)
   # Returns: 768-dim vector
   ```

2. **Vector Search:**
   ```python
   vector_limit = query.limit * self.config.search.vector_retrieval_multiplier  # 5x
   results = storage.search_objects(
       embedding=query_embedding,
       n_results=vector_limit,
   )
   ```

### Configuration

```yaml
search:
  vector_retrieval_multiplier: 5  # Retrieve 5x more for better recall

embeddings:
  huggingface:
    model_name: "jinaai/jina-code-embeddings-0.5b"
    device: auto
    batch_size: 64
```

---

## Stage 5: Adaptive Fusion

### Implementation

**File:** `packages/codecontext-cli/src/codecontext/search/fusion.py`

**Class:** `AdaptiveFusion`

**Algorithm:** Normalized Linear Combination (NOT RRF)

### Fusion Formula

```
fused_score = (bm25_weight × normalized_bm25) + ((1 - bm25_weight) × normalized_vector)

where:
- bm25_weight: 0.4 (default)
- normalized_bm25: Min-max normalized BM25 score [0, 1]
- normalized_vector: Min-max normalized vector score [0, 1]
```

### Process

**Code Location:** `packages/codecontext-cli/src/codecontext/search/retriever.py:334`
```python
fused = self._adaptive_fusion(bm25_results, vector_results, bm25_boost=None)
```

1. **Normalize Scores:**
   ```python
   # Min-max normalization to [0, 1]
   normalized_score = (score - min_score) / (max_score - min_score)
   ```

2. **Weighted Combination:**
   ```python
   final_score = (0.4 × bm25_normalized) + (0.6 × vector_normalized)
   ```

### Configuration

```yaml
search:
  bm25_weight: 0.4  # 40% keyword + 60% semantic
```

**Tuning Guide:**
- **High keyword precision (0.6-0.7):** Exact function/class names
- **Balanced (0.4 - default):** General queries
- **High semantic (0.2-0.3):** Conceptual queries

---

## Stage 6: Graph Expansion (GraphRAG)

### Implementation

**File:** `packages/codecontext-cli/src/codecontext/search/graph_expander.py`

**Class:** `GraphExpander`

**Algorithm:** 1-hop relationship traversal with Personalized PageRank (PPR)

### PPR Algorithm

```
PPR(v) = (1 - α) × Σ PPR(u) × P(u, v) / outdegree(u) + α × seed(v)

where:
- α: teleport probability (0.15)
- seed(v): 1 if v is seed node, 0 otherwise
- P(u, v): transition probability from u to v
```

### Process

**Code Location:** `packages/codecontext-cli/src/codecontext/search/retriever.py:336`
```python
expanded = self.graph_expander.expand_results(fused, top_k=5)
```

1. **Select Top-K Seeds:**
   ```python
   seeds = fused_results[:5]  # Top 5 as seeds
   ```

2. **Traverse 1-hop Relationships:**
   ```python
   for seed in seeds:
       neighbors = storage.get_relationships(seed.id, max_hops=1)
   ```

3. **Compute PPR Scores:**
   ```python
   ppr_score = compute_ppr(neighbor, seeds)
   ```

4. **Filter by Threshold:**
   ```python
   if ppr_score >= 0.4:
       expanded_results.append(neighbor)
   ```

5. **Combine Scores:**
   ```python
   final_score = (1 - graph_weight) × original_score + graph_weight × ppr_score
   # graph_weight = 0.3
   ```

### Configuration

```yaml
search:
  enable_graph_expansion: true
  graph_max_hops: 1              # 1-hop traversal
  graph_ppr_threshold: 0.4       # PPR threshold
  graph_score_weight: 0.3        # 30% graph + 70% original
```

**Relationship Priorities:**
- DOCUMENTS/DOCUMENTED_BY: Highest priority
- CALLS/CALLED_BY: High priority
- CONTAINS/CONTAINED_BY: Medium priority

---

## Stage 7: MMR Reranking

### Implementation

**File:** `packages/codecontext-cli/src/codecontext/search/mmr.py`

**Class:** `MMRReranker`

### MMR Formula

```
MMR = arg max[d ∈ R\S] [λ × Sim1(d, Q) - (1-λ) × max[d' ∈ S] Sim2(d, d')]

where:
- d: candidate document
- Q: query
- R: all results
- S: already selected documents
- λ: relevance vs diversity trade-off (0.75)
- Sim1: query-document similarity
- Sim2: document-document similarity
```

### Process

**Code Location:** `packages/codecontext-cli/src/codecontext/search/retriever.py:338`
```python
mmr_results = self._apply_mmr(expanded, query)
```

1. **Select Top Result:**
   - Pick document with highest query similarity

2. **Iterative Selection:**
   ```python
   for each remaining document d:
       relevance = similarity(d, query)
       diversity = max(similarity(d, selected) for selected in already_selected)

       mmr_score = (0.75 × relevance) - (0.25 × diversity)

       select document with highest mmr_score
   ```

### Configuration

```yaml
search:
  mmr_lambda: 0.75  # 75% relevance + 25% diversity
```

**Tuning Guide:**
- **λ = 1.0:** Pure relevance (no diversity)
- **λ = 0.75 (default):** Balanced
- **λ = 0.5:** Equal relevance and diversity
- **λ = 0.0:** Pure diversity

---

## Stage 8: File Diversity Filter

### Implementation

**File:** `packages/codecontext-cli/src/codecontext/search/diversity_filter.py`

**Class:** `FileDiversityFilter`

### Algorithm

```
For each file in results:
1. Keep top-N chunks (preserve_top_n = 1)
2. Limit remaining chunks to max_chunks_per_file - N
3. Remove excess chunks
```

### Process

**Code Location:** `packages/codecontext-cli/src/codecontext/search/retriever.py:340`
```python
self.diversity_filter.apply_inplace(mmr_results)
```

1. **Group by File:**
   ```python
   file_groups = group_by(results, key=lambda r: r.file_path)
   ```

2. **Preserve Top-1:**
   ```python
   for file, chunks in file_groups.items():
       preserved = chunks[:1]  # Always keep top-1
   ```

3. **Apply Limit:**
   ```python
   remaining = chunks[1:]
   max_remaining = max_chunks_per_file - 1
   final_chunks = preserved + remaining[:max_remaining]
   ```

### Configuration

```yaml
search:
  max_chunks_per_file: 2         # Max 2 chunks per file
  diversity_preserve_top_n: 1    # Always preserve top-1
```

**Example:**
```
File A: 5 chunks → Keep top 2 (1 preserved + 1 additional)
File B: 1 chunk  → Keep 1
File C: 3 chunks → Keep top 2
```

---

## Complete Configuration

```yaml
# Translation (v0.5.0)
translation:
  enabled: true
  provider: nllb
  nllb:
    model_name: "facebook/nllb-200-distilled-600M"
    device: cpu
    batch_size: 16

# Search Pipeline
search:
  default_limit: 10

  # Stage 5: Fusion
  bm25_weight: 0.4          # 40% keyword + 60% semantic

  # Stage 6: Graph Expansion
  enable_graph_expansion: true
  graph_max_hops: 1
  graph_ppr_threshold: 0.4
  graph_score_weight: 0.3

  # Stage 7: MMR
  mmr_lambda: 0.75          # 75% relevance + 25% diversity

  # Stage 8: File Diversity
  max_chunks_per_file: 2
  diversity_preserve_top_n: 1

  # Over-retrieval
  bm25_retrieval_multiplier: 5
  vector_retrieval_multiplier: 5
```

---

## Performance Characteristics

### Search Latency

**Components:**
1. **Translation:** ~100-200ms (if non-English)
2. **Query Expansion:** ~5-10ms
3. **BM25 Search:** ~50-100ms (in-memory index)
4. **Vector Search:** ~100-200ms (ChromaDB query)
5. **Fusion:** ~10-20ms
6. **Graph Expansion:** ~50-100ms (1-hop, batch fetch)
7. **MMR Reranking:** ~20-50ms
8. **File Diversity:** ~5-10ms

**Total:** <500ms for typical queries (including translation)

---

## Troubleshooting

### Poor Keyword Matching

**Symptom:** Missing results for exact function/class names

**Solution:**
```yaml
bm25_weight: 0.6  # Increase keyword weight
```

### Poor Semantic Understanding

**Symptom:** Missing results for conceptual queries

**Solution:**
```yaml
bm25_weight: 0.3  # Increase semantic weight
```

### Too Many Similar Results

**Symptom:** Top 10 results are all very similar

**Solution:**
```yaml
mmr_lambda: 0.5  # Increase diversity
```

### File Monopolization

**Symptom:** All results from same file

**Solution:**
```yaml
max_chunks_per_file: 1  # Stricter diversity
```

### Translation Not Working

**Symptom:** Korean queries not translating

**Debug:**
```bash
# Check translation provider enabled
grep "translation:" .codecontext.yaml

# Check logs
codecontext search "한국어 쿼리" | grep "Translated"
```

---

## Related Documentation

- [Architecture Overview](architecture.md)
- [Performance Optimization](performance-optimization.md)
- [Configuration Reference](../.codecontext.yaml.example)

---

**Last Updated:** 2025-01-12
