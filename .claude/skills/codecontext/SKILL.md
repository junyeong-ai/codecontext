---
name: codecontext
description: Search codebases using CodeContext's 8-stage hybrid search (Translation→Expansion→BM25→Vector→Fusion→GraphRAG→MMR→Diversity). Returns JSON with code snippets, 22 relationship types, impact analysis. Use for architecture exploration, API discovery, dependency tracking, implementation finding across Python, Java, Kotlin, TypeScript, JavaScript.
allowed-tools: Bash
---

# CodeContext CLI - Intelligent Code Search

Hybrid search engine that understands code semantics through AST parsing, vector embeddings, and relationship graphs.

## Quick Reference

```bash
# Check index status (run first)
codecontext status

# AI agent usage (JSON output)
codecontext search "authentication flow" --format json

# With filters
codecontext search "payment processing" --format json --language python --limit 20

# Debug scoring
codecontext search "database connection" --format json --expand
```

## Pre-flight Checks

**Before searching, verify index exists:**

```bash
codecontext status
```

**Expected output (index exists):**
```
✓ Index: 1854 code objects, 51 documents
✓ Storage: ChromaDB (localhost:8000)
✓ Embedding: jinaai/jina-code-embeddings-0.5b
```

**If index doesn't exist:**
```
✗ No index found
Run: codecontext index
```

**Common issues:**
- ChromaDB not running → Start ChromaDB first
- No index created → Run `codecontext index` (may take several minutes)
- Empty results → Index exists but query has no matches (try broader terms)

## 8-Stage Search Pipeline

CodeContext executes searches through an 8-stage pipeline:

1. **Translation** - Auto-detects and translates 200 languages to English
2. **Query Expansion** - Case variants, abbreviations (40+ mappings), synonyms
3. **BM25 Search** - Keyword matching with field weighting
4. **Vector Search** - Semantic similarity on code + descriptions
5. **Adaptive Fusion** - Combines BM25 (40%) + Vector (60%)
6. **Graph Expansion** - 1-hop PPR relationship traversal (GraphRAG)
7. **MMR Reranking** - Maximal Marginal Relevance (75% relevance, 25% diversity)
8. **Diversity Filtering** - Max 2 chunks per file

## CLI Options

### Required
- `query`: Natural language query (not code snippets)

### Optional
- `--format json`: Machine-readable output (required for AI agents)
- `--expand`: Include scoring breakdown (debug mode)
- `--language python|java|kotlin|javascript|typescript`: Filter by language
- `--file-pattern "src/**/*.py"`: Glob pattern for file filtering
- `--limit 20`: Number of results (1-100, default 10)
- `--project myproject`: Project name (auto-detected if omitted)

## Query Best Practices

### ✅ Effective Queries (Natural Language)
- "authentication flow"
- "payment processing logic"
- "database connection pooling"
- "REST API endpoints for users"
- "error handling in file upload"

### ❌ Ineffective Queries (Code Snippets)
- `def process_payment(`
- `class UserService`
- `import requests`

### Why Natural Language Works Better
1. **Query Expansion**: "processPayment" auto-expands to "process_payment", "process-payment"
2. **Translation**: Korean "결제 처리" auto-translates to "payment processing"
3. **Synonyms**: "get" expands to "fetch", "retrieve", "find"
4. **Semantic Search**: Vector embeddings understand intent, not just syntax

## Error Handling

All errors throw `CodeContextError` hierarchy:
- `ConfigurationError`: Invalid config (.codecontext.yaml)
- `EmbeddingError`: Embedding provider failure
- `SearchError`: Search execution failure
- `ParserError`: AST parsing failure
- `ValidationError`: Data validation failure

**JSON Output Guarantee**: In `--format json` mode, all logging is suppressed, ensuring clean JSON output even on errors.

## Result Interpretation

### Empty Results (`{"results": [], "total": 0}`)

**Possible causes:**

1. **No index exists**
   ```bash
   codecontext status  # Check if index exists
   ```
   **Solution**: Run `codecontext index`

2. **Index exists but no matches**
   - Query too specific (e.g., "processPayment" → try "payment processing")
   - Wrong language filter (e.g., --language python but code is in Java)
   - File pattern too restrictive
   **Solution**: Broaden query, remove filters, try synonyms

3. **Index is empty/incomplete**
   ```bash
   codecontext status --verbose  # Check object count
   ```
   **Solution**: Re-run `codecontext index` if count is 0

### Error Responses

**ChromaDB connection error:**
```
Error: Could not connect to ChromaDB at localhost:8000
```
**Solution**: Start ChromaDB (`chroma run --host localhost --port 8000`)

**No embedding provider:**
```
Error: Embedding provider required for search
```
**Solution**: Configure embeddings in `.codecontext.yaml`

---

**See reference.md for:**
- Complete JSON output schema
- 22 Relationship types (11 bidirectional pairs)
- Scoring breakdown details
- Performance tuning configuration
- Advanced usage patterns
