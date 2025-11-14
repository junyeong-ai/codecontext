# CodeContext CLI Reference

Detailed reference documentation for CodeContext search JSON output, relationships, and configuration.

---

## JSON Output Structure

Complete schema for `--format json` output:

```json
{
  "results": [
    {
      "id": "chunk_unique_id",
      "score": 0.95,
      "rank": 1,
      "path": "src/services/payment.py",

      "location": {
        "file": "src/services/payment.py",
        "start_line": 42,
        "end_line": 68,
        "url": "src/services/payment.py:42-68"
      },

      "metadata": {
        "name": "process_payment",
        "type": "FUNCTION",
        "signature": "def process_payment(amount: Decimal, method: str) -> bool",
        "language": "python",
        "parent": "parent_chunk_id_or_null"
      },

      "structure": {
        "calls": ["validate_amount", "charge_card"],
        "references": ["PaymentGateway", "Transaction"],
        "complexity": {
          "cyclomatic": 5,
          "lines": 26,
          "nesting_depth": 3
        }
      },

      "snippet": {
        "essential": ["def process_payment(amount, method):", "return gateway.charge(...)"],
        "full": null
      },

      "scoring": {
        "bm25_score": 0.82,
        "vector_code_score": 0.91,
        "vector_desc_score": 0.88,
        "graph_score": 0.74,
        "final_score": 0.95
      },

      "relationships": {
        "callers": {
          "items": [
            {"name": "OrderService", "location": "chunk_id", "type": "direct_call"}
          ],
          "total_count": 12
        },
        "callees": {
          "items": [
            {"name": "PaymentGateway.charge", "location": "chunk_id", "external": false}
          ],
          "total_count": 5
        },
        "contains": {
          "items": [
            {"name": "validate_amount", "location": "chunk_id"}
          ],
          "total_count": 3
        },
        "similar": {
          "items": [],
          "total_count": 0
        }
      },

      "impact": {
        "recursive_callers": 25
      }
    }
  ],
  "total": 10,
  "query": "payment processing"
}
```

### Field Descriptions

**Top-level:**
- `results[]`: Array of search results, sorted by score (descending)
- `total`: Number of results returned
- `query`: Original search query

**Per-result:**
- `id`: Unique chunk identifier
- `score`: Final fused score (0.0-1.0)
- `rank`: Position in result list (1-indexed)
- `path`: Relative file path from project root

**location:**
- `file`: Same as `path` (backward compatibility)
- `start_line`: Starting line number (1-indexed)
- `end_line`: Ending line number (inclusive)
- `url`: Direct file reference format `path:start-end`

**metadata:**
- `name`: Function/class/method name
- `type`: Object type (FUNCTION, CLASS, METHOD, etc.)
- `signature`: Full function signature with types
- `language`: Programming language (python, java, kotlin, etc.)
- `parent`: Parent chunk ID (null for top-level)

**structure:**
- `calls[]`: Functions/methods called by this code
- `references[]`: Classes/variables referenced
- `complexity.cyclomatic`: McCabe cyclomatic complexity
- `complexity.lines`: Number of lines
- `complexity.nesting_depth`: Maximum nesting level

**snippet:**
- `essential[]`: Key lines (signature + return statements)
- `full`: Always null in current version

**scoring** (only with `--expand`):
- `bm25_score`: Keyword match score (unbounded, can be >1.0)
- `vector_code_score`: Code embedding similarity (0.0-1.0)
- `vector_desc_score`: Description embedding similarity (0.0-1.0)
- `graph_score`: Graph relationship relevance (0.0-1.0)
- `final_score`: Final fused score (0.0-1.0)

**relationships** (requires ChromaDB connection):
- `callers`: Code that calls this function
- `callees`: Functions called by this code
- `contains`: Nested code entities
- `similar`: Semantically similar code
- Each has `items[]` (sample, max 10) and `total_count` (complete count)

**impact:**
- `recursive_callers`: Total number of functions that directly or indirectly call this code

---

## Relationship Types (22 types - 11 bidirectional pairs)

### Code-to-Code Relationships (16 types - 8 pairs)

| Forward | Reverse | Description |
|---------|---------|-------------|
| CALLS | CALLED_BY | Function/method invocation |
| REFERENCES | REFERENCED_BY | Variable or type reference |
| EXTENDS | EXTENDED_BY | Class inheritance |
| IMPLEMENTS | IMPLEMENTED_BY | Interface implementation |
| CONTAINS | CONTAINED_BY | Structural containment (class contains method) |
| IMPORTS | IMPORTED_BY | Module import |
| DEPENDS_ON | DEPENDED_BY | General dependency |
| ANNOTATES | ANNOTATED_BY | Annotation/decorator application |

### Document-to-Code Relationships (6 types - 3 pairs)

| Forward | Reverse | Description |
|---------|---------|-------------|
| DOCUMENTS | DOCUMENTED_BY | Documentation documents code |
| MENTIONS | MENTIONED_IN | Documentation mentions code entity |
| IMPLEMENTS_SPEC | IMPLEMENTED_IN | Code implements specification |

**Usage in JSON:**
- Parse `relationships.*.total_count` for complete dependency counts
- Use `relationships.*.items[]` for sample references (limited to 10)
- GraphRAG prioritizes DOCUMENTS/DOCUMENTED_BY relationships

---

## Advanced Usage Patterns

### Dependency Analysis
```bash
codecontext search "PaymentService" --format json
```
**Parse:**
- `relationships.callers.total_count`: How many functions depend on this
- `impact.recursive_callers`: Total transitive dependencies

### Architecture Exploration
```bash
codecontext search "authentication" --format json --limit 30
```
**Analyze:**
- `impact.recursive_callers`: Find critical high-impact components
- `relationships.callees.total_count`: Identify complexity hotspots

### Debug Scoring Issues
```bash
codecontext search "database" --format json --expand
```
**Check:**
- `scoring.bm25_score` vs `scoring.vector_code_score`: Balance between keyword and semantic
- Low scores across all strategies: Query may be too vague

### Cross-Language Search
```bash
codecontext search "API client" --format json
```
**Returns:** TypeScript, Java, Python clients (language-agnostic semantic search)

### File-Specific Search
```bash
codecontext search "validation" --format json --file-pattern "src/services/**"
```
**Restricts:** Search to specific directories only

---

## Performance Tuning

### Default Configuration (`.codecontext.yaml`)

```yaml
search:
  # Fusion weights
  bm25_weight: 0.4                    # 40% keyword + 60% semantic

  # Diversity controls
  mmr_lambda: 0.75                    # 75% relevance + 25% diversity
  max_chunks_per_file: 2              # Prevent file clustering
  diversity_preserve_top_n: 1         # Always keep top result

  # Graph expansion
  enable_graph_expansion: true
  graph_max_hops: 1                   # 1-hop relationships only
  graph_ppr_threshold: 0.4            # PPR score threshold
  graph_score_weight: 0.3             # 30% graph context weight

  # Over-retrieval multipliers
  bm25_retrieval_multiplier: 5        # Retrieve 5x results for fusion
  vector_retrieval_multiplier: 5      # Retrieve 5x results for fusion

  # Query expansion
  max_query_variants: 5               # Limit expanded query variants
```

### Tuning Guidelines

**Increase keyword importance:**
```yaml
bm25_weight: 0.6  # 60% keyword + 40% semantic
```
Use when: Searching for specific function names, exact matches

**Increase semantic importance:**
```yaml
bm25_weight: 0.2  # 20% keyword + 80% semantic
```
Use when: Conceptual searches, cross-language queries

**Increase diversity:**
```yaml
mmr_lambda: 0.5  # 50% relevance + 50% diversity
```
Use when: Exploring codebase, avoiding redundant results

**Disable graph expansion:**
```yaml
enable_graph_expansion: false
```
Use when: Pure code search without documentation context

**Increase graph influence:**
```yaml
graph_score_weight: 0.5  # 50% graph context weight
```
Use when: Leveraging rich documentation and relationships

---

## Pipeline Details

### 1. Translation
- **Engine**: NLLB-200 (facebook/nllb-200-distilled-600M)
- **Languages**: 200+ languages supported
- **Auto-detection**: langdetect library
- **Performance**: ~300ms CPU, ~50ms GPU

### 2. Query Expansion
- **Case variants**: camelCase, snake_case, kebab-case
- **Abbreviations**: 40+ common mappings (ctx→context, db→database, etc.)
- **Synonyms**: get→fetch/retrieve, create→make/build, etc.
- **Limit**: Maximum 5 variants to prevent noise

### 3. BM25 Search
- **Algorithm**: BM25 with field weights
- **Over-retrieval**: `limit × 5` (e.g., 50 for top-10)
- **Field weights**: name > signature > content

### 4. Vector Search
- **Embeddings**: Dual (code + NL description)
- **Models**: jinaai/jina-code-embeddings-0.5b (default), OpenAI text-embedding-3-small
- **Over-retrieval**: `limit × 5`

### 5. Adaptive Fusion
- **Algorithm**: Normalized linear combination
- **Default**: 40% BM25 + 60% Vector
- **Normalization**: Min-max scaling to [0, 1]

### 6. Graph Expansion (GraphRAG)
- **Method**: Personalized PageRank (PPR)
- **Seeds**: Top-5 results from fusion
- **Hops**: 1-hop only (configurable up to 3)
- **Threshold**: 0.4 PPR score minimum
- **Priority**: DOCUMENTS/DOCUMENTED_BY relationships weighted highest

### 7. MMR Reranking
- **Algorithm**: Maximal Marginal Relevance
- **Lambda**: 0.75 (75% relevance, 25% diversity)
- **Purpose**: Reduce redundant similar results

### 8. Diversity Filtering
- **Rule**: Maximum 2 chunks per file
- **Preservation**: Always keeps top-1 result
- **Method**: In-place filtering by file path

---

## Error Reference

### Configuration Errors

**Missing .codecontext.yaml:**
```
ConfigurationError: No configuration file found
```
**Solution**: Create `.codecontext.yaml` from `.codecontext.yaml.example`

**Invalid YAML syntax:**
```
ConfigurationError: Invalid YAML in config file
```
**Solution**: Validate YAML syntax, check for tabs vs spaces

### Embedding Errors

**No embedding provider:**
```
EmbeddingError: No embedding provider configured
```
**Solution**: Configure `embeddings.provider` in `.codecontext.yaml`

**OpenAI API key missing:**
```
EmbeddingError: OPENAI_API_KEY environment variable not set
```
**Solution**: Set `export OPENAI_API_KEY=sk-...`

### Storage Errors

**ChromaDB not running:**
```
StorageError: Could not connect to ChromaDB at localhost:8000
```
**Solution**: Start ChromaDB with `chroma run --host localhost --port 8000`

**Collection not found:**
```
StorageError: Collection 'project_name' not found
```
**Solution**: Run `codecontext index` to create collection

### Search Errors

**Empty query:**
```
ValidationError: query_text cannot be empty
```
**Solution**: Provide non-empty search query

**Invalid limit:**
```
ValidationError: limit must be between 1 and 100
```
**Solution**: Use `--limit` between 1-100

---

**Last Updated:** 2025-11-14
**CodeContext Version:** 0.5.0
