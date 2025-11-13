# CodeContext Documentation

Documentation hub for CodeContext users, contributors, and maintainers.

---

## Navigation by Role

### For Users (CLI Usage)

Start with user-focused guides:

1. **[README.md](../README.md)** (한글) - Complete user guide with quick start
2. **[README.en.md](../README.en.md)** (English) - English translation
3. **[CLAUDE.md Commands](../CLAUDE.md#commands)** - Quick command reference

### For Contributors (Development)

Learn how to extend CodeContext:

1. **[CLAUDE.md](../CLAUDE.md)** - AI agent development reference
2. **[Adding a New Language](guides/adding-new-language.md)** - Step-by-step guide
3. **[Custom Parsers Guide](guides/custom-parsers.md)** - Parser development

### For Maintainers (Architecture)

Understand the system design:

1. **[Architecture Overview](architecture.md)** - System design and data flow
2. **[Hybrid Search](hybrid-search.md)** - BM25 + Vector + RRF + MMR
3. **[Language Optimizers](language-optimizers.md)** - AST optimization
4. **[Performance Optimization](performance-optimization.md)** - Tuning guide

---

## Core Documentation

### Architecture & Design

**[Architecture Overview](architecture.md)**
- System design and data flow
- Component details (parsers, indexer, search, storage)
- Design patterns (provider, factory, strategy)
- Package dependencies and plugin system

**[Hybrid Search](hybrid-search.md)** ⭐ NEW
- BM25 keyword search (weight: 0.4)
- Vector semantic search (weight: 0.6)
- RRF fusion algorithm (k=60)
- MMR re-ranking (λ=0.7)
- Configuration and tuning guide

**[Language Optimizers](language-optimizers.md)** ⭐ NEW
- Python optimizer (docstrings, type hints)
- Java optimizer (annotations, Javadoc)
- Kotlin optimizer (data classes, null safety)
- TypeScript optimizer (interfaces, decorators)
- Adding new optimizers

**[Performance Optimization](performance-optimization.md)** ⭐ NEW
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

---

## Guides (How-To)

**[Adding a New Language](guides/adding-new-language.md)**
- Step-by-step guide to add language support
- Creating parsers and optimizers
- Testing and validation

**[Embedding Configuration](guides/embedding-configuration.md)**
- HuggingFace vs OpenAI embeddings
- Device selection (CPU, MPS, CUDA)
- Batch size tuning

**[Custom Parsers](guides/custom-parsers.md)**
- Parser interface implementation
- AST extraction strategies
- Testing custom parsers

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

## Historical Documents

Archived planning documents from completed features:

**[Refactoring Notes](refactoring/)**
- Archived refactoring documentation for completed features

---

## Documentation Standards

### Active Documentation Criteria

Documents remain active if they meet **2 or more** of these criteria:

1. Provides actionable guidance (how-to, reference)
2. Reflects current implementation state
3. Contains unique information (not duplicated elsewhere)
4. Has a clear target audience (users/contributors/maintainers)

### Archive Criteria

Documents are archived (moved to `historical/` or `refactoring/`) when:

1. Planning phase is complete (feature implemented)
2. Content provides valuable context for future similar work
3. No duplication with active documentation

### Removal Criteria

Documents are removed when:

1. Information is incorrect or outdated (and not worth fixing)
2. Completely duplicates existing documentation
3. No historical value for future reference

### Review Cadence

**Trigger**: Quarterly or after major feature completion

**Ownership**: Feature maintainer or tech lead

**Checklist**:
- [ ] Verify active docs reflect current codebase
- [ ] Archive completed planning documents
- [ ] Remove obsolete documents
- [ ] Update docs/README.md with current structure
- [ ] Check for broken markdown links

---

## Quick Links

**Getting Started:**
- [README.md](../README.md) - User guide (한글)
- [README.en.md](../README.en.md) - User guide (English)
- [Quick Start](../README.md#quick-start)

**Development:**
- [CLAUDE.md](../CLAUDE.md) - AI agent reference
- [Contributing to Documentation](#contributing-to-documentation)

**Core Features:**
- [Hybrid Search](hybrid-search.md) - BM25 + Vector + RRF + MMR
- [Language Optimizers](language-optimizers.md) - AST optimization
- [Performance Optimization](performance-optimization.md) - Speed tuning

**System Design:**
- [Architecture](architecture.md) - System overview
- [Data Flow](architecture.md#data-flow)
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
   - Author (if not CodeContext Team)
   - Status (if planning document)

4. **Link from this README**:
   - Update the appropriate section above
   - Ensure bi-directional links

5. **Test all links**:
   - Ensure no broken references
   - Use relative paths (e.g., `guides/adding-new-language.md`)

---

**Last Updated**: 2025-11-10
**Maintained By**: CodeContext Team
