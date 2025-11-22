# codecontext-core

Core interfaces and data models for CodeContext - Intelligent Code Search Engine.

## Overview

This package provides the foundational interfaces and data models used across all CodeContext packages. It contains no implementation details, only abstract definitions that other packages depend on.

## Installation

```bash
pip install codecontext-core
```

## Contents

### Interfaces

- **EmbeddingProvider**: Abstract interface for embedding generation providers
- **VectorStore**: Abstract interface for vector storage backends

### Data Models

- **CodeObject**: Represents a semantic unit of code
- **DocumentNode**: Represents documentation or summary content
- **Relationship**: Defines connections between entities
- **IndexState**: Tracks the state of the indexed codebase
- **FileChecksum**: File-level checksum cache for incremental indexing
- **SearchQuery**: Represents a search query and parameters
- **SearchResult**: Represents a search result

### Enums

- **ObjectType**: Types of code objects (class, method, function, etc.)
- **Language**: Supported programming languages
- **NodeType**: Types of document nodes
- **RelationType**: Types of relationships between entities (22 types - 11 bidirectional pairs)
  - **Code-to-Code (8 pairs):**
    - CALLS ↔ CALLED_BY
    - REFERENCES ↔ REFERENCED_BY
    - EXTENDS ↔ EXTENDED_BY
    - IMPLEMENTS ↔ IMPLEMENTED_BY
    - CONTAINS ↔ CONTAINED_BY
    - IMPORTS ↔ IMPORTED_BY
    - DEPENDS_ON ↔ DEPENDED_BY
    - ANNOTATES ↔ ANNOTATED_BY
  - **Document-to-Code (3 pairs):**
    - DOCUMENTS ↔ DOCUMENTED_BY
    - MENTIONS ↔ MENTIONED_IN
    - IMPLEMENTS_SPEC ↔ IMPLEMENTED_IN
- **IndexStatus**: Status of the index

### Exceptions

- **CodeContextError**: Base exception for all CodeContext errors
- **ConfigurationError**: Configuration errors
- **EmbeddingError**: Embedding generation failures
- **StorageError**: Storage operation failures
- **ParserError**: AST parsing failures
- And more...

## Python Version Support

- Python 3.13

## License

MIT License
