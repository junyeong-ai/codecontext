"""ChromaDB storage provider implementation using Python client library."""

from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID
import logging
import time

from codecontext_core import CodeObject, DocumentNode, Relationship, StorageError, VectorStore
from codecontext_core.models.core import ObjectType
from codecontext.config.schema import ChromaDBConfig

if TYPE_CHECKING:
    import chromadb
else:
    try:
        import chromadb
    except ImportError:
        raise ImportError("chromadb package is required. Install with: pip install chromadb")

logger = logging.getLogger(__name__)


class ChromaDBVectorStore(VectorStore):
    """ChromaDB-based vector storage provider using Python client library.

    File Size Justification (658 LOC):
    =====================================
    This class implements the Facade pattern, coordinating 4 specialized ChromaDB
    collections (code_objects, documents, relationships, state) through a single
    interface. Splitting this file would create an anti-pattern:

    1. **Single Responsibility**: One facade per storage backend (ChromaDB)
    2. **Coordinated Operations**: Methods often touch multiple collections
    3. **Transaction-like Semantics**: Related operations grouped together
    4. **Entry Point Discovery**: Single file for all ChromaDB operations

    Splitting Strategy Rejected:
    - Collection-based split: Would require cross-file coordination
    - Operation-based split: Would violate single responsibility
    - Size reduction would sacrifice architectural clarity

    Alternative Considered: Extract collection managers as internal classes.
    Rejected because it adds complexity without improving maintainability.

    Conclusion: 658 LOC is acceptable for this Facade pattern implementation.
    """

    MAX_RETRIES = 5
    INITIAL_BACKOFF = 0.5  # 500ms

    def __init__(self, config: ChromaDBConfig, project_id: str) -> None:
        """
        Initialize ChromaDB storage provider with Python client.

        Args:
            config: ChromaDB configuration (host, port)
            project_id: Unique project identifier for collection isolation
        """
        super().__init__(config, project_id)
        self.config = config
        self.project_id = project_id
        self.client: Optional[chromadb.ClientAPI] = None

        # 2-collection architecture: content (vectors) + meta (metadata only)
        self.collection_names = {
            "content": config.get_collection_name(project_id, "content"),
            "meta": config.get_collection_name(project_id, "meta"),
        }

        # Store collection instances
        self.collections: dict[str, chromadb.Collection] = {}

    def initialize(self) -> None:
        """
        Initialize the vector store and create collections if needed.

        Raises:
            StorageError: If initialization fails (including connection errors)
        """
        try:
            # Create HTTP client using ChromaDB Python client
            self.client = chromadb.HttpClient(
                host=self.config.host,
                port=self.config.port,
            )

            # Test connection with heartbeat
            try:
                self.client.heartbeat()
            except Exception as e:
                logger.error("❌ Cannot connect to ChromaDB server")
                logger.error("Error: %s", e)
                logger.error("Start server: ./scripts/chroma-cli.sh start")
                raise StorageError(
                    "ChromaDB server not running. Start with: ./scripts/chroma-cli.sh start"
                ) from e

            # Create or get project-specific collections
            for key, name in self.collection_names.items():
                try:
                    # Use get_or_create_collection for idempotency
                    collection = self.client.get_or_create_collection(
                        name=name,
                        metadata={
                            "hnsw:space": "cosine",
                            "project_id": self.project_id,
                        },
                    )
                    self.collections[key] = collection
                except Exception as e:
                    raise StorageError(f"Failed to create collection '{name}': {e}") from e

        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to initialize ChromaDB: {e}") from e

    def _upsert_with_retry(
        self,
        collection: chromadb.Collection,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Upsert with exponential backoff retry for SQLite concurrency issues."""
        for attempt in range(self.MAX_RETRIES):
            try:
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
                return
            except Exception as e:
                error_msg = str(e)
                if "readonly database" in error_msg or "database is locked" in error_msg:
                    if attempt < self.MAX_RETRIES - 1:
                        backoff = self.INITIAL_BACKOFF * (2**attempt)
                        time.sleep(backoff)
                        continue
                raise

    def add_code_objects(self, objects: list[Any]) -> None:
        """
        Add code objects to the store.

        Args:
            objects: List of code objects to add

        Raises:
            StorageError: If storage operation fails
        """
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            ids, embeddings, metadatas, documents = [], [], [], []
            for obj in objects:
                ids.append(obj.deterministic_id)
                if obj.embedding is not None:
                    embeddings.append(obj.embedding)
                metadatas.append(obj.to_metadata())
                documents.append(obj.content)

            if len(embeddings) != len(objects):
                missing_count = len(objects) - len(embeddings)
                raise StorageError(
                    f"Embedding validation failed: {missing_count} of {len(objects)} "
                    f"objects missing embeddings. All objects must have embeddings before storage."
                )

            self._upsert_with_retry(collection, ids, embeddings, documents, metadatas)

        except Exception as e:
            raise StorageError(f"Failed to add code objects: {e}") from e

    def add_documents(self, documents: list[Any]) -> None:
        """
        Add document nodes to the store.

        Args:
            documents: List of documents to add

        Raises:
            StorageError: If storage operation fails
        """
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            ids, embeddings, contents, metadatas = [], [], [], []
            for doc in documents:
                ids.append(doc.deterministic_id)
                if doc.embedding is not None:
                    embeddings.append(doc.embedding)
                contents.append(doc.content)
                metadatas.append(doc.to_metadata())

            if len(embeddings) == len(documents):
                self._upsert_with_retry(collection, ids, embeddings, contents, metadatas)

        except Exception as e:
            raise StorageError(f"Failed to add documents: {e}") from e

    async def add_relationships(self, relationships: list[Any]) -> None:
        """
        Add relationships to the store.

        Args:
            relationships: List of relationships to add

        Raises:
            StorageError: If storage operation fails
        """
        import asyncio

        if not self.client or "meta" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["meta"]

            # Deduplicate relationships by deterministic ID (within batch)
            seen_ids = set()
            unique_rels = []
            for rel in relationships:
                rel_id = rel.generate_deterministic_id()
                if rel_id not in seen_ids:
                    seen_ids.add(rel_id)
                    unique_rels.append((rel_id, rel))

            if not unique_rels:
                return

            ids = [rel_id for rel_id, _ in unique_rels]
            metadatas = [rel.to_metadata() for _, rel in unique_rels]
            documents = [f"{rel.source_id}-{rel.target_id}" for _, rel in unique_rels]

            # Run blocking I/O in thread pool to avoid blocking event loop
            # Use upsert to handle cross-batch duplicates
            await asyncio.to_thread(
                collection.upsert,
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

        except Exception as e:
            raise StorageError(f"Failed to add relationships: {e}") from e

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
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            where_filter = {}
            if language_filter:
                where_filter["language"] = language_filter
            if file_filter:
                where_filter["file_path"] = file_filter

            results = collection.query(
                query_embeddings=[query_embedding],  # type: ignore[arg-type]
                n_results=limit,
                where=where_filter if where_filter else None,  # type: ignore[arg-type]
                include=["metadatas", "documents", "distances"],
            )

            return self._format_results(results)  # type: ignore[arg-type]

        except Exception as e:
            raise StorageError(f"Failed to search code objects: {e}") from e

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
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            where_filter = {"language": language_filter} if language_filter else None

            results = collection.query(
                query_embeddings=[query_embedding],  # type: ignore[arg-type]
                n_results=limit,
                where=where_filter,  # type: ignore[arg-type]
                include=["metadatas", "documents", "distances"],
            )

            return self._format_results(results)  # type: ignore[arg-type]

        except Exception as e:
            raise StorageError(f"Failed to search documents: {e}") from e

    def get_code_object(self, object_id: str) -> Optional["CodeObject"]:
        """
        Retrieve a code object by ID.

        Args:
            object_id: Deterministic ID of the code object (32-char hex string)

        Returns:
            CodeObject if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            result = collection.get(
                ids=[object_id],
                include=["metadatas", "documents"],
            )

            if result["ids"] and len(result["ids"]) > 0:
                metadatas = result.get("metadatas")
                documents = result.get("documents")
                if metadatas and documents and len(metadatas) > 0 and len(documents) > 0:
                    metadata = dict(metadatas[0])  # Convert Mapping to dict
                    content = documents[0]
                    return CodeObject.from_metadata(metadata, content)
            return None

        except Exception as e:
            raise StorageError(f"Failed to get code object: {e}") from e

    def get_code_objects_batch(self, object_ids: list[str]) -> list[CodeObject]:
        """
        Retrieve multiple code objects by IDs in a single batch operation.

        This method significantly improves performance by reducing HTTP requests
        from N individual calls to 1 batch call. Includes full object data
        (metadata + content) for complete reconstruction.

        Args:
            object_ids: List of deterministic IDs (32-char hex strings)

        Returns:
            List of CodeObject instances for found objects.
            Missing IDs are silently skipped.

        Raises:
            StorageError: If retrieval fails

        Example:
            >>> ids = ["abc123...", "def456..."]
            >>> objects = provider.get_code_objects_batch(ids)
            >>> # Returns: [CodeObject(...), CodeObject(...)]
        """
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        if not object_ids:
            return []

        try:
            collection = self.collections["content"]

            result = collection.get(
                ids=object_ids,
                include=["metadatas", "documents"],
            )

            # Build list of found objects (preserving order when possible)
            objects = []
            if result["ids"]:
                metadatas = result.get("metadatas")
                documents = result.get("documents")
                if metadatas and documents:
                    for obj_id, metadata, content in zip(result["ids"], metadatas, documents):
                        objects.append(CodeObject.from_metadata(dict(metadata), content))

            return objects

        except Exception as e:
            raise StorageError(f"Failed to batch get code objects: {e}") from e

    def get_document(self, document_id: str) -> Optional[DocumentNode]:
        """
        Retrieve a document node by deterministic ID.

        Args:
            document_id: Deterministic ID of the document (32-char hex string)

        Returns:
            DocumentNode if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            result = collection.get(
                ids=[document_id],
                include=["metadatas", "documents"],
            )

            if result["ids"] and len(result["ids"]) > 0:
                metadatas = result.get("metadatas")
                documents = result.get("documents")
                if metadatas and documents and len(metadatas) > 0 and len(documents) > 0:
                    metadata = dict(metadatas[0])  # Convert Mapping to dict
                    content = documents[0]
                    return DocumentNode.from_metadata(metadata, content)
            return None

        except Exception as e:
            raise StorageError(f"Failed to get document: {e}") from e

    def get_documents_batch(self, document_ids: list[str]) -> list[DocumentNode]:
        """Batch retrieve documents by IDs."""
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        if not document_ids:
            return []

        try:
            collection = self.collections["content"]

            result = collection.get(
                ids=document_ids,
                where={"object_type": ObjectType.DOCUMENT.value},
                include=["metadatas", "documents"],
            )

            documents = []
            if result["ids"]:
                metadatas = result.get("metadatas", [])
                contents = result.get("documents", [])

                for i in range(len(result["ids"])):
                    if i < len(metadatas) and i < len(contents):
                        doc_node = DocumentNode.from_metadata(dict(metadatas[i]), contents[i])
                        documents.append(doc_node)

            return documents

        except Exception as e:
            raise StorageError(f"Failed to batch get documents: {e}") from e

    def get_all_documents(self, limit: int = 10000) -> list[DocumentNode]:
        """Retrieve all document nodes from storage."""
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            result = collection.get(
                where={"object_type": ObjectType.DOCUMENT.value},
                limit=limit,
                include=["metadatas", "documents"],
            )

            if not result["ids"]:
                return []

            metadatas = result.get("metadatas", [])
            contents = result.get("documents", [])

            documents = []
            for i in range(len(result["ids"])):
                if i < len(metadatas) and i < len(contents):
                    doc = DocumentNode.from_metadata(dict(metadatas[i]), contents[i])
                    documents.append(doc)

            return documents

        except Exception as e:
            raise StorageError(f"Failed to get all documents: {e}") from e

    def get_relationships(
        self, source_id: str, relation_type: Optional[str] = None
    ) -> list["Relationship"]:
        """
        Get relationships for a source entity.

        Args:
            source_id: Source entity deterministic ID (32-char hex string)
            relation_type: Optional filter by relation type

        Returns:
            List of Relationship objects

        Raises:
            StorageError: If retrieval fails
        """
        if not self.client or "meta" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["meta"]

            where_filter = {"source_id": source_id}
            if relation_type:
                where_filter["relation_type"] = relation_type

            results = collection.get(
                where=where_filter,  # type: ignore[arg-type]
                include=["metadatas"],
            )

            relationships = []
            if results["ids"]:
                metadatas = results.get("metadatas")
                if metadatas:
                    for metadata in metadatas:
                        relationships.append(Relationship.from_metadata(dict(metadata)))

            return relationships

        except Exception as e:
            raise StorageError(f"Failed to get relationships: {e}") from e

    def get_relationships_batch(
        self, source_ids: list[str], relation_type: Optional[str] = None
    ) -> dict[str, list["Relationship"]]:
        """
        Get relationships for multiple source entities in a single batch operation.

        This method significantly improves performance by reducing HTTP requests
        from N individual calls to 1 batch call.

        Args:
            source_ids: List of source entity deterministic IDs (32-char hex strings)
            relation_type: Optional filter by relation type

        Returns:
            Dictionary mapping source_id -> list[Relationship].
            Source IDs with no relationships return empty list.

        Raises:
            StorageError: If retrieval fails

        Example:
            >>> ids = ["abc123...", "def456..."]
            >>> rels = provider.get_relationships_batch(ids)
            >>> # Returns: {
            >>>   "abc123...": [Relationship(...), ...],
            >>>   "def456...": [Relationship(...)]
            >>> }
        """
        if not self.client or "meta" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        if not source_ids:
            return {}

        try:
            collection = self.collections["meta"]

            # Build where filter with $or for multiple source_ids
            where_filter: dict = {"$or": [{"source_id": sid} for sid in source_ids]}
            if relation_type:
                # Combine with relation_type filter
                where_filter = {"$and": [where_filter, {"relation_type": relation_type}]}

            results = collection.get(
                where=where_filter,  # type: ignore[arg-type]
                include=["metadatas"],
            )

            # Group relationships by source_id
            relationships_by_source: dict[str, list["Relationship"]] = {
                sid: [] for sid in source_ids
            }

            if results["ids"]:
                metadatas = results.get("metadatas")
                if metadatas:
                    for metadata in metadatas:
                        rel = Relationship.from_metadata(dict(metadata))  # type: ignore[arg-type]
                        source_id = rel.source_id
                        if source_id in relationships_by_source:
                            relationships_by_source[source_id].append(rel)

            return relationships_by_source

        except Exception as e:
            raise StorageError(f"Failed to batch get relationships: {e}") from e

    def delete_code_objects(self, object_ids: list[UUID]) -> None:
        """
        Delete code objects by IDs.

        Args:
            object_ids: List of object IDs to delete

        Raises:
            StorageError: If deletion fails
        """
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]
            ids = [str(oid) for oid in object_ids]
            collection.delete(ids=ids)

        except Exception as e:
            raise StorageError(f"Failed to delete code objects: {e}") from e

    def delete_code_objects_by_file(self, file_path: str) -> int:
        """
        Delete all code objects for a specific file.

        Args:
            file_path: File path to delete objects for

        Returns:
            Number of objects deleted

        Raises:
            StorageError: If deletion fails
        """
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            # Find all objects for this file
            result = collection.get(where={"file_path": file_path})

            if not result["ids"]:
                return 0

            # Delete the objects
            collection.delete(ids=result["ids"])

            return len(result["ids"])

        except Exception as e:
            raise StorageError(f"Failed to delete code objects by file: {e}") from e

    def delete_documents(self, document_ids: list[UUID]) -> None:
        """
        Delete documents by IDs.

        Args:
            document_ids: List of document IDs to delete

        Raises:
            StorageError: If deletion fails
        """
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]
            ids = [str(did) for did in document_ids]
            collection.delete(ids=ids)

        except Exception as e:
            raise StorageError(f"Failed to delete documents: {e}") from e

    def get_index_state(self) -> Optional[Any]:
        """
        Get the current index state.

        Returns:
            IndexState if exists, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        if not self.client or "meta" not in self.collections:
            return None

        try:
            collection = self.collections["meta"]

            result = collection.get(
                ids=["index_state"],
                include=["metadatas"],
            )

            if result["ids"] and len(result["ids"]) > 0:
                metadatas = result.get("metadatas")
                if metadatas and len(metadatas) > 0:
                    return metadatas[0]
            return None

        except Exception:
            # Return None for not found errors
            return None

    def update_index_state(self, state: Any) -> None:
        """
        Update the index state.

        Args:
            state: New index state

        Raises:
            StorageError: If update fails
        """
        if not self.client or "meta" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["meta"]
            state_dict = state.to_metadata() if hasattr(state, "to_metadata") else state

            collection.upsert(
                ids=["index_state"],
                documents=["index_state"],
                metadatas=[state_dict],
            )

        except Exception as e:
            raise StorageError(f"Failed to update index state: {e}") from e

    def get_statistics(self) -> dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with statistics (counts, sizes, etc.)

        Raises:
            StorageError: If retrieval fails
        """
        if not self.client:
            raise StorageError("ChromaDB not initialized")

        try:
            content_collection = self.collections["content"]

            # Count code objects and documents separately
            code_result = content_collection.get(
                where={"object_type": {"$ne": ObjectType.DOCUMENT.value}},
                include=[],
            )
            doc_result = content_collection.get(
                where={"object_type": ObjectType.DOCUMENT.value},
                include=[],
            )

            code_count = len(code_result["ids"]) if code_result["ids"] else 0
            doc_count = len(doc_result["ids"]) if doc_result["ids"] else 0

            # Get last modified time from index state
            last_modified = ""
            try:
                index_state = self.get_index_state()
                if index_state and hasattr(index_state, "last_indexed_at"):
                    last_modified = index_state.last_indexed_at.isoformat()
            except Exception:
                pass  # Ignore errors, last_modified is optional

            return {
                "content_count": content_collection.count(),
                "meta_count": self.collections["meta"].count(),
                "code_objects_count": code_count,
                "documents_count": doc_count,
                "last_modified": last_modified,
            }

        except Exception as e:
            raise StorageError(f"Failed to get statistics: {e}") from e

    def get_state(self, key: str) -> bytes | None:
        """Get state value by key.

        Args:
            key: State key

        Returns:
            State value as bytes, or None if not found
        """
        if not self.client or "meta" not in self.collections:
            return None

        try:
            import base64

            collection = self.collections["meta"]
            state_id = f"state_{key}"

            result = collection.get(ids=[state_id], include=["documents"])

            if result["ids"] and len(result["ids"]) > 0:
                documents = result.get("documents")
                if documents and len(documents) > 0:
                    encoded = documents[0]
                    return base64.b64decode(encoded)

            return None

        except Exception:
            return None

    def set_state(self, key: str, value: bytes) -> None:
        """Set state value by key.

        Args:
            key: State key
            value: State value as bytes
        """
        if not self.client or "meta" not in self.collections:
            return

        try:
            import base64

            collection = self.collections["meta"]
            state_id = f"state_{key}"

            encoded = base64.b64encode(value).decode("ascii")

            collection.upsert(
                ids=[state_id],
                documents=[encoded],
                metadatas=[{"type": "state"}],
            )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to set state for {key}: {e}")

    def delete_state(self, key: str) -> None:
        """Delete state by key.

        Args:
            key: State key
        """
        if not self.client or "meta" not in self.collections:
            return

        try:
            collection = self.collections["meta"]
            state_id = f"state_{key}"
            collection.delete(ids=[state_id])

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to delete state for {key}: {e}")

    def close(self) -> None:
        """Close client and cleanup resources."""
        self.client = None
        self.collections.clear()

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
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]
            collection.delete(ids=ids)
            return len(ids)

        except Exception as e:
            raise StorageError(f"Failed to delete items: {e}") from e

    def get_all_code_objects(self) -> list[Any]:
        """Get all code objects from storage."""
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            result = collection.get(
                where={"object_type": {"$ne": ObjectType.DOCUMENT.value}},
                include=["metadatas", "documents"],
            )

            if not result["ids"]:
                return []

            objects = []
            metadatas = result.get("metadatas")
            documents = result.get("documents")

            if metadatas and documents:
                for i in range(len(result["ids"])):
                    obj = CodeObject.from_metadata(dict(metadatas[i]), documents[i])
                    objects.append(obj)

            return objects

        except Exception as e:
            raise StorageError(f"Failed to get all code objects: {e}") from e

    def get_indexed_file_paths(self) -> set[str]:
        """Get all indexed file paths."""
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            result = collection.get(
                where={"object_type": {"$ne": ObjectType.DOCUMENT.value}},
                include=["metadatas"],
            )

            if not result["ids"]:
                return set()

            file_paths = set()
            metadatas = result.get("metadatas")
            if metadatas:
                file_paths = {
                    metadata.get("file_path") for metadata in metadatas if metadata.get("file_path")
                }

            return file_paths  # type: ignore[return-value]

        except Exception as e:
            raise StorageError(f"Failed to get indexed file paths: {e}") from e

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
        if not self.client or "content" not in self.collections:
            raise StorageError("ChromaDB not initialized")

        try:
            collection = self.collections["content"]

            result = collection.get(
                where={"file_path": file_path},
                include=["metadatas", "documents", "embeddings"],
            )

            if not result["ids"]:
                return []

            # Reconstruct CodeObject instances
            objects = []
            metadatas = result.get("metadatas")
            documents = result.get("documents")
            embeddings = result.get("embeddings")

            if metadatas and documents:
                for i in range(len(result["ids"])):
                    metadata = metadatas[i]
                    content = documents[i]
                    obj = CodeObject.from_metadata(dict(metadata), content)
                    # Restore embedding if available
                    if embeddings and i < len(embeddings):
                        obj.embedding = list(embeddings[i])  # type: ignore[arg-type]
                    objects.append(obj)

            return objects

        except Exception as e:
            raise StorageError(f"Failed to get objects for file {file_path}: {e}") from e

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
        if not self.client or "meta" not in self.collections:
            return None

        try:
            collection = self.collections["meta"]

            # Use file path as ID (with prefix to avoid conflicts)
            checksum_id = f"checksum_{file_path}"

            result = collection.get(
                ids=[checksum_id],
                include=["metadatas"],
            )

            if result["ids"] and len(result["ids"]) > 0:
                metadatas = result.get("metadatas")
                if metadatas and len(metadatas) > 0:
                    metadata = metadatas[0]
                    # Return metadata dict that can be converted to FileChecksum
                    return type("FileChecksum", (), dict(metadata))()  # type: ignore[call-overload]

            return None

        except Exception as e:
            # Return None for not found or other errors
            # Safe failure: incremental sync falls back to full scan
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(
                f"Failed to retrieve checksum for {file_path}: {e}. "
                f"File will be processed normally."
            )
            return None

    def set_file_checksum(self, file_checksum: Any) -> None:
        """
        Set file checksum record.

        Args:
            file_checksum: FileChecksum object to store

        Raises:
            StorageError: If update fails
        """
        if not self.client or "meta" not in self.collections:
            return

        try:
            collection = self.collections["meta"]

            # Convert FileChecksum to dict
            if hasattr(file_checksum, "to_metadata"):
                checksum_dict = file_checksum.to_metadata()
            elif hasattr(file_checksum, "__dict__"):
                checksum_dict = {k: str(v) for k, v in file_checksum.__dict__.items()}
            else:
                checksum_dict = dict(file_checksum)

            file_path = checksum_dict.get("file_path", "")
            checksum_id = f"checksum_{file_path}"

            collection.upsert(
                ids=[checksum_id],
                documents=[f"checksum_{file_path}"],
                metadatas=[checksum_dict],
            )

        except Exception as e:
            # Safe failure: checksum will be recalculated on next sync
            # Don't break incremental sync, but log for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Failed to store checksum for {file_path}: {e}. "
                f"File will be re-indexed on next incremental sync."
            )
            # Continue without raising to avoid breaking sync process

    def get_file_checksums_batch(self, file_paths: list[str]) -> dict[str, str]:
        """
        Get cached checksums for multiple files in a single query.

        Performance optimization: Reduces DB round-trips from N queries to 1 query.

        Args:
            file_paths: List of file paths to get checksums for

        Returns:
            Dictionary mapping file_path to checksum (only includes files with cached checksums)

        Raises:
            StorageError: If retrieval fails
        """
        if not self.client or "meta" not in self.collections:
            return {}

        if not file_paths:
            return {}

        try:
            collection = self.collections["meta"]

            # Generate IDs for all file paths
            checksum_ids = [f"checksum_{fp}" for fp in file_paths]

            # Single batch query
            result = collection.get(
                ids=checksum_ids,
                include=["metadatas"],
            )

            # Build result dict
            checksums: dict[str, str] = {}
            if result["ids"]:
                metadatas = result.get("metadatas")
                if metadatas:
                    for i, metadata in enumerate(metadatas):
                        if metadata and "file_path" in metadata and "file_checksum" in metadata:
                            file_path = str(metadata["file_path"])
                            file_checksum = str(metadata["file_checksum"])
                            checksums[file_path] = file_checksum

            return checksums

        except Exception:
            # Return empty dict on error to avoid breaking incremental sync
            return {}

    def _format_results(self, results: dict[str, Any]) -> list[dict[str, Any]]:
        """Format ChromaDB query results."""
        formatted: list[dict[str, Any]] = []

        ids = results.get("ids", [[]])[0] if results.get("ids") else []
        if not ids:
            return formatted

        distances = results.get("distances", [[]])[0] if results.get("distances") else []
        metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
        documents = results.get("documents", [[]])[0] if results.get("documents") else []

        for i, id_val in enumerate(ids):
            distance = distances[i] if i < len(distances) else 0.0
            # Convert distance to similarity score (cosine distance: 0-2, score: 0-1)
            score = max(0.0, 1.0 - (distance / 2.0))

            result = {
                "id": id_val,
                "distance": distance,
                "score": score,
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "document": documents[i] if i < len(documents) else "",
            }
            formatted.append(result)

        return formatted
