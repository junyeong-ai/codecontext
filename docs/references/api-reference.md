# API Reference

Core interfaces and data models for CodeContext.

---

## Core Interfaces

### EmbeddingProvider

**Location**: [packages/codecontext-core/src/codecontext_core/interfaces.py](../../packages/codecontext-core/src/codecontext_core/interfaces.py)

```python
class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (one per input text)

        Raises:
            EmbeddingError: If embedding generation fails
        """

    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of embeddings produced."""

    @abstractmethod
    def batch_size(self) -> int:
        """Return the optimal batch size for this provider."""

    @abstractmethod
    def close(self) -> None:
        """Clean up resources (models, connections)."""
```

**Implementations**:
- [HuggingFaceEmbeddingProvider](../../packages/codecontext-embeddings-huggingface/src/codecontext_embeddings_huggingface/provider.py)
- [OpenAIEmbeddingProvider](../../packages/codecontext-embeddings-openai/src/codecontext_embeddings_openai/provider.py)

---

### StorageProvider

**Location**: [packages/codecontext-core/src/codecontext_core/interfaces.py](../../packages/codecontext-core/src/codecontext_core/interfaces.py)

```python
class StorageProvider(ABC):
    """Abstract interface for vector storage providers."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize storage (create collections, connect)."""

    @abstractmethod
    def store_objects(
        self,
        objects: list[CodeObject],
        embeddings: list[list[float]],
    ) -> None:
        """Store code objects with their embeddings."""

    @abstractmethod
    def store_documents(
        self,
        documents: list[DocumentNode],
        embeddings: list[list[float]],
    ) -> None:
        """Store documentation nodes with their embeddings."""

    @abstractmethod
    def store_relationships(
        self,
        relationships: list[Relationship],
    ) -> None:
        """Store relationships between code objects."""

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[CodeObject]:
        """Search for code objects by semantic similarity."""

    @abstractmethod
    def get_relationships(
        self,
        object_id: str,
        relation_type: RelationType | None = None,
    ) -> list[Relationship]:
        """Get relationships for a code object."""

    @abstractmethod
    def close(self) -> None:
        """Clean up resources (connections)."""
```

**Implementations**:
- [QdrantProvider](../../packages/codecontext-storage-qdrant/src/codecontext_storage_qdrant/provider.py)

---

### CodeParser

**Location**: [packages/codecontext-cli/src/codecontext/parsers/interfaces.py](../../packages/codecontext-cli/src/codecontext/parsers/interfaces.py)

```python
class CodeParser(Parser):
    """Parser interface for source code files."""

    # Required attributes
    parser: TreeSitterParser
    language: Language

    @abstractmethod
    def extract_code_objects(
        self,
        file_path: Path,
        source: str,
    ) -> list[CodeObject]:
        """
        Extract code objects from source file.

        Args:
            file_path: Path to the source file
            source: Source code content

        Returns:
            List of extracted code objects (classes, functions, methods)
        """

    @abstractmethod
    def extract_relationships(
        self,
        file_path: Path,
        source: str,
        objects: list[CodeObject],
    ) -> list[tuple[str, str, str]]:
        """
        Extract relationships between code objects.

        Args:
            file_path: Path to the source file
            source: Source code content
            objects: Previously extracted code objects

        Returns:
            List of (source_id, target_id, relation_type) tuples
        """

    @abstractmethod
    def extract_ast_metadata(
        self,
        node: Any,
        source_bytes: bytes,
    ) -> dict:
        """
        Extract language-specific AST metadata.

        Returns:
            Dictionary containing:
            - complexity: Cyclomatic complexity
            - nesting_depth: Maximum nesting depth
            - lines_of_code: Total lines
        """
```

**Implementations**:
- [PythonParser](../../packages/codecontext-cli/src/codecontext/parsers/languages/python.py)
- [KotlinParser](../../packages/codecontext-cli/src/codecontext/parsers/languages/kotlin.py)
- [JavaParser](../../packages/codecontext-cli/src/codecontext/parsers/languages/java.py)
- [JavaScriptParser](../../packages/codecontext-cli/src/codecontext/parsers/languages/javascript.py)
- [TypeScriptParser](../../packages/codecontext-cli/src/codecontext/parsers/languages/typescript.py)

---

### DocumentParser

**Location**: [packages/codecontext-cli/src/codecontext/parsers/interfaces.py](../../packages/codecontext-cli/src/codecontext/parsers/interfaces.py)

```python
class DocumentParser(Parser):
    """Parser interface for documentation and configuration files."""

    @abstractmethod
    def parse_file(self, file_path: Path) -> list[DocumentNode]:
        """
        Parse document file into structured nodes.

        Args:
            file_path: Path to the document file

        Returns:
            List of document nodes with metadata
        """

    @abstractmethod
    def extract_code_references(self, content: str) -> list[dict]:
        """
        Extract references to code from documentation.

        Args:
            content: Document content

        Returns:
            List of code references with context
        """

    @abstractmethod
    def chunk_document(
        self,
        content: str,
        max_chunk_size: int = 1500,
    ) -> list[tuple[str, int, int]]:
        """
        Split large documents into chunks for embedding.

        Returns:
            List of (chunk_content, start_index, end_index) tuples
        """
```

**Implementations**:
- [MarkdownParser](../../packages/codecontext-cli/src/codecontext/parsers/languages/markdown.py)
- [ConfigFileParser](../../packages/codecontext-cli/src/codecontext/parsers/languages/config.py)

---

## Data Models

### CodeObject

**Location**: [packages/codecontext-core/src/codecontext_core/models.py](../../packages/codecontext-core/src/codecontext_core/models.py)

```python
@dataclass
class CodeObject:
    """Represents a code entity (class, function, method, variable)."""

    id: str                      # Unique identifier
    name: str                    # Object name
    object_type: ObjectType      # CLASS, FUNCTION, METHOD, VARIABLE
    language: Language           # Programming language
    file_path: str               # Source file path
    start_line: int              # Starting line number
    end_line: int                # Ending line number
    signature: str               # Function/method signature
    docstring: str | None        # Documentation string
    code_snippet: str            # Source code snippet
    parent_id: str | None        # Parent object ID (for nested objects)
    metadata: dict               # Language-specific metadata

    # AST metadata
    complexity: int | None       # Cyclomatic complexity
    nesting_depth: int | None    # Maximum nesting depth
    lines_of_code: int | None    # Total lines of code
```

**ObjectType Enum**:
```python
class ObjectType(str, Enum):
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    PROPERTY = "property"
    INTERFACE = "interface"
    ENUM = "enum"
    CONSTANT = "constant"
```

---

### Relationship

**Location**: [packages/codecontext-core/src/codecontext_core/models.py](../../packages/codecontext-core/src/codecontext_core/models.py)

```python
@dataclass
class Relationship:
    """Represents a relationship between code objects."""

    id: str                      # Unique identifier
    source_id: str               # Source object ID
    target_id: str               # Target object ID
    relation_type: RelationType  # CALLS, CONTAINS, REFERENCES
    metadata: dict               # Additional context
```

**RelationType Enum**:
```python
class RelationType(str, Enum):
    CALLS = "calls"              # Function/method invocation
    CONTAINS = "contains"        # Hierarchical containment
    REFERENCES = "references"    # Inheritance/interface implementation
```

---

### DocumentNode

**Location**: [packages/codecontext-core/src/codecontext_core/models.py](../../packages/codecontext-core/src/codecontext_core/models.py)

```python
@dataclass
class DocumentNode:
    """Represents a documentation node (markdown section, config entry)."""

    id: str                      # Unique identifier
    content: str                 # Node content
    node_type: str               # heading, paragraph, code_block, config_key
    file_path: str               # Source file path
    start_line: int              # Starting line number
    end_line: int                # Ending line number
    metadata: dict               # Additional metadata

    # For hierarchical documents
    level: int | None            # Heading level (markdown)
    parent_id: str | None        # Parent node ID

    # For config files
    config_key: str | None       # Configuration key path
    config_value: str | None     # Configuration value
    env_references: list[str]    # Environment variable references
```

---

### Language

**Location**: [packages/codecontext-core/src/codecontext_core/models.py](../../packages/codecontext-core/src/codecontext_core/models.py)

```python
class Language(str, Enum):
    """Supported programming languages."""

    # Code languages
    PYTHON = "python"
    KOTLIN = "kotlin"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"

    # Config languages
    YAML = "yaml"
    JSON = "json"
    PROPERTIES = "properties"

    # Document languages
    MARKDOWN = "markdown"
```

---

## Factory Patterns

### EmbeddingProviderFactory

**Location**: [packages/codecontext-cli/src/codecontext/embeddings/factory.py](../../packages/codecontext-cli/src/codecontext/embeddings/factory.py)

```python
class EmbeddingProviderFactory:
    """Factory for creating embedding providers."""

    @staticmethod
    def create(
        provider_name: str,
        config: EmbeddingsConfig,
    ) -> EmbeddingProvider:
        """
        Create embedding provider by name.

        Args:
            provider_name: "huggingface" or "openai"
            config: Provider configuration

        Returns:
            Configured embedding provider instance

        Raises:
            ValueError: If provider not found
        """
```

---

### StorageProviderFactory

**Location**: [packages/codecontext-cli/src/codecontext/storage/factory.py](../../packages/codecontext-cli/src/codecontext/storage/factory.py)

```python
class StorageProviderFactory:
    """Factory for creating storage providers."""

    @staticmethod
    def create(
        provider_name: str,
        config: StorageConfig,
    ) -> StorageProvider:
        """
        Create storage provider by name.

        Args:
            provider_name: "qdrant"
            config: Provider configuration

        Returns:
            Configured storage provider instance

        Raises:
            ValueError: If provider not found
        """
```

---

### ParserFactory

**Location**: [packages/codecontext-cli/src/codecontext/parsers/factory.py](../../packages/codecontext-cli/src/codecontext/parsers/factory.py)

```python
class ParserFactory:
    """Factory for creating code parsers."""

    def get_parser(self, file_path: str) -> CodeParser:
        """
        Get parser for file (CODE FILES ONLY).

        Args:
            file_path: Path to source file

        Returns:
            Language-specific parser instance

        Raises:
            UnsupportedLanguageError: If not a code file
        """

    def get_parser_by_language(self, language: Language) -> CodeParser:
        """Get parser for a specific language."""
```

---

## Exceptions

**Location**: [packages/codecontext-core/src/codecontext_core/exceptions.py](../../packages/codecontext-core/src/codecontext_core/exceptions.py)

```python
class CodeContextError(Exception):
    """Base exception for all CodeContext errors."""

class EmbeddingError(CodeContextError):
    """Error during embedding generation."""

class StorageError(CodeContextError):
    """Error during storage operations."""

class ParsingError(CodeContextError):
    """Error during code parsing."""

class UnsupportedLanguageError(CodeContextError):
    """Language not supported."""

class ConfigurationError(CodeContextError):
    """Invalid configuration."""
```

---

## Usage Examples

### Using EmbeddingProvider

```python
from codecontext.embeddings.factory import EmbeddingProviderFactory
from codecontext.config.schema import EmbeddingsConfig

# Create provider
config = EmbeddingsConfig(provider="huggingface")
provider = EmbeddingProviderFactory.create("huggingface", config)

# Generate embeddings
texts = ["def hello(): print('Hello')", "class Foo: pass"]
embeddings = provider.embed(texts)

print(f"Dimension: {provider.dimension()}")  # 768
print(f"Embeddings: {len(embeddings)}")      # 2
```

### Using StorageProvider

```python
from codecontext.storage.factory import StorageProviderFactory
from codecontext.config.schema import StorageConfig
from codecontext_core.models import CodeObject, ObjectType, Language

# Create provider
config = StorageConfig(provider="qdrant")
provider = StorageProviderFactory.create("qdrant", config)
provider.initialize()

# Store objects
objects = [
    CodeObject(
        id="obj1",
        name="hello",
        object_type=ObjectType.FUNCTION,
        language=Language.PYTHON,
        file_path="test.py",
        start_line=1,
        end_line=2,
        signature="def hello()",
        code_snippet="def hello(): print('Hello')",
    )
]
embeddings = [[0.1, 0.2, ...]]  # 768-dim vectors
provider.store_objects(objects, embeddings)

# Search
query_embedding = [0.15, 0.18, ...]
results = provider.search(query_embedding, limit=10)
```

### Using CodeParser

```python
from codecontext.parsers.factory import ParserFactory
from codecontext.config.schema import ParsingConfig

# Create factory
config = ParsingConfig()
factory = ParserFactory.from_parsing_config(config)

# Get parser for file
parser = factory.get_parser("example.py")

# Extract code objects
source = "def hello(): print('Hello')"
objects = parser.extract_code_objects(Path("example.py"), source)

# Extract relationships
relationships = parser.extract_relationships(
    Path("example.py"),
    source,
    objects,
)
```

---

## Additional Resources

- [Architecture Diagram](../architecture.md)
- [Custom Parsers Guide](../guides/custom-parsers.md)
- [Embedding Configuration Guide](../guides/embedding-configuration.md)
