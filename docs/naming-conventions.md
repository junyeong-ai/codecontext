# Naming Conventions

**Purpose**: Establish clear guidelines for naming patterns in the CodeContext codebase

**Date**: 2025-10-13

---

## Overview

This document defines naming conventions based on design patterns and roles. After comprehensive code review, current naming patterns are **appropriate and should be maintained**.

## Suffix Guidelines

### ✅ When Suffixes Add Value

Suffixes should indicate **design patterns** or **specific roles**:

#### Design Patterns

- **`*Factory`**: Creates instances based on configuration
  - Example: `EmbeddingProviderFactory`, `StorageProviderFactory`
  - Rationale: Clear factory pattern implementation
  - Usage: When object creation logic requires abstraction

- **`*Provider`**: Implements plugin/provider pattern with multiple implementations
  - Example: `QdrantProvider`, `HuggingFaceProvider`
  - Rationale: Indicates pluggable architecture component
  - Usage: When multiple interchangeable implementations exist

- **`*Strategy`**: Implements strategy pattern for algorithm selection
  - Example: `SyncStrategy`, `FullSyncStrategy`, `IncrementalSyncStrategy`
  - Rationale: Clear strategy pattern separation
  - Usage: When multiple algorithms accomplish same goal

#### Role-Based Suffixes

- **`*Manager`**: Manages resources or coordinates operations
  - Example: `CollectionManager`
  - Rationale: Qdrant collection lifecycle management
  - Usage: When coordinating multiple related operations

- **`*Coordinator`**: Orchestrates complex workflows
  - Usage: When coordinating between multiple subsystems

- **`*Parser`**: Parses specific file format or language
  - Example: `PythonParser`, `KotlinParser`, `MarkdownParser`
  - Rationale: Clear parsing responsibility
  - Usage: When extracting structured data from unstructured input

- **`*Extractor`**: Extracts specific information
  - Example: `RelationshipExtractor`
  - Rationale: Single-purpose extraction logic
  - Usage: When focused on pulling specific data from larger context

- **`*Retriever`**: Retrieves data from storage
  - Example: `SearchRetriever`
  - Rationale: Data access layer
  - Usage: When fetching data from persistent storage

- **`*Formatter`**: Formats output for display
  - Example: `TableFormatter`, `JSONFormatter`
  - Rationale: Presentation layer responsibility
  - Usage: When transforming data for user consumption

### ❌ When Suffixes Don't Add Value

Avoid generic suffixes that don't convey clear meaning:

- **`*Util`**: Too generic, prefer specific names
  - ❌ `StringUtil` → ✅ `StringHelper`, `TextProcessor`

- **`*Helper`**: Vague, prefer role-based names
  - ❌ `DataHelper` → ✅ `DataTransformer`, `DataValidator`

- **`*Handler`**: Ambiguous, prefer specific responsibility
  - ❌ `EventHandler` → ✅ `EventProcessor`, `EventListener`

## Current Codebase Review

### ✅ Approved Naming Patterns

The following patterns have been reviewed and approved:

#### Factory Pattern
- `EmbeddingProviderFactory` - Creates embedding providers from config
- `StorageProviderFactory` - Creates storage providers from config
- `ParserFactory` - Creates language-specific parsers

**Justification**: These factories abstract complex creation logic and support plugin architecture.

#### Provider Pattern
- `QdrantProvider` - Vector storage implementation
- `HuggingFaceProvider` - Embedding implementation
- `OpenAIProvider` - Alternative embedding implementation

**Justification**: Provider pattern enables swappable implementations without code changes.

#### Manager Pattern
- `CollectionManager` - Manages Qdrant collection lifecycle

**Justification**: Coordinates create/delete/verify operations for collections, preventing direct Qdrant client exposure.

### No Changes Required

After review of RT-005 research findings, **no naming changes are required**. Current patterns are:
- Consistent with design patterns
- Clear in their intent
- Appropriate for their roles

## Naming Best Practices

### Classes

1. **Use clear, descriptive names**
   ```python
   # Good
   class PythonParser(BaseLanguageParser)
   class QdrantProvider(StorageProvider)

   # Avoid
   class PyParse
   class Qdrant
   ```

2. **Suffix indicates pattern or role**
   ```python
   # Design Pattern
   class SyncStrategy(ABC)
   class FullSyncStrategy(SyncStrategy)

   # Role-based
   class SearchRetriever
   class ResultFormatter
   ```

3. **Base classes are abstract**
   ```python
   # Clear abstraction
   class BaseLanguageParser(ABC)
   class StorageProvider(ABC)
   ```

### Functions

1. **Verbs for actions**
   ```python
   def calculate_checksum()
   def extract_metadata()
   def generate_embedding()
   ```

2. **Clear intent**
   ```python
   # Good
   def find_code_objects_by_language()

   # Avoid
   def get_stuff()
   def do_work()
   ```

### Variables

1. **Descriptive names**
   ```python
   # Good
   embedding_dimension = 768
   chunk_size_tokens = 512

   # Avoid
   dim = 768
   size = 512
   ```

2. **Boolean prefixes**
   ```python
   is_valid = True
   has_embedding = False
   should_retry = True
   ```

## Consistency Rules

1. **Follow established patterns** - When adding new code, match existing naming in that module
2. **Document pattern usage** - If using a pattern (Factory, Provider, Strategy), implement it fully
3. **Avoid mixing patterns** - Don't use Factory pattern naming without factory implementation
4. **Be explicit over clever** - Clear intent beats short names

## Examples

### Good Naming

```python
# Clear design pattern usage
class EmbeddingProviderFactory:
    @staticmethod
    def create(config: Config) -> EmbeddingProvider:
        # Factory logic
        pass

# Clear role indication
class MarkdownChunker:
    def chunk_document(self, content: str) -> List[DocumentNode]:
        # Chunking logic
        pass

# Clear action
def generate_deterministic_id(file_path: str, name: str) -> str:
    # ID generation logic
    pass
```

### Poor Naming

```python
# Too generic
class Util:
    @staticmethod
    def do_stuff():
        pass

# Misleading pattern name
class DataFactory:  # But doesn't actually create objects
    def process(self):
        pass

# Unclear intent
def handle(data):
    pass
```

## Conclusion

CodeContext uses **design pattern-based naming** effectively. Current naming conventions are **approved and should be maintained**. When adding new code:

1. Match existing patterns in the module
2. Use suffixes that indicate clear patterns or roles
3. Avoid generic names (Util, Helper, Handler)
4. Be explicit about responsibility

---

**Status**: ✅ Naming conventions documented and approved
**Last Updated**: 2025-10-13
**Next Review**: As needed when adding new design patterns
