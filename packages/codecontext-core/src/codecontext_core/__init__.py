"""CodeContext Core - Shared interfaces and data models."""

from codecontext_core.exceptions import (
    CodeContextError,
    ConfigurationError,
    EmbeddingError,
    StorageError,
    IndexingError,
    SearchError,
    ParserError,
    ValidationError,
    GitError,
    UnsupportedLanguageError,
    FileNotInRepositoryError,
    InvalidChecksumError,
)
from codecontext_core.interfaces import (
    EmbeddingProvider,
    InstructionType,
    TranslationProvider,
    VectorStore,
)
from codecontext_core.device import DeviceStrategy, DeviceConfig, create_device_strategy
from codecontext_core.allocator import AllocatorDetector, AllocatorInfo
from codecontext_core.monitoring import ProcessTree, ProcessMetrics
from codecontext_core.models import (
    ObjectType,
    Language,
    NodeType,
    RelationType,
    IndexStatus,
    CodeObject,
    DocumentNode,
    Relationship,
    IndexState,
    FileChecksum,
    SearchQuery,
    SearchResult,
    SearchScoring,
)
from codecontext_core.models.cast_chunk import CASTChunk
from codecontext_core.tokenizer import IdentifierTokenizer, CodeTokenizer
from codecontext_core.bm25 import BM25FEncoder

__version__ = "1.0.0"

__all__ = [
    # Exceptions
    "CodeContextError",
    "ConfigurationError",
    "EmbeddingError",
    "StorageError",
    "IndexingError",
    "SearchError",
    "ParserError",
    "ValidationError",
    "GitError",
    "UnsupportedLanguageError",
    "FileNotInRepositoryError",
    "InvalidChecksumError",
    # Interfaces
    "EmbeddingProvider",
    "InstructionType",
    "TranslationProvider",
    "VectorStore",
    # Device
    "DeviceStrategy",
    "DeviceConfig",
    "create_device_strategy",
    # Allocator
    "AllocatorDetector",
    "AllocatorInfo",
    # Monitoring
    "ProcessTree",
    "ProcessMetrics",
    # Models - Enums
    "ObjectType",
    "Language",
    "NodeType",
    "RelationType",
    "IndexStatus",
    # Models - Data Classes
    "CodeObject",
    "DocumentNode",
    "Relationship",
    "IndexState",
    "FileChecksum",
    "SearchQuery",
    "SearchResult",
    "CASTChunk",
    "SearchScoring",
    # Tokenizer
    "IdentifierTokenizer",
    "CodeTokenizer",
    # BM25
    "BM25FEncoder",
]
