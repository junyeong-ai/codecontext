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
│  │  ├─ HuggingFace: jina-code-0.5b (896-dim, local)        │   │
│  │  └─ OpenAI: text-embedding-3-* (API, paid)              │   │
│  │  [packages/codecontext-embeddings-*/]                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Qdrant Vector Storage                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Single collection per project:                          │   │
│  │  ├─ Named vectors: dense (896-dim), sparse (hash-based) │   │
│  │  ├─ Unified payload: code + documents + metadata        │   │
│  │  ├─ Relationships: stored in state (pickle)             │   │
│  │  └─ Remote mode (Docker) / Embedded mode                │   │
│  │  [packages/codecontext-storage-qdrant/]                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Hybrid Search System                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SearchRetriever (5-stage pipeline)                     │   │
│  │  ├─ 1. Query embedding                                  │   │
│  │  ├─ 2. Qdrant hybrid search (sparse + dense)           │   │
│  │  ├─ 3. Graph expansion (PPR, optional)                 │   │
│  │  ├─ 4. Type/Name boosting + score weight               │   │
│  │  └─ 5. Diversity filter & Top-K (max 2/file)           │   │
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

**Implementation**: [packages/codecontext-cli/src/codecontext/parsers/](../packages/codecontext-cli/src/codecontext/parsers/)

**Key files**:
- [interfaces.py](../packages/codecontext-cli/src/codecontext/parsers/interfaces.py) - Parser interfaces
- [factory.py](../packages/codecontext-cli/src/codecontext/parsers/factory.py) - Parser factory
- [languages/](../packages/codecontext-cli/src/codecontext/parsers/languages/) - Language implementations

---

### 2. Indexer Layer

**Purpose**: Orchestrate parsing, embedding, and storage

**Strategies**: FullIndexStrategy (complete) | IncrementalIndexStrategy (git-based)

**Flow**: Discover files → Parse (AST) → Embed (batch) → Store (Qdrant)

**Files**: [indexer/sync/full.py](../packages/codecontext-cli/src/codecontext/indexer/sync/full.py) | [sync/incremental.py](../packages/codecontext-cli/src/codecontext/indexer/sync/incremental.py)

---

### 3. Embeddings Layer

**Purpose**: Generate vector embeddings for semantic search

**Providers**:
- **HuggingFace**: jina-code-0.5b (896-dim, local) - [embeddings-huggingface/](../packages/codecontext-embeddings-huggingface/)
- **OpenAI**: text-embedding-3-* (1536/3072-dim, API) - [embeddings-openai/](../packages/codecontext-embeddings-openai/)

**Plugin**: Auto-registered via entry points

---

### 4. Storage Layer

**Provider**: Qdrant - [storage-qdrant/](../packages/codecontext-storage-qdrant/)

**Architecture**:
- Single collection: `dense` (896-dim) + `sparse` (hash-based BM25F)
- Unified payload: Code + documents + metadata
- Relationships: Stored in state (pickle)
- Modes: Remote (Docker) | Embedded

**Operations**: `add_code_objects()` | `add_relationships()` | `_search_hybrid()` (RRF/DBSF)

---

### 5. Search Layer

**5-Stage Pipeline**: [search/retriever.py](../packages/codecontext-cli/src/codecontext/search/retriever.py)

```
1. Query Embedding (896-dim)
2. Hybrid Search (RRF/DBSF, 70%:30% ratio)
3. Graph Expansion (1-hop PPR, optional)
4. Type/Name Boosting + Score Weight (additive boost × score weight)
5. Diversity (max 2/file, preserve top 1)
```

**Components**: SearchRetriever | GraphExpander | Formatters

**Details**: [Hybrid Search Guide](hybrid-search.md)

---

### 6. Formatters Layer

**Formatters**: Text (human) | JSON (AI, ≤300 tokens) | Config | Document

**Implementation**: [formatters/](../packages/codecontext-cli/src/codecontext/formatters/)

---

## Data Models

**CodeObject**: class | function | method | variable | interface | enum
- Metadata: signature, docstring, complexity, LOC
- Location: file_path, start_line, end_line

**Relationship**: CALLS | CONTAINS | REFERENCES | EXTENDS | IMPLEMENTS | IMPORTS (12 types, 6 bidirectional pairs)

**DocumentNode**: heading | paragraph | code_block | config_key

**Definition**: [core/models.py](../packages/codecontext-core/src/codecontext_core/models.py)

---

## Design Patterns

**Provider**: Pluggable embeddings/storage (HuggingFace, OpenAI, Qdrant)

**Factory**: Creates parsers, providers, formatters from config

**Strategy**: FullIndexStrategy | IncrementalIndexStrategy

**Interface Segregation**: Parser (base) | CodeParser | DocumentParser | ConfigParser

---

## Configuration System

**Priority**: Env vars (`CODECONTEXT_*`) > Project (`.codecontext.yaml`) > User (`~/.codecontext/config.yaml`) > Defaults

**Implementation**: [cli/config/](../packages/codecontext-cli/src/codecontext/config/)

---

## Package Dependencies

```
cli → core
embeddings-* → core (discovered via entry points)
storage-* → core (discovered via entry points)
```

**Entry points**: Auto-discover plugins (huggingface, openai, qdrant)

---

## Performance

| Operation | Target | Bottleneck |
|-----------|--------|------------|
| Indexing (10K files) | <10 min | AST parsing (50%), Embedding (20%) |
| Search | <500ms | Vector similarity (80%) |
| Memory | <2GB | Model (1.2GB) |

**Optimizations**: Parallel AST (4-8x) | GPU embeddings (5-10x) | Incremental (10-100x)

---

## Additional Resources

- [Hybrid Search](hybrid-search.md) - Detailed guide to hybrid search with GraphRAG
- [Performance Optimization](performance-optimization.md) - Indexing and search tuning
- [Naming Conventions](naming-conventions.md) - Code standards
