# CodeContext Development Reference

AI agent reference for CodeContext development and maintenance.

---

## Quick Facts

```yaml
stack:
  python: 3.13
  workspace: UV
  tree_sitter: 0.25.2
  chromadb: 1.3.0+
  embeddings:
    - jinaai/jina-code-embeddings-0.5b (HuggingFace)
    - text-embedding-3-small (OpenAI)
  cli: Typer 0.20.0+
  config: Pydantic
  testing: pytest
  devices: [CPU, CUDA, MPS]

capabilities:
  - Hybrid Search: 8-stage pipeline (Translation → Expansion → BM25 → Vector → Fusion → GraphRAG → MMR → Diversity)
  - Translation: 200 languages (auto-detect, Korean/etc → English)
  - Relationships: 22 RelationType (11 bidirectional pairs)
  - Document-Code Linking: Automatic markdown → code reference extraction
  - Languages: Python, Kotlin, Java, JavaScript, TypeScript (AST parsing)
  - Optimizers: Language-specific AST optimization (Python, Java, Kotlin, TS)

concurrency:
  async_model: AsyncGenerator-based streaming
  indexing: Parallel batch processing (0 = auto: cpu_count//2, max 8)
  embedding: Async streaming with memory barriers
  storage: ChromaDB HTTP async client

error_handling:
  parsing: Partial AST recovery on syntax errors (50% threshold)
  timeout: 5s default (Kotlin: 10s, TypeScript: 7s)
  retry: Exponential backoff for external APIs (OpenAI, ChromaDB)
  validation: Pydantic with ConfigDict(extra="forbid")
```

---

## Architecture

### Design Patterns

- Provider: Pluggable embeddings/storage via entry points
- Factory: Dynamic provider discovery
- Strategy: Device (CPU/CUDA/MPS), sync (full/incremental)
- Streaming: AsyncGenerator-based chunk streaming
- Configuration: Pydantic validation

### Data Flow

```
Source Code + Documentation
  ↓ Tree-sitter AST Parsing
  ↓ Language Optimizers (Python/Java/Kotlin/TS)
  ↓ Code Objects + Relationships
  ↓ Document-Code Linking (automatic)
  ↓ NL Generator
  ↓ Embeddings (model-agnostic)
  ↓ ChromaDB (4 collections: code_objects, documents, relationships, state)
  ↓ Hybrid Search (8-stage)
  ↓ Results (snippets + metadata + relationships + doc links)
```

### Package Structure

```
packages/
├── codecontext-core/              # Interfaces, data models, RelationType (22)
├── codecontext-cli/               # CLI, orchestration, search, indexing
├── codecontext-embeddings-huggingface/   # Local embeddings
├── codecontext-embeddings-openai/        # OpenAI embeddings
├── codecontext-storage-chromadb/         # HTTP storage + bidirectional queries
└── codecontext-translation-nllb/         # Translation (200 languages)
```

### Key Components

**parsers/** - Multi-language AST parsing
- `languages/`: Python, Kotlin, Java, JS, TS, Markdown, Config
- `language_optimizers/`: python_optimizer.py, java_optimizer.py, kotlin_optimizer.py, typescript_optimizer.py
- `common/chunkers/`: Hierarchical chunking
- `common/nl_generator.py`: Natural language generation

**indexer/** - Batch processing
- `sync/full.py`: Full indexing with doc-code linking
- `sync/incremental.py`: Git-based incremental
- `extractor.py`: Relationship extraction
- `document_code_linker.py`: Automatic doc → code links
- `document_indexer.py`: Markdown indexing

**search/** - Hybrid retrieval (8-stage)
- `retriever.py`: SearchRetriever (orchestration)
- `query_expander.py`: QueryExpander (case variants, abbreviations, synonyms)
- `bm25_index.py`: BM25Index (keyword matching, field-weighted)
- `bm25_index_store.py`: BM25 cache persistence
- `fusion.py`: AdaptiveFusion (normalized linear combination)
- `graph_expander.py`: GraphExpander (1-hop PPR, GraphRAG)
- `mmr.py`: MMRReranker (diversity reranking)
- `diversity_filter.py`: FileDiversityFilter (max 2 chunks/file)

**config/**
- `schema.py`: SearchConfig, IndexingConfig, EmbeddingConfig (source of truth)
- `settings.py`: Config loading (env vars → .codecontext.yaml → ~/.codecontext/config.yaml)

**storage/**
- `factory.py`: Dynamic provider loading
- ChromaDB: Bidirectional queries (direction: "outgoing" | "incoming" | "both")

---

## Relationship System

### RelationType (22 types - 11 pairs)

**Code-to-Code: Forward (8)**
- CALLS, REFERENCES, EXTENDS, IMPLEMENTS, CONTAINS, IMPORTS, DEPENDS_ON, ANNOTATES

**Code-to-Code: Reverse (8)**
- CALLED_BY, REFERENCED_BY, EXTENDED_BY, IMPLEMENTED_BY, CONTAINED_BY, IMPORTED_BY, DEPENDED_BY, ANNOTATED_BY

**Document-to-Code (6 types - 3 pairs)**
- DOCUMENTS ↔ DOCUMENTED_BY
- MENTIONS ↔ MENTIONED_IN
- IMPLEMENTS_SPEC ↔ IMPLEMENTED_IN

### Graph Expansion

**1-hop relationship traversal with PPR scoring**:

```python
# packages/codecontext-cli/src/codecontext/search/graph_expander.py
class GraphExpander:
    def expand_results(initial_results: list[SearchResult], top_k: int) -> list[SearchResult]
```

**Features:**
- Research-based: SubgraphRAG, KG2RAG, HybridRAG (2024)
- PPR (Personalized PageRank) scoring
- Batch fetching (50x faster than individual)
- Relationship priorities (DOCUMENTS/DOCUMENTED_BY highest)

**Algorithm:**
1. Take Top-K initial results as seeds
2. Traverse 1-hop relationships
3. Compute PPR scores
4. Filter by threshold (0.3)
5. Merge with initial results
6. Re-rank by combined score

### Document-Code Linking

**Automatic link generation** during indexing:

```python
# packages/codecontext-cli/src/codecontext/indexer/document_code_linker.py
class DocumentCodeLinker:
    def extract_code_references(content: str) -> list[dict]
    def match_reference_to_objects(ref: dict, objects: list) -> list[tuple[id, confidence]]
    def create_relationships(documents: list) -> list[Relationship]
```

**Matching Strategies:**
- Exact name: 1.0
- File path: 0.9
- Class.method: 0.95
- Fuzzy partial: 0.7

**Integration:** Runs automatically after document indexing, creates bidirectional relationships, stored in ChromaDB.

---

## Configuration

### Hierarchy (Priority)

1. Environment variables (`CODECONTEXT_*`)
2. Project config (`.codecontext.yaml`)
3. User config (`~/.codecontext/config.yaml`)
4. Defaults (built-in)

### Critical Settings

**Hybrid Search:**
```yaml
search:
  bm25_weight: 0.4          # 40% keyword + 60% semantic
  mmr_lambda: 0.75          # 75% relevance + 25% diversity
  enable_graph_expansion: true
  graph_max_hops: 1
  graph_ppr_threshold: 0.4
  graph_score_weight: 0.3
  bm25_retrieval_multiplier: 5
  vector_retrieval_multiplier: 5
  max_chunks_per_file: 2
  diversity_preserve_top_n: 1
```

**Translation:**
```yaml
translation:
  enabled: true
  provider: nllb
  nllb:
    model_name: "facebook/nllb-200-distilled-600M"
    device: cpu              # cpu | cuda | mps
    batch_size: 16
    device_threads: 0        # 0 = auto
```

**Embedding Providers:**
```yaml
embeddings:
  provider: huggingface  # huggingface | openai
  huggingface:
    model_name: "jinaai/jina-code-embeddings-0.5b"
    device: auto  # auto | cpu | cuda | mps
    batch_size: null  # null = auto (cpu:16, mps:64, cuda:128)
    use_fp16: false
    max_length: 32768
  openai:
    model: "text-embedding-3-small"
    batch_size: 100
```

**Batch Size:** `null` → device auto (cpu:16, mps:64, cuda:128)

---

## Commands

### Environment

```bash
uv sync
uv run codecontext --help
source .venv/bin/activate
```

### ChromaDB

```bash
./scripts/chroma-cli.sh start
./scripts/chroma-cli.sh status
./scripts/chroma-cli.sh stop
./scripts/chroma-cli.sh logs -n 50
./scripts/chroma-cli.sh restart
```

### CLI

```bash
codecontext index
codecontext index --incremental
codecontext search "query"
codecontext search "query" --format json
codecontext status --verbose
```

### Testing

```bash
pytest
pytest --cov=codecontext
pytest -n auto
uv run pytest quality_tests/ -v -s
```

---

## Embedding Providers

### Architecture

**Interface:** `codecontext_core.interfaces.EmbeddingProvider`
- `initialize()` - Setup
- `embed_stream()` - AsyncGenerator streaming
- `get_batch_size()` - Optimal batch size
- `get_dimension()` - Embedding dimension
- `cleanup()` - Resource cleanup

**Plugin System:** Entry points in `pyproject.toml`
```toml
[project.entry-points."codecontext.embeddings"]
huggingface = "codecontext_embeddings_huggingface.provider:HuggingFaceEmbeddingProvider"
openai = "codecontext_embeddings_openai.provider:OpenAIEmbeddingProvider"
```

### HuggingFace Provider

**Dependencies:** `transformers`, `torch`
**Default Model:** jinaai/jina-code-embeddings-0.5b

**Device Strategies:**
- `CPUStrategy`: batch_size=16, threads=auto, jemalloc detection
- `CUDAStrategy`: batch_size=128, TF32=enabled, memory=0.8
- `MPSStrategy`: batch_size=64, memory=0.8

**Memory Management:**
- Automatic jemalloc detection and recommendations (CPU)
- Explicit memory barriers between chunks
- Aggressive cleanup every 5 batches
- Device-specific cache clearing (GPU/MPS)

**Critical: CPU Inference Optimization**
```bash
./scripts/setup-jemalloc.sh
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 codecontext index
# Peak memory: -34%, Average: -53%, Speed: up to 2.2x (PyTorch benchmarks)
```

See [docs/MEMORY_OPTIMIZATION.md](docs/MEMORY_OPTIMIZATION.md) for complete guide.

### OpenAI Provider

**Dependencies:** `openai` (async client)
**Models:** text-embedding-3-small, text-embedding-3-large, ada-002

**Features:**
- Adaptive rate limiting (RPM/TPM)
- Exponential backoff retry
- Cost tracking
- Native async API

### Adding Custom Provider

1. Create package `codecontext-embeddings-<name>`
2. Implement `EmbeddingProvider` interface
3. Add entry point in `pyproject.toml`
4. Add config to `EmbeddingConfig` in schema.py

---

## Development Workflow

### Adding New Language

1. Create parser: `parsers/languages/<language>.py`
2. Inherit from `BaseLanguageParser`
3. Optionally create optimizer: `parsers/language_optimizers/<language>_optimizer.py`
4. Register in factory: `parsers/factory.py`
5. Add tests: `tests/unit/test_<language>_parser.py`

### Adding Relationship Type

1. Update enum: `codecontext_core/models/core.py` (RelationType)
2. Add to reverse mapping: `codecontext_core/relationship_utils.py`
3. Update config: `codecontext_cli/config/schema.py` (max_related_per_type)
4. Create extractor: `indexer/extractor.py`
5. Add tests

### Modifying Search Algorithm

**8-Stage Pipeline:** `search/retriever.py` - SearchRetriever.search()
**BM25:** `search/bm25_index.py` - BM25Index
**BM25 Cache:** `search/bm25_index_store.py` - Persistence
**Vector:** `search/retriever.py` - _vector_search()
**Fusion:** `search/fusion.py` - AdaptiveFusion
**Graph Expansion:** `search/graph_expander.py` - GraphExpander
**MMR:** `search/mmr.py` - MMRReranker
**Diversity:** `search/diversity_filter.py` - FileDiversityFilter

---

## File Locations

**Core Logic:**
- Hybrid search: `packages/codecontext-cli/src/codecontext/search/retriever.py`
- Query expansion: `packages/codecontext-cli/src/codecontext/search/query_expander.py`
- BM25 index: `packages/codecontext-cli/src/codecontext/search/bm25_index.py`
- BM25 cache: `packages/codecontext-cli/src/codecontext/search/bm25_index_store.py`
- Fusion: `packages/codecontext-cli/src/codecontext/search/fusion.py`
- Graph expansion: `packages/codecontext-cli/src/codecontext/search/graph_expander.py`
- MMR reranking: `packages/codecontext-cli/src/codecontext/search/mmr.py`
- Diversity filter: `packages/codecontext-cli/src/codecontext/search/diversity_filter.py`
- Doc-code linking: `packages/codecontext-cli/src/codecontext/indexer/document_code_linker.py`
- Config schema: `packages/codecontext-cli/src/codecontext/config/schema.py`

**Data Models:**
- RelationType (22): `packages/codecontext-core/src/codecontext_core/models/core.py`
- Relationship utils: `packages/codecontext-core/src/codecontext_core/relationship_utils.py`
- Interfaces: `packages/codecontext-core/src/codecontext_core/interfaces.py`

**Storage:**
- ChromaDB provider: `packages/codecontext-storage-chromadb/src/codecontext_storage_chromadb/provider.py`
- Bidirectional queries: `get_relationships(entity_id, direction="both")`

---

## Code Standards

- Line Length: 100 (black, ruff)
- Type Hints: Required (mypy enforced)
- Naming:
  - Factory: `*Factory`
  - Provider: `*Provider`
  - Strategy: `*Strategy`
  - Expander: `*Expander`
  - Avoid: `*Util`, `*Helper`
- Patterns:
  - Models: dataclasses
  - Config: Pydantic
  - Interfaces: ABC
  - Providers: factory pattern
  - Graph expansion: GraphExpander

---

## Documentation

**User Guide:**
- [README.md](README.md) - Korean user guide with quick start
- [README.en.md](README.en.md) - English user guide

**Configuration:**
- [.codecontext.yaml.example](.codecontext.yaml.example) - Complete config reference

**Developer:**
- [CLAUDE.md](CLAUDE.md) - This file (AI agent reference)

---

**Version:** 0.5.0 | **License:** MIT | **Python:** 3.13
