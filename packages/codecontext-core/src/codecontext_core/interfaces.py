"""Base interfaces for embedding providers and vector storage."""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, AsyncGenerator, Optional, Protocol
from uuid import UUID


class InstructionType(StrEnum):
    """Instruction types for code embeddings.

    Based on Jina Code Embeddings instruction framework.
    Enables task-specific and asymmetric query/passage encoding.
    """

    NL2CODE_QUERY = "nl2code_query"
    NL2CODE_PASSAGE = "nl2code_passage"
    CODE2CODE_QUERY = "code2code_query"
    CODE2CODE_PASSAGE = "code2code_passage"
    QA_QUERY = "qa_query"
    QA_PASSAGE = "qa_passage"
    DOCUMENT_PASSAGE = "document_passage"


class StreamProgress(Protocol):
    """Progress reporting for streaming operations."""

    def on_batch_start(self, batch_idx: int, batch_size: int) -> None:
        """Called before processing a batch."""
        ...

    def on_batch_complete(self, batch_idx: int, count: int) -> None:
        """Called after batch completes."""
        ...


class EmbeddingProvider(ABC):
    """Embedding provider interface.

    All providers (HuggingFace, OpenAI, custom) implement this interface.
    Supports streaming for memory efficiency.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize provider resources (model, client, etc)."""
        pass

    @abstractmethod
    def embed_text(
        self, text: str, instruction_type: InstructionType = InstructionType.NL2CODE_QUERY
    ) -> list[float]:
        """Embed single text with instruction prefix.

        Args:
            text: Text to embed
            instruction_type: Type of instruction to apply (query vs passage, task type)

        Returns:
            Embedding vector (dimension unchanged)
        """
        pass

    @abstractmethod
    async def embed_stream(
        self,
        chunks: AsyncGenerator[list[str], None],
        *,
        progress: Optional["StreamProgress"] = None,
    ) -> AsyncGenerator[list[list[float]], None]:
        """Stream embeddings for chunks of texts.

        Args:
            chunks: Async generator yielding batches of texts
            progress: Optional progress callback

        Yields:
            Embedding vectors for each batch
        """
        if False:  # pragma: no cover
            yield []

    @abstractmethod
    def get_batch_size(self) -> int:
        """Return optimal batch size for this provider."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return embedding dimension."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up provider resources."""
        pass

    async def __aenter__(self) -> "EmbeddingProvider":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Async context manager exit."""
        await self.cleanup()


class TranslationProvider(ABC):
    """Translation provider interface.

    All providers (NLLB, Google, custom) implement this interface.
    Supports streaming for memory-efficient batch translation.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize provider resources (model, client, etc)."""
        pass

    @abstractmethod
    def translate_text(self, text: str, source_lang: str, target_lang: str = "en") -> str:
        """Translate single text (sync, for search queries).

        Args:
            text: Text to translate
            source_lang: Source language code (ISO 639-1)
            target_lang: Target language code (default: "en")

        Returns:
            Translated text
        """
        pass

    @abstractmethod
    async def translate_stream(
        self,
        chunks: AsyncGenerator[list[str], None],
        source_lang: str,
        target_lang: str = "en",
        *,
        progress: Optional["StreamProgress"] = None,
    ) -> AsyncGenerator[list[str], None]:
        """Stream translations for chunks of texts.

        Args:
            chunks: Async generator yielding batches of texts
            source_lang: Source language code
            target_lang: Target language code (default: "en")
            progress: Optional progress callback

        Yields:
            Translated texts for each batch
        """
        if False:  # pragma: no cover
            yield []

    @abstractmethod
    def get_batch_size(self) -> int:
        """Return optimal batch size for this provider."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up provider resources."""
        pass

    async def __aenter__(self) -> "TranslationProvider":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Async context manager exit."""
        await self.cleanup()


class VectorStore(ABC):
    """Abstract base class for vector storage providers."""

    def __init__(self, config: Any, project_id: str) -> None:
        """
        Initialize storage with project-specific isolation.

        Args:
            config: Provider-specific configuration
            project_id: Unique project identifier for collection isolation

        Note:
            Subclasses must call super().__init__(config, project_id)
        """
        self.config = config
        self.project_id = project_id

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the vector store and create collections if needed.

        Raises:
            StorageError: If initialization fails
        """
        pass

    @abstractmethod
    def add_code_objects(self, objects: list[Any], relationships: list[Any] | None = None) -> None:
        """
        Add code objects with optional relationships to the store.

        Args:
            objects: List of code objects to add
            relationships: Optional list of relationships

        Raises:
            StorageError: If storage operation fails
        """
        pass

    @abstractmethod
    def add_documents(self, documents: list[Any]) -> None:
        """
        Add document nodes to the store.

        Args:
            documents: List of documents to add

        Raises:
            StorageError: If storage operation fails
        """
        pass

    @abstractmethod
    def search_code_objects(
        self,
        query_embedding: list[float],
        limit: int = 10,
        language_filter: Optional[str] = None,
        file_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for code objects by embedding similarity.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            language_filter: Optional language filter
            file_filter: Optional file pattern filter

        Returns:
            List of results with metadata and scores

        Raises:
            StorageError: If search fails
        """
        pass

    @abstractmethod
    def search_documents(
        self,
        query_embedding: list[float],
        limit: int = 10,
        language_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for documents by embedding similarity.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            language_filter: Optional language filter

        Returns:
            List of results with metadata and scores

        Raises:
            StorageError: If search fails
        """
        pass

    @abstractmethod
    def get_code_object(self, object_id: str) -> Optional[Any]:
        """
        Retrieve a code object by deterministic ID.

        Args:
            object_id: Deterministic ID of the code object (32-char hex string)

        Returns:
            CodeObject if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Any]:
        """
        Retrieve a document node by deterministic ID.

        Args:
            document_id: Deterministic ID of the document (32-char hex string)

        Returns:
            DocumentNode if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_documents_batch(self, document_ids: list[str]) -> list[Any]:
        """
        Batch retrieve documents by deterministic IDs.

        Args:
            document_ids: List of deterministic IDs (32-char hex strings)

        Returns:
            List of DocumentNode objects (same order as input IDs)

        Raises:
            StorageError: If retrieval fails

        Note:
            More efficient than multiple get_document() calls.
            Missing IDs are skipped (no error raised).
        """
        pass

    @abstractmethod
    def get_code_objects_batch(self, object_ids: list[str]) -> list[Any]:
        """
        Batch retrieve code objects by deterministic IDs.

        Args:
            object_ids: List of deterministic IDs (32-char hex strings)

        Returns:
            List of CodeObject instances (same order as input IDs)

        Raises:
            StorageError: If retrieval fails

        Note:
            More efficient than multiple get_code_object() calls.
            Missing IDs are skipped (no error raised).
        """
        pass

    @abstractmethod
    def get_all_documents(self, limit: int = 10000) -> list[Any]:
        """
        Retrieve all document nodes from storage.

        This method fetches all documents without filtering, suitable for
        bulk operations like BM25 indexing where all documents are needed.

        Args:
            limit: Maximum number of documents to retrieve (default: 10000)

        Returns:
            List of DocumentNode objects

        Raises:
            StorageError: If retrieval fails

        Note:
            Unlike search_documents(), this method does not use vector similarity.
            It retrieves all documents directly from the collection.
        """
        pass

    @abstractmethod
    def get_relationships(self, source_id: str, relation_type: Optional[str] = None) -> list[Any]:
        """
        Get relationships for a source entity.

        Args:
            source_id: Source entity deterministic ID (32-char hex string)
            relation_type: Optional filter by relation type

        Returns:
            List of relationships

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    def delete_code_objects(self, object_ids: list[UUID]) -> None:
        """
        Delete code objects by IDs.

        Args:
            object_ids: List of object IDs to delete

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    def delete_code_objects_by_file(self, file_path: str) -> int:
        """
        Delete all code objects from a specific file.

        Args:
            file_path: Path to the file

        Returns:
            Number of objects deleted

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    def delete(self, ids: list[str]) -> int:
        """
        Delete items by deterministic IDs.

        Args:
            ids: List of deterministic IDs to delete

        Returns:
            Number of items deleted

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    def delete_documents(self, document_ids: list[UUID]) -> None:
        """
        Delete documents by IDs.

        Args:
            document_ids: List of document IDs to delete

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    def get_file_checksum(self, file_path: str) -> Optional[Any]:
        """
        Get file checksum record.

        Args:
            file_path: Path to the file

        Returns:
            FileChecksum object if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    def set_file_checksum(self, file_checksum: Any) -> None:
        """
        Set file checksum record.

        Args:
            file_checksum: FileChecksum object to store

        Raises:
            StorageError: If update fails
        """
        pass

    @abstractmethod
    def get_file_checksums_batch(self, file_paths: list[str]) -> dict[str, str]:
        """
        Get file checksums for multiple files in batch.

        Args:
            file_paths: List of file paths

        Returns:
            Dictionary mapping file_path to file_checksum

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_code_objects_by_file(self, file_path: str) -> list[Any]:
        """
        Get all code objects from a specific file.

        Args:
            file_path: Path to the file

        Returns:
            List of code objects

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_indexed_file_paths(self) -> set[str]:
        """
        Get all indexed file paths without loading full objects.

        Memory-efficient alternative to get_all_code_objects() when only
        file paths are needed (e.g., for detecting deleted files).

        Returns:
            Set of file paths that have indexed code objects

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_index_state(self) -> Optional[Any]:
        """
        Get the current index state.

        Returns:
            IndexState if exists, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    def update_index_state(self, state: Any) -> None:
        """
        Update the index state.

        Args:
            state: New index state

        Raises:
            StorageError: If update fails
        """
        pass

    @abstractmethod
    def get_statistics(self) -> dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with statistics (counts, sizes, etc.)

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_state(self, key: str) -> bytes | None:
        """Get state value by key.

        Args:
            key: State key

        Returns:
            State value as bytes, or None if not found
        """
        pass

    @abstractmethod
    def set_state(self, key: str, value: bytes) -> None:
        """Set state value by key.

        Args:
            key: State key
            value: State value as bytes
        """
        pass

    @abstractmethod
    def delete_state(self, key: str) -> None:
        """Delete state by key.

        Args:
            key: State key
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connections and cleanup resources."""
        pass

    def __enter__(self) -> "VectorStore":
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit."""
        self.close()
