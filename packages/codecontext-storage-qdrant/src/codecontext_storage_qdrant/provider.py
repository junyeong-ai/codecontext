"""Qdrant storage provider with native hybrid search."""

import base64
import hashlib
import json
import logging
import time
from typing import Any, Optional, TYPE_CHECKING, cast
from uuid import UUID

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    PointStruct,
    Prefetch,
    ScoredPoint,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from codecontext_core import VectorStore, BM25FEncoder
from codecontext_core.exceptions import StorageError
from codecontext_core.models.core import (
    CodeObject,
    DocumentNode,
    FileChecksum,
    IndexState,
    Language,
    NodeType,
    ObjectType,
    Relationship,
)

if TYPE_CHECKING:
    from codecontext_core.interfaces import EmbeddingProvider
    from codecontext.config.schema import FieldWeights

logger = logging.getLogger(__name__)


class QdrantProvider(VectorStore):
    def __init__(
        self,
        config: Any,
        project_id: str,
        field_weights: "FieldWeights",
        embedding_provider: "EmbeddingProvider | None" = None,
    ) -> None:
        super().__init__(config, project_id)

        self.mode = getattr(config, "mode", "embedded")
        self.storage_path = getattr(config, "path", "~/.codecontext/data")
        self.url = getattr(config, "url", None)
        self.api_key = getattr(config, "api_key", None)
        self.collection_name = project_id

        self.client: QdrantClient | None = None
        self.embedding_provider = embedding_provider
        self.field_weights = field_weights

        # Fusion configuration
        fusion_method = getattr(config, "fusion_method", "weighted")
        self.fusion_method = (
            fusion_method.value if hasattr(fusion_method, "value") else fusion_method
        )
        self.prefetch_ratio_dense = getattr(config, "prefetch_ratio_dense", 5.0)
        self.prefetch_ratio_sparse = getattr(config, "prefetch_ratio_sparse", 3.0)

        self.enable_performance_logging = getattr(config, "enable_performance_logging", False)
        self.vector_size: int | None = None
        self.upsert_batch_size = getattr(config, "upsert_batch_size", 100)

        # BM25F encoder
        weights = {
            "name": float(field_weights.name),
            "qualified_name": float(field_weights.qualified_name),
            "signature": float(field_weights.signature),
            "docstring": float(field_weights.docstring),
            "content": float(field_weights.content),
            "filename": float(field_weights.filename),
            "file_path": float(field_weights.file_path),
        }
        self.bm25_encoder = BM25FEncoder(
            field_weights=weights,
            k1=getattr(field_weights, "k1", 1.2),
            b=getattr(field_weights, "b", 0.75),
            avg_dl=getattr(field_weights, "avg_dl", 100.0),
        )

    def set_client(self, client: QdrantClient) -> None:
        """Set external Qdrant client (for remote mode reuse)."""
        self.client = client
        logger.debug(f"Injected external Qdrant client for collection: {self.collection_name}")

    def initialize(self) -> None:
        try:
            if self.mode == "embedded":
                from pathlib import Path

                storage_path = Path(self.storage_path).expanduser() / self.collection_name
                storage_path.mkdir(parents=True, exist_ok=True)
                self.client = QdrantClient(path=str(storage_path))
                logger.info(f"Qdrant initialized (embedded): {storage_path}")
            else:
                self.client = QdrantClient(url=self.url, api_key=self.api_key)
                logger.info(f"Qdrant initialized (remote): {self.url}")

            if self.client.collection_exists(self.collection_name):
                collection_info = self.client.get_collection(self.collection_name)
                vectors = collection_info.config.params.vectors
                if isinstance(vectors, dict) and "dense" in vectors:
                    self.vector_size = vectors["dense"].size
                    logger.info(f"Read vector dimension from collection: {self.vector_size}")
                else:
                    raise StorageError("Collection exists but dense vector config not found")
            else:
                if not self.embedding_provider:
                    raise StorageError("Embedding provider required to create new collection")
                test_embedding = self.embedding_provider.embed_text("test")
                self.vector_size = len(test_embedding)
                logger.info(f"Detected vector dimension: {self.vector_size}")
                self._create_collection()

            logger.info(f"Collection: {self.collection_name}")

        except Exception as e:
            raise StorageError(f"Failed to initialize Qdrant: {e}") from e

    def _create_collection(self) -> None:
        """Create Qdrant collection with dense and sparse vectors.

        Sparse vectors use IDF modifier for complete BM25 implementation.
        Qdrant 1.10+ computes IDF automatically in real-time.
        """
        if not self.client or not self.vector_size:
            raise StorageError("Client not initialized or vector size not set")

        from qdrant_client.models import Modifier

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={"dense": VectorParams(size=self.vector_size, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams(modifier=Modifier.IDF)},
        )
        logger.info(f"Created collection with IDF modifier: {self.collection_name}")

    def _encode_sparse(self, text: str) -> SparseVector:
        indices, values = self.bm25_encoder.encode_query(text)
        return SparseVector(indices=indices, values=values)

    def _code_object_to_sparse(self, obj: CodeObject) -> SparseVector:
        filename = ""
        if obj.file_path:
            filename = (
                obj.file_path.split("/")[-1]
                if isinstance(obj.file_path, str)
                else obj.file_path.name
            )

        doc = {
            "name": obj.name,
            "qualified_name": obj.qualified_name,
            "signature": obj.signature,
            "docstring": obj.docstring,
            "content": obj.content,
            "filename": filename,
            "file_path": str(obj.file_path) if obj.file_path else "",
        }

        indices, values = self.bm25_encoder.encode(doc)
        return SparseVector(indices=indices, values=values)

    def _document_to_sparse(self, doc: DocumentNode) -> SparseVector:
        doc_dict: dict[str, str | None] = {
            "name": doc.title or "",
            "content": doc.content or "",
            "file_path": doc.file_path or "",
        }

        doc_encoder = BM25FEncoder(
            field_weights={"name": 5.0, "content": 5.0, "file_path": 2.0},
            k1=self.bm25_encoder.k1,
            b=self.bm25_encoder.b,
            avg_dl=self.bm25_encoder.avg_dl,
        )

        indices, values = doc_encoder.encode(doc_dict)
        return SparseVector(indices=indices, values=values)

    def add_code_objects(
        self, objects: list[CodeObject], relationships: list[Relationship] | None = None
    ) -> None:
        if not self.client or not objects:
            return

        try:
            rel_by_source: dict[str, list[dict[str, Any]]] = {}
            if relationships:
                for rel in relationships:
                    source_key = str(rel.source_id)
                    if source_key not in rel_by_source:
                        rel_by_source[source_key] = []
                    rel_by_source[source_key].append(rel.to_metadata())

            points = []
            for obj in objects:
                if not obj.embedding:
                    continue

                sparse_vector = self._code_object_to_sparse(obj)
                payload = obj.to_metadata()

                obj_id = obj.deterministic_id
                if obj_id in rel_by_source:
                    payload["relationships"] = rel_by_source[obj_id]

                point = PointStruct(
                    id=obj_id,
                    vector={"dense": obj.embedding, "sparse": sparse_vector},
                    payload=payload,
                )
                points.append(point)

            for i in range(0, len(points), self.upsert_batch_size):
                batch = points[i : i + self.upsert_batch_size]
                self.client.upsert(collection_name=self.collection_name, points=batch, wait=True)

        except Exception as e:
            raise StorageError(f"Failed to add code objects: {e}") from e

    def add_documents(self, documents: list[DocumentNode]) -> None:
        if not self.client or not documents:
            return

        try:
            points = []
            for doc in documents:
                if not doc.embedding:
                    continue

                sparse_vector = self._document_to_sparse(doc)
                payload = doc.to_metadata()

                point = PointStruct(
                    id=doc.deterministic_id,
                    vector={"dense": doc.embedding, "sparse": sparse_vector},
                    payload=payload,
                )
                points.append(point)

            for i in range(0, len(points), self.upsert_batch_size):
                batch = points[i : i + self.upsert_batch_size]
                self.client.upsert(collection_name=self.collection_name, points=batch)

            logger.debug(f"Added {len(documents)} documents")

        except Exception as e:
            raise StorageError(f"Failed to add documents: {e}") from e

    def _search_hybrid(
        self,
        query_embedding: list[float],
        query_text: str,
        limit: int,
        type_filter: str | None = None,
        language_filter: str | None = None,
        file_filter: str | None = None,
    ) -> list[ScoredPoint]:
        """Hybrid search using Qdrant native fusion (RRF or DBSF) with asymmetric prefetch."""
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            start_time = time.time()
            sparse_vector = self._encode_sparse(query_text)

            filter_conditions = []
            if type_filter:
                filter_conditions.append(
                    FieldCondition(key="type", match=MatchValue(value=type_filter))
                )
            if language_filter:
                filter_conditions.append(
                    FieldCondition(key="language", match=MatchValue(value=language_filter))
                )
            if file_filter:
                filter_conditions.append(
                    FieldCondition(key="file_path", match=MatchValue(value=file_filter))
                )

            query_filter = Filter(must=cast(Any, filter_conditions)) if filter_conditions else None

            dense_prefetch = int(limit * self.prefetch_ratio_dense)
            sparse_prefetch = int(limit * self.prefetch_ratio_sparse)

            fusion_type = Fusion.RRF if self.fusion_method == "rrf" else Fusion.DBSF

            results = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    Prefetch(
                        using="dense",
                        query=query_embedding,
                        limit=dense_prefetch,
                        filter=query_filter,
                    ),
                    Prefetch(
                        using="sparse",
                        query=sparse_vector,
                        limit=sparse_prefetch,
                        filter=query_filter,
                    ),
                ],
                query=FusionQuery(fusion=fusion_type),
                limit=limit,
                with_vectors=True,
            )

            if self.enable_performance_logging:
                elapsed = time.time() - start_time
                logger.info(
                    f"Hybrid search ({fusion_type.value}): {elapsed:.3f}s, dense_prefetch={dense_prefetch}, sparse_prefetch={sparse_prefetch}"
                )

            return list(results.points)

        except Exception as e:
            raise StorageError(f"Hybrid search failed: {e}") from e

    def search_code_objects(
        self,
        query_embedding: list[float],
        limit: int = 10,
        language_filter: Optional[str] = None,
        file_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        results = self._search_hybrid(
            query_embedding=query_embedding,
            query_text="",
            limit=limit,
            type_filter="code",
            language_filter=language_filter,
            file_filter=file_filter,
        )

        return [
            {"id": point.id, "score": point.score, **(point.payload or {})} for point in results
        ]

    def search_documents(
        self,
        query_embedding: list[float],
        limit: int = 10,
        language_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        results = self._search_hybrid(
            query_embedding=query_embedding,
            query_text="",
            limit=limit,
            type_filter="document",
            language_filter=language_filter,
        )

        return [
            {"id": point.id, "score": point.score, **(point.payload or {})} for point in results
        ]

    def get_code_object(self, object_id: str) -> Optional[CodeObject]:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            result = self.client.retrieve(
                collection_name=self.collection_name, ids=[object_id], with_vectors=True
            )

            if not result:
                return None

            point = result[0]
            payload = point.payload
            if not payload:
                return None

            embedding: list[float] | None = None
            if point.vector:
                if isinstance(point.vector, dict) and "dense" in point.vector:
                    dense_vec = point.vector["dense"]
                    if isinstance(dense_vec, list) and all(
                        isinstance(x, float) for x in dense_vec[:1]
                    ):
                        embedding = cast(list[float], dense_vec)
                elif isinstance(point.vector, list) and all(
                    isinstance(x, float) for x in point.vector[:1]
                ):
                    embedding = cast(list[float], point.vector)

            point_id = UUID(point.id) if isinstance(point.id, str) else point.id
            if not isinstance(point_id, UUID):
                return None

            return CodeObject(
                id=point_id,
                file_path=str(payload["file_path"]),
                relative_path=str(payload.get("relative_path", payload["file_path"])),
                object_type=ObjectType(str(payload["object_type"])),
                name=str(payload["name"]),
                language=Language(str(payload["language"])),
                start_line=int(payload["start_line"]),
                end_line=int(payload["end_line"]),
                content=str(payload["content"]),
                checksum=str(payload.get("checksum", "")),
                signature=str(payload.get("signature")) if payload.get("signature") else None,
                docstring=str(payload.get("docstring")) if payload.get("docstring") else None,
                embedding=embedding,
            )

        except Exception as e:
            raise StorageError(f"Failed to get code object: {e}") from e

    def get_document(self, document_id: str) -> Optional[DocumentNode]:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            result = self.client.retrieve(collection_name=self.collection_name, ids=[document_id])

            if not result:
                return None

            point = result[0]
            payload = point.payload
            if not payload:
                return None

            point_id = UUID(point.id) if isinstance(point.id, str) else point.id
            if not isinstance(point_id, UUID):
                return None

            embedding: list[float] | None = None
            if point.vector and isinstance(point.vector, dict):
                dense_vec = point.vector.get("dense")
                if isinstance(dense_vec, list) and all(isinstance(x, float) for x in dense_vec[:1]):
                    embedding = cast(list[float], dense_vec)

            node_type_str = payload.get("node_type", "markdown")
            node_type = NodeType(str(node_type_str)) if node_type_str else NodeType.MARKDOWN

            return DocumentNode(
                id=point_id,
                file_path=str(payload["file_path"]),
                relative_path=str(payload.get("relative_path", "")),
                node_type=node_type,
                content=str(payload["content"]),
                checksum=str(payload.get("checksum", "")),
                title=str(payload.get("title")) if payload.get("title") else None,
                language=str(payload.get("language")) if payload.get("language") else None,
                chunk_index=int(payload.get("chunk_index", 0)),
                total_chunks=int(payload.get("total_chunks", 1)),
                embedding=embedding,
            )

        except Exception as e:
            raise StorageError(f"Failed to get document: {e}") from e

    def get_documents_batch(self, document_ids: list[str]) -> list[DocumentNode]:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            results = self.client.retrieve(collection_name=self.collection_name, ids=document_ids)

            documents = []
            for point in results:
                payload = point.payload
                if not payload:
                    continue

                point_id = UUID(point.id) if isinstance(point.id, str) else point.id
                if not isinstance(point_id, UUID):
                    continue

                embedding: list[float] | None = None
                if point.vector and isinstance(point.vector, dict):
                    dense_vec = point.vector.get("dense")
                    if isinstance(dense_vec, list) and all(
                        isinstance(x, float) for x in dense_vec[:1]
                    ):
                        embedding = cast(list[float], dense_vec)

                node_type_str = payload.get("node_type", "markdown")
                node_type = NodeType(str(node_type_str)) if node_type_str else NodeType.MARKDOWN

                doc = DocumentNode(
                    id=point_id,
                    file_path=str(payload["file_path"]),
                    relative_path=str(payload.get("relative_path", "")),
                    node_type=node_type,
                    content=str(payload["content"]),
                    checksum=str(payload.get("checksum", "")),
                    title=str(payload.get("title")) if payload.get("title") else None,
                    language=str(payload.get("language")) if payload.get("language") else None,
                    chunk_index=int(payload.get("chunk_index", 0)),
                    total_chunks=int(payload.get("total_chunks", 1)),
                    embedding=embedding,
                )
                documents.append(doc)

            return documents

        except Exception as e:
            raise StorageError(f"Failed to get documents batch: {e}") from e

    def get_code_objects_batch(
        self, object_ids: list[str], include_vectors: bool = False
    ) -> list[CodeObject]:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            results = self.client.retrieve(
                collection_name=self.collection_name, ids=object_ids, with_vectors=include_vectors
            )

            objects = []
            for point in results:
                payload = point.payload
                if not payload:
                    continue

                point_id = UUID(point.id) if isinstance(point.id, str) else point.id
                if not isinstance(point_id, UUID):
                    continue

                embedding: list[float] | None = None
                if include_vectors and point.vector:
                    if isinstance(point.vector, dict) and "dense" in point.vector:
                        dense_vec = point.vector["dense"]
                        if isinstance(dense_vec, list) and all(
                            isinstance(x, float) for x in dense_vec[:1]
                        ):
                            embedding = cast(list[float], dense_vec)
                    elif isinstance(point.vector, list) and all(
                        isinstance(x, float) for x in point.vector[:1]
                    ):
                        embedding = cast(list[float], point.vector)

                obj = CodeObject(
                    id=point_id,
                    file_path=str(payload["file_path"]),
                    relative_path=str(payload.get("relative_path", payload["file_path"])),
                    object_type=ObjectType(str(payload["object_type"])),
                    name=str(payload["name"]),
                    language=Language(str(payload["language"])),
                    start_line=int(payload["start_line"]),
                    end_line=int(payload["end_line"]),
                    content=str(payload["content"]),
                    checksum=str(payload.get("checksum", "")),
                    signature=str(payload.get("signature")) if payload.get("signature") else None,
                    docstring=str(payload.get("docstring")) if payload.get("docstring") else None,
                    embedding=embedding,
                )
                objects.append(obj)

            return objects

        except Exception as e:
            raise StorageError(f"Failed to get code objects batch: {e}") from e

    def get_all_documents(self, limit: int = 10000) -> list[DocumentNode]:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=cast(Any, [FieldCondition(key="type", match=MatchValue(value="document"))])
                ),
                limit=limit,
                with_payload=True,
                with_vectors=True,
            )[0]

            documents = []
            for point in results:
                payload = point.payload
                if not payload:
                    continue

                point_id = UUID(point.id) if isinstance(point.id, str) else point.id
                if not isinstance(point_id, UUID):
                    continue

                embedding: list[float] | None = None
                if point.vector and isinstance(point.vector, dict):
                    dense_vec = point.vector.get("dense")
                    if isinstance(dense_vec, list) and all(
                        isinstance(x, float) for x in dense_vec[:1]
                    ):
                        embedding = cast(list[float], dense_vec)

                node_type_str = payload.get("node_type", "markdown")
                node_type = NodeType(str(node_type_str)) if node_type_str else NodeType.MARKDOWN

                doc = DocumentNode(
                    id=point_id,
                    file_path=str(payload["file_path"]),
                    relative_path=str(payload.get("relative_path", "")),
                    node_type=node_type,
                    content=str(payload["content"]),
                    checksum=str(payload.get("checksum", "")),
                    title=str(payload.get("title")) if payload.get("title") else None,
                    language=str(payload.get("language")) if payload.get("language") else None,
                    chunk_index=int(payload.get("chunk_index", 0)),
                    total_chunks=int(payload.get("total_chunks", 1)),
                    embedding=embedding,
                )
                documents.append(doc)

            return documents

        except Exception as e:
            raise StorageError(f"Failed to get all documents: {e}") from e

    def get_relationships(
        self, source_id: str, relation_type: Optional[str] = None
    ) -> list[Relationship]:
        if not self.client:
            return []

        try:
            result = self.client.retrieve(collection_name=self.collection_name, ids=[source_id])
            if not result or not result[0].payload:
                return []

            rels_data = result[0].payload.get("relationships", [])
            relationships = [Relationship.from_metadata(r) for r in rels_data]

            if relation_type:
                relationships = [r for r in relationships if r.relation_type.value == relation_type]

            return relationships
        except Exception:
            return []

    def delete_code_objects(self, object_ids: list[UUID]) -> None:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[str(oid) for oid in object_ids],
            )
        except Exception as e:
            raise StorageError(f"Failed to delete code objects: {e}") from e

    def delete_code_objects_by_file(self, file_path: str) -> int:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            filter_condition = Filter(
                must=[
                    FieldCondition(key="type", match=MatchValue(value="code")),
                    FieldCondition(key="file_path", match=MatchValue(value=file_path)),
                ]
            )

            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_condition,
                limit=10000,
                with_payload=False,
            )[0]

            if results:
                ids = [point.id for point in results]
                self.client.delete(collection_name=self.collection_name, points_selector=ids)
                return len(ids)

            return 0

        except Exception as e:
            raise StorageError(f"Failed to delete code objects by file: {e}") from e

    def delete(self, ids: list[str]) -> int:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            self.client.delete(collection_name=self.collection_name, points_selector=ids)
            return len(ids)
        except Exception as e:
            raise StorageError(f"Failed to delete: {e}") from e

    def delete_documents(self, document_ids: list[UUID]) -> None:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[str(did) for did in document_ids],
            )
        except Exception as e:
            raise StorageError(f"Failed to delete documents: {e}") from e

    def get_file_checksum(self, file_path: str) -> Optional[Any]:
        data = self._get_state(f"checksum_{file_path}")
        if data:
            metadata = json.loads(data.decode("utf-8"))
            return FileChecksum.from_metadata(metadata)
        return None

    def set_file_checksum(self, file_checksum: Any) -> None:
        key = f"checksum_{file_checksum.file_path}"
        self._set_state(key, json.dumps(file_checksum.to_metadata()).encode("utf-8"))

    def get_file_checksums_batch(self, file_paths: list[str]) -> dict[str, str]:
        """Get file checksums for multiple files in batch.

        Args:
            file_paths: List of file paths

        Returns:
            Dictionary mapping file_path to file_checksum
        """
        result = {}
        for file_path in file_paths:
            checksum_obj = self.get_file_checksum(file_path)
            if checksum_obj:
                result[file_path] = checksum_obj.file_checksum
        return result

    def get_code_objects_by_file(self, file_path: str) -> list[CodeObject]:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="type", match=MatchValue(value="code")),
                        FieldCondition(key="file_path", match=MatchValue(value=file_path)),
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=True,
            )[0]

            objects = []
            for point in results:
                payload = point.payload
                if not payload:
                    continue

                point_id = UUID(point.id) if isinstance(point.id, str) else point.id
                if not isinstance(point_id, UUID):
                    continue

                embedding: list[float] | None = None
                if point.vector and isinstance(point.vector, dict):
                    dense_vec = point.vector.get("dense")
                    if isinstance(dense_vec, list) and all(
                        isinstance(x, float) for x in dense_vec[:1]
                    ):
                        embedding = cast(list[float], dense_vec)

                obj = CodeObject(
                    id=point_id,
                    file_path=str(payload["file_path"]),
                    relative_path=str(payload.get("relative_path", payload["file_path"])),
                    object_type=ObjectType(str(payload["object_type"])),
                    name=str(payload["name"]),
                    language=Language(str(payload["language"])),
                    start_line=int(payload["start_line"]),
                    end_line=int(payload["end_line"]),
                    content=str(payload["content"]),
                    checksum=str(payload.get("checksum", "")),
                    signature=str(payload.get("signature")) if payload.get("signature") else None,
                    docstring=str(payload.get("docstring")) if payload.get("docstring") else None,
                    embedding=embedding,
                )
                objects.append(obj)

            return objects

        except Exception as e:
            raise StorageError(f"Failed to get code objects by file: {e}") from e

    def get_indexed_file_paths(self) -> set[str]:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=cast(Any, [FieldCondition(key="type", match=MatchValue(value="code"))])
                ),
                limit=10000,
                with_payload=["file_path"],
                with_vectors=False,
            )[0]

            return {point.payload["file_path"] for point in results if point.payload}

        except Exception as e:
            raise StorageError(f"Failed to get indexed file paths: {e}") from e

    def get_index_state(self) -> Optional[Any]:
        data = self._get_state("index_state")
        if data:
            metadata = json.loads(data.decode("utf-8"))
            return IndexState.from_metadata(metadata)
        return None

    def update_index_state(self, state: Any) -> None:
        data = json.dumps(state.to_metadata()).encode("utf-8")
        self._set_state("index_state", data)

        saved_data = self._get_state("index_state")
        if not saved_data:
            raise StorageError("Index state verification failed: state not found after save")

        logger.info(
            f"Index state updated: {state.project_id} (commit: {state.last_commit_hash[:8] if state.last_commit_hash else 'none'})"
        )

    def get_statistics(self) -> dict[str, Any]:
        if not self.client:
            raise StorageError("Client not initialized")

        try:
            collection_info = self.client.get_collection(self.collection_name)

            code_count = self.client.count(
                collection_name=self.collection_name,
                count_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="code"))]
                ),
            ).count

            doc_count = self.client.count(
                collection_name=self.collection_name,
                count_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="document"))]
                ),
            ).count

            return {
                "total_count": collection_info.points_count,
                "content_count": code_count,
                "meta_count": doc_count,
            }

        except Exception as e:
            raise StorageError(f"Failed to get statistics: {e}") from e

    def _get_state(self, key: str) -> bytes | None:
        if not self.client:
            return None

        point_id = int.from_bytes(
            hashlib.sha256(f"state_{key}".encode()).digest()[:8], byteorder="big", signed=False
        )
        try:
            result = self.client.retrieve(collection_name=self.collection_name, ids=[point_id])
            if result and result[0].payload and result[0].payload.get("data"):
                return base64.b64decode(result[0].payload["data"])
            return None
        except Exception:
            return None

    def _set_state(self, key: str, value: bytes) -> None:
        if not self.client:
            raise StorageError("Client not initialized")
        if not self.vector_size:
            raise StorageError("Vector size not initialized")

        point_id = int.from_bytes(
            hashlib.sha256(f"state_{key}".encode()).digest()[:8], byteorder="big", signed=False
        )
        try:
            point = PointStruct(
                id=point_id,
                vector={"dense": [0.0] * self.vector_size},
                payload={"type": "state", "data": base64.b64encode(value).decode("utf-8")},
            )
            self.client.upsert(collection_name=self.collection_name, points=[point], wait=True)
            logger.debug(f"State '{key}' saved (point_id={point_id})")
        except Exception as e:
            raise StorageError(f"Failed to set state '{key}': {e}") from e

    def get_state(self, key: str) -> bytes | None:
        return self._get_state(key)

    def set_state(self, key: str, value: bytes) -> None:
        self._set_state(key, value)

    def delete_state(self, key: str) -> None:
        if not self.client:
            logger.warning("Client not initialized, cannot delete state")
            return

        state_key = f"state_{key}"
        try:
            self.client.delete(collection_name=self.collection_name, points_selector=[state_key])
        except Exception as e:
            logger.warning(f"Failed to delete state: {e}")

    def close(self) -> None:
        if self.client:
            self.client.close()
            logger.info("Qdrant connection closed")

    @staticmethod
    def _normalize_zscore(scores: np.ndarray) -> np.ndarray:
        """Z-score normalization, map to [0, 1] using ±3σ bounds."""
        if len(scores) == 0:
            return scores
        mean, std = scores.mean(), scores.std()
        if std == 0:
            return np.full_like(scores, 0.5, dtype=np.float32)
        z = (scores - mean) / std
        result: np.ndarray = np.clip((z + 3) / 6, 0, 1).astype(np.float32)
        return result
