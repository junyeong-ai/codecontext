# CodeContext Documentation

Documentation hub for CodeContext users, contributors, and maintainers.

---

## Navigation by Role

### For Users (CLI Usage)

Start with user-focused guides:

1. **[README.md](../README.md)** (한글) - User guide with quick start
2. **[README.en.md](../README.en.md)** (English) - English translation

### For AI Agents (Development)

Learn the codebase and contribute:

1. **[CLAUDE.md](../CLAUDE.md)** - AI agent development reference
   - Stack and architecture
   - Critical implementation points
   - Debugging entry points
   - Configuration reference

2. **[LoRA Fine-Tuning](lora-fine-tuning.md)** - LoRA adapter integration
   - Configuration and validation
   - Loading logic and error handling
   - Testing and debugging
   - Common patterns

### For Developers (Architecture)

Understand the system design:

1. **[Architecture Overview](architecture.md)** - System design and data flow
2. **[Hybrid Search](hybrid-search.md)** - Qdrant Hybrid (Sparse + Dense) + GraphRAG
3. **[Performance Optimization](performance-optimization.md)** - Tuning guide

---

## Core Documentation

### Architecture & Design

**[Architecture Overview](architecture.md)**
- System design and data flow
- Component details (parsers, indexer, search, storage)
- Design patterns (provider, factory, strategy)
- Package dependencies and plugin system

**[Hybrid Search](hybrid-search.md)**
- Qdrant native hybrid search (sparse + dense vectors)
- 5-stage pipeline: embedding → hybrid → graph → boosting+weight → diversity
- Code-aware tokenization (camelCase/snake_case/kebab-case)
- RRF/DBSF fusion with 70%:30% semantic:keyword ratio
- Type/name boosting (additive) with score weight filtering

**[Performance Optimization](performance-optimization.md)**
- Parallel AST parsing (4-8x speedup)
- GPU-accelerated embeddings (3-10x speedup)
- xxHash checksums (50-60x faster)
- Text pre-sorting (20-30% faster)
- Configuration presets and benchmarking

**[Naming Conventions](naming-conventions.md)**
- Factory pattern (`*Factory`)
- Provider pattern (`*Provider`)
- Strategy pattern (`*Strategy`)
- Code organization standards

**[LoRA Fine-Tuning](lora-fine-tuning.md)**
- Configuration and validation
- PEFT integration and graceful degradation
- Directory structure requirements
- Testing, debugging, and common patterns

---

## Guides (How-To)

**[Embedding Configuration](guides/embedding-configuration.md)**
- HuggingFace vs OpenAI embeddings
- Device selection (CPU, MPS, CUDA)
- Batch size tuning

**[Performance Tuning](guides/performance-tuning.md)**
- Qdrant optimization
- Memory optimization
- Search performance tuning
- Configuration examples

---

## References (Technical Deep-Dives)

**[AST Patterns Reference](references/ast-patterns.md)**
- Tree-sitter node types for all supported languages
- Common AST patterns
- Language-specific quirks

**[API Reference](references/api-reference.md)**
- Core interfaces (Parser, CodeObject, Relationship)
- Provider APIs (embedding, storage)
- Configuration schemas

**[Path Filtering Performance](references/path-filtering-research.md)**
- Performance analysis of path filtering strategies
- Benchmark results

---

## Documentation Standards

### Active Documentation Criteria

Documents remain active if they meet **2 or more** of these criteria:

1. Provides actionable guidance (how-to, reference)
2. Reflects current implementation state
3. Contains unique information (not duplicated elsewhere)
4. Has a clear target audience (users/AI agents/developers)

### Archive Criteria

Documents are archived when:

1. Planning phase is complete (feature implemented)
2. Content provides valuable context for future similar work
3. No duplication with active documentation

### Removal Criteria

Documents are removed when:

1. Information is incorrect or outdated (and not worth fixing)
2. Completely duplicates existing documentation
3. No historical value for future reference

---

## Quick Links

**Getting Started:**
- [README.md](../README.md) - User guide (한글)
- [README.en.md](../README.en.md) - User guide (English)
- [Quick Start](../README.md#빠른-시작-3단계-5분)

**Development:**
- [CLAUDE.md](../CLAUDE.md) - AI agent reference

**Core Features:**
- [Hybrid Search](hybrid-search.md) - Qdrant Hybrid + GraphRAG
- [Performance Optimization](performance-optimization.md) - Qdrant + GPU tuning

**System Design:**
- [Architecture](architecture.md) - System overview
- [Data Flow](architecture.md#system-overview)
- [Design Patterns](architecture.md#design-patterns)

---

## Contributing to Documentation

When adding new documentation:

1. **Choose the right category**:
   - `guides/` - How-to guides for specific tasks
   - `references/` - Technical analysis and deep-dives
   - Root level - High-level overviews (architecture, hybrid-search, etc.)

2. **Follow markdown standards**:
   - Use headings for structure
   - Include code blocks with syntax highlighting
   - Add tables for comparisons
   - Use diagrams for complex flows

3. **Include metadata**:
   - Date (at bottom: "Last Updated: YYYY-MM-DD")
   - Status (if applicable)

4. **Link from this README**:
   - Update the appropriate section above
   - Ensure bi-directional links

5. **Test all links**:
   - Ensure no broken references
   - Use relative paths (e.g., `guides/performance-tuning.md`)

---

**Last Updated**: 2025-11-16
**Maintained By**: CodeContext Team
