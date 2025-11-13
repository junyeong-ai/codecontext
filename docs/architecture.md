# CodeContext Architecture

High-level system design and data flow.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Source Code                              │
│  Python, Kotlin, Java, JavaScript, TypeScript, Config, Markdown │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Tree-sitter AST Parsing                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ParserFactory → CodeParser/DocumentParser/ConfigParser  │   │
│  │  [packages/codecontext-cli/src/codecontext/parsers/]     │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│            Language-Specific Optimization                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  OptimizerFactory                                        │   │
│  │  ├─ PythonOptimizer:     Docstrings, type hints         │   │
│  │  ├─ JavaOptimizer:       Annotations, access modifiers  │   │
│  │  ├─ KotlinOptimizer:     Data classes, null safety      │   │
│  │  └─ TypeScriptOptimizer: Interfaces, decorators         │   │
│  │  [parsers/language_optimizers/]                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              Code Objects + Relationships                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  CodeObject (class, function, method, variable)          │   │
│  │  Relationship (CALLS, CONTAINS, REFERENCES)              │   │
│  │  [packages/codecontext-core/src/codecontext_core/]       │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Embedding Generation                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  EmbeddingProviderFactory                                │   │
│  │  ├─ HuggingFace: jina-code-0.5b (768-dim, local)            │   │
│  │  └─ OpenAI: text-embedding-3-* (API, paid)              │   │
│  │  [packages/codecontext-embeddings-*/]                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                ChromaDB Vector Storage                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  4 Collections per project:                              │   │
│  │  ├─ code_objects:   Code entities + embeddings           │   │
│  │  ├─ documents:      Documentation + embeddings           │   │
│  │  ├─ relationships:  Code relationships                   │   │
│  │  └─ state:          Indexing metadata                    │   │
│  │  [packages/codecontext-storage-chromadb/]                │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Hybrid Search System                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SearchRetriever                                         │   │
│  │  ├─ BM25 keyword search (weight: 0.4)                   │   │
│  │  ├─ Vector semantic search (weight: 0.6)                │   │
│  │  ├─ RRF fusion (k=60)                                   │   │
│  │  ├─ MMR re-ranking (λ=0.7)                              │   │
│  │  └─ Relationship expansion (graph traversal)            │   │
│  │  [packages/codecontext-cli/src/codecontext/search/]     │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Ranked Results                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FormatterFactory                                        │   │
│  │  ├─ TextFormatter:     Human-readable table             │   │
│  │  ├─ JSONFormatter:     AI-optimized (≤300 tokens)       │   │
│  │  ├─ ConfigFormatter:   Config file results              │   │
│  │  └─ DocumentFormatter: Documentation results            │   │
│  │  [packages/codecontext-cli/src/codecontext/formatters/] │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Parsers Layer

**Purpose**: Extract structured code objects and relationships from source files

**Components**:
- **ParserFactory**: Creates appropriate parser for file type
- **CodeParser**: Extracts code objects (Python, Kotlin, Java, JS, TS)
- **DocumentParser**: Extracts document nodes (Markdown)
- **ConfigParser**: Extracts config metadata (YAML, JSON, Properties)
- **Language Optimizers**: Post-process AST for better search quality

**Implementation**: [packages/codecontext-cli/src/codecontext/parsers/](../packages/codecontext-cli/src/codecontext/parsers/)

**Key files**:
- [interfaces.py](../packages/codecontext-cli/src/codecontext/parsers/interfaces.py) - Parser interfaces
- [factory.py](../packages/codecontext-cli/src/codecontext/parsers/factory.py) - Parser factory
- [languages/](../packages/codecontext-cli/src/codecontext/parsers/languages/) - Language implementations
- [language_optimizers/](../packages/codecontext-cli/src/codecontext/parsers/language_optimizers/) - AST optimization

**Optimizers**:
- **PythonOptimizer**: Docstrings, type hints, decorators
- **JavaOptimizer**: Annotations, access modifiers, Javadoc
- **KotlinOptimizer**: Data classes, null safety, KDoc
- **TypeScriptOptimizer**: Interfaces, decorators, JSDoc

**See also**: [Language Optimizers Guide](language-optimizers.md)

---

### 2. Indexer Layer

**Purpose**: Orchestrate parsing, embedding, and storage

**Components**:
- **FullIndexStrategy**: Complete codebase indexing
- **IncrementalIndexStrategy**: Git-based change detection
- **ChunkProcessor**: Memory-efficient streaming pipeline

**Implementation**: [packages/codecontext-cli/src/codecontext/indexer/](../packages/codecontext-cli/src/codecontext/indexer/)

**Key files**:
- [sync/full.py](../packages/codecontext-cli/src/codecontext/indexer/sync/full.py) - Full sync strategy
- [sync/incremental.py](../packages/codecontext-cli/src/codecontext/indexer/sync/incremental.py) - Incremental sync
- [strategy.py](../packages/codecontext-cli/src/codecontext/indexer/strategy.py) - Strategy interface

**Indexing flow**:
```
1. Discover files (git-based for incremental)
2. Parse files → CodeObject + Relationship
3. Generate embeddings (batch processing)
4. Store in ChromaDB (4 collections)
```

---

### 3. Embeddings Layer

**Purpose**: Generate vector embeddings for semantic search

**Providers**:

#### HuggingFace (Local, Free)
- **Model**: jinaai/jina-code-embeddings-0.5b
- **Dimension**: 768
- **Implementation**: [packages/codecontext-embeddings-huggingface/](../packages/codecontext-embeddings-huggingface/)

#### OpenAI (API, Paid)
- **Models**: text-embedding-3-small (1536-dim), text-embedding-3-large (3072-dim)
- **Implementation**: [packages/codecontext-embeddings-openai/](../packages/codecontext-embeddings-openai/)

**Plugin architecture**: Providers registered via entry points (no manual registration)

---

### 4. Storage Layer

**Purpose**: Persist code objects, embeddings, and relationships

**Provider**: ChromaDB (HTTP client)
- **Implementation**: [packages/codecontext-storage-chromadb/](../packages/codecontext-storage-chromadb/)
- **Collections**:
  1. `code_objects`: Code entities with embeddings
  2. `documents`: Documentation with embeddings
  3. `relationships`: Code relationships (CALLS, CONTAINS, REFERENCES)
  4. `state`: Indexing metadata (last commit, timestamps)

**Key operations**:
- `store_objects()`: Batch storage of code objects
- `store_relationships()`: Relationship graph storage
- `search()`: Vector similarity search
- `get_relationships()`: Relationship graph traversal

---

### 5. Search Layer

**Purpose**: Retrieve relevant code using hybrid search

**Components**:
- **BM25Index**: Keyword-based search with TF-IDF
- **SearchRetriever**: Hybrid search orchestration
- **ReciprocalRankFusion**: Result fusion (RRF)
- **MMRReranker**: Diversity-based re-ranking

**Implementation**: [packages/codecontext-cli/src/codecontext/search/](../packages/codecontext-cli/src/codecontext/search/)

**Hybrid Search Pipeline**:
```
1. Generate embedding for query
2. Parallel execution:
   a. BM25 keyword search (weight: 0.4)
   b. Vector semantic search (weight: 0.6)
3. RRF fusion (k=60)
4. MMR re-ranking (λ=0.7)
5. Relationship expansion (optional)
6. Format for output (Text/JSON)
```

**Key files**:
- [bm25_index.py](../packages/codecontext-cli/src/codecontext/search/bm25_index.py) - BM25 keyword search
- [retriever.py](../packages/codecontext-cli/src/codecontext/search/retriever.py) - Hybrid search orchestration
- [fusion.py](../packages/codecontext-cli/src/codecontext/search/fusion.py) - RRF fusion
- [mmr.py](../packages/codecontext-cli/src/codecontext/search/mmr.py) - MMR re-ranking

**See also**: [Hybrid Search Guide](hybrid-search.md)

---

### 6. Formatters Layer

**Purpose**: Format search results for different consumers

**Formatters**:
- **TextFormatter**: Human-readable table with syntax highlighting
- **JSONFormatter**: AI-optimized (≤300 tokens per result)
- **ConfigFormatter**: Configuration file results
- **DocumentFormatter**: Documentation results

**Implementation**: [packages/codecontext-cli/src/codecontext/formatters/](../packages/codecontext-cli/src/codecontext/formatters/)

---

## Data Models

### CodeObject

Represents a code entity:
- **Types**: class, function, method, variable, import, property, interface, enum
- **Metadata**: signature, docstring, complexity, nesting depth, LOC
- **Location**: file_path, start_line, end_line

**Definition**: [packages/codecontext-core/src/codecontext_core/models.py](../packages/codecontext-core/src/codecontext_core/models.py)

### Relationship

Represents a relationship between code objects:
- **Types**:
  - `CALLS`: Function/method invocation
  - `CONTAINS`: Hierarchical containment (class → method)
  - `REFERENCES`: Inheritance/interface implementation

**Definition**: [packages/codecontext-core/src/codecontext_core/models.py](../packages/codecontext-core/src/codecontext_core/models.py)

### DocumentNode

Represents a documentation node:
- **Types**: heading, paragraph, code_block, config_key
- **Metadata**: level, parent_id, config_key, env_references

**Definition**: [packages/codecontext-core/src/codecontext_core/models.py](../packages/codecontext-core/src/codecontext_core/models.py)

---

## Design Patterns

### 1. Provider Pattern

**Purpose**: Pluggable implementations for embeddings and storage

**Example**:
```python
# Embedding providers
EmbeddingProviderFactory.create("huggingface", config)
EmbeddingProviderFactory.create("openai", config)

# Storage providers
StorageProviderFactory.create("chromadb", config)
```

### 2. Factory Pattern

**Purpose**: Object creation with configuration

**Factories**:
- `ParserFactory`: Creates language-specific parsers
- `EmbeddingProviderFactory`: Creates embedding providers
- `StorageProviderFactory`: Creates storage providers
- `FormatterFactory`: Creates output formatters

### 3. Strategy Pattern

**Purpose**: Interchangeable algorithms

**Strategies**:
- `FullIndexStrategy`: Complete codebase indexing
- `IncrementalIndexStrategy`: Git-based change detection

### 4. Interface Segregation

**Purpose**: Separate interfaces for different parser types

**Interfaces**:
- `Parser`: Base interface (language detection, file support)
- `CodeParser`: Code extraction (Python, Kotlin, Java, JS, TS)
- `DocumentParser`: Document parsing (Markdown)
- `ConfigParser`: Config extraction (YAML, JSON, Properties)

---

## Configuration System

**Hierarchy** (highest to lowest priority):
1. Environment variables (`CODECONTEXT_*`)
2. Project config (`.codecontext.yaml`)
3. User config (`~/.codecontext/config.yaml`)
4. Built-in defaults

**Implementation**: [packages/codecontext-cli/src/codecontext/config/](../packages/codecontext-cli/src/codecontext/config/)

---

## Package Dependencies

```
codecontext-cli
├── depends on: codecontext-core
├── discovers: codecontext-embeddings-* (via entry points)
└── discovers: codecontext-storage-* (via entry points)

codecontext-embeddings-huggingface
└── depends on: codecontext-core

codecontext-embeddings-openai
└── depends on: codecontext-core

codecontext-storage-chromadb
└── depends on: codecontext-core
```

**Entry point discovery** (automatic plugin registration):
```toml
[project.entry-points."codecontext.embeddings"]
huggingface = "codecontext_embeddings_huggingface:HuggingFaceEmbeddingProvider"

[project.entry-points."codecontext.storage"]
chromadb = "codecontext_storage_chromadb:ChromaDBVectorStore"
```

---

## Performance Characteristics

| Operation | Target | Bottleneck |
|-----------|--------|------------|
| **Indexing (10K files)** | <10 min | AST parsing (50%), Embedding (20%) |
| **Search** | <500ms | Vector similarity (80%) |
| **Memory usage** | <2GB | Embedding model (1.2GB) |

**Optimizations**:
- Parallel AST parsing (4-8x speedup)
- GPU-accelerated embeddings (5-10x speedup)
- Batch processing (minimize I/O)
- Incremental indexing (10-100x faster for small changes)

---

## Additional Resources

- [Hybrid Search](hybrid-search.md) - Detailed guide to BM25 + Vector + RRF + MMR
- [Language Optimizers](language-optimizers.md) - AST optimization for better search
- [Performance Optimization](performance-optimization.md) - Indexing and search tuning
- [Custom Parsers Guide](guides/custom-parsers.md) - Adding new languages
- [Naming Conventions](naming-conventions.md) - Code standards
