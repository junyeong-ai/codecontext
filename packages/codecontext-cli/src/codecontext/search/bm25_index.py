"""Unified BM25 index with document type awareness.

Clean Architecture (no legacy code):
- Single BM25 corpus for all documents (code + documents)
- Type-aware field weighting profiles
- O(1) type lookup via dict
- Qualified name boosting for code
- Header/keyword boosting for documents

Design Principles:
- SRP: Single responsibility - BM25 indexing and search
- DRY: No code duplication
- Type Safety: Complete type hints
- Extensibility: Easy to add new document types
"""

from collections import defaultdict
from typing import Any, Literal

import bm25s

import logging

from codecontext.search.tokenizer import CodeTokenizer
from codecontext.search.utils import validate_bm25_results

logger = logging.getLogger(__name__)

FIELD_PROFILES = {
    "code": {
        "qualified_name": 10.0,
        "docstring": 8.0,
        "signature": 6.0,
        "name": 5.5,
        "content": 3.5,
        "parent_context": 3.0,
        "file_path": 2.0,
    },
    "document": {
        "title": 5.0,
        "headers": 4.5,
        "content": 5.0,
        "file_path": 2.0,
    },
}


class BM25Index:
    """Unified BM25 index with multi-document-type support.

    Architecture:
    - Single corpus for all document types
    - Type-aware field weighting
    - O(1) lookups via dict
    - Extensible via FIELD_PROFILES

    Example:
        >>> index = BM25Index()
        >>> index.add_documents([{"id": "1", "name": "foo"}], doc_type="code")
        >>> index.add_documents([{"id": "2", "title": "bar"}], doc_type="document")
        >>> results = index.search("foo", filter_type="code")
    """

    def __init__(
        self,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> None:
        """Initialize BM25 index.

        Args:
            k1: Term saturation parameter (1.2 standard)
            b: Length normalization parameter (0.75 standard)
        """
        self.k1 = k1
        self.b = b

        # Index data
        self.documents: list[dict[str, Any]] = []
        self.doc_ids: list[str] = []
        self.doc_types: list[Literal["code", "document"]] = []
        self.corpus_tokens: list[list[str]] = []
        self.retriever: Any = None  # bm25s.BM25 instance

        # Fast lookups (O(1))
        self.id_to_idx: dict[str, int] = {}
        self.type_to_indices: dict[str, set[int]] = defaultdict(set)

        # Code-specific: qualified name index for boosting
        self.qualified_name_index: dict[str, set[int]] = defaultdict(set)

        logger.debug(f"Initialized BM25Index (k1={k1}, b={b})")

    def add_documents(
        self,
        documents: list[dict[str, Any]],
        doc_type: Literal["code", "document"],
    ) -> None:
        """Add documents to index with explicit type.

        Args:
            documents: List of documents with fields like:
                - id: unique identifier (required)
                - For code: name, qualified_name, signature, docstring, content, file_path
                - For documents: title, keywords, headers, summary, content, file_path
            doc_type: Document type ("code" or "document")

        Raises:
            ValueError: If document is missing required fields
        """
        if not documents:
            logger.warning("No documents to add")
            return

        field_profile = FIELD_PROFILES[doc_type]

        for doc in documents:
            if "id" not in doc:
                raise ValueError(f"Document missing 'id' field: {doc}")

            idx = len(self.documents)
            doc_id = doc["id"]

            # Store document and metadata
            self.documents.append(doc)
            self.doc_ids.append(doc_id)
            self.doc_types.append(doc_type)

            # Fast lookups
            self.id_to_idx[doc_id] = idx
            self.type_to_indices[doc_type].add(idx)

            # Tokenize with type-specific profile
            tokens = self._tokenize_with_profile(doc, field_profile)
            self.corpus_tokens.append(tokens)

            # Code-specific: index qualified name
            if doc_type == "code" and "qualified_name" in doc:
                self._index_qualified_name(doc["qualified_name"], idx)

        # Rebuild BM25 index
        self._rebuild_index()

        logger.debug(
            f"Indexed {len(documents)} {doc_type} documents "
            f"(total: {len(self.documents)} documents)"
        )

    def _tokenize_with_profile(
        self, doc: dict[str, Any], field_profile: dict[str, float]
    ) -> list[str]:
        """Tokenize document with field-weighted repetition.

        Args:
            doc: Document dictionary
            field_profile: Field weights for this document type

        Returns:
            List of tokens with field-weighted repetition
        """
        return CodeTokenizer.tokenize_document(doc, field_profile)

    def _index_qualified_name(self, qualified_name: str, doc_idx: int) -> None:
        """Index qualified name segments for code boosting.

        Segments UserService.authenticate into:
        - "userservice.authenticate" (full)
        - "userservice" (parent)
        - "authenticate" (method)

        Args:
            qualified_name: Qualified name (e.g., "UserService.authenticate")
            doc_idx: Document index
        """
        if not qualified_name:
            return

        # Full qualified name (lowercase for case-insensitive matching)
        self.qualified_name_index[qualified_name.lower()].add(doc_idx)

        # All segments and partial qualified names
        segments = qualified_name.split(".")
        for i in range(len(segments)):
            # Progressively shorter: a.b.c → [a.b.c, b.c, c]
            partial = ".".join(segments[i:])
            self.qualified_name_index[partial.lower()].add(doc_idx)

            # Individual segments: [a, b, c]
            self.qualified_name_index[segments[i].lower()].add(doc_idx)

    def _rebuild_index(self) -> None:
        """Rebuild BM25 index from corpus."""
        if not self.corpus_tokens:
            logger.warning("No documents to index")
            return

        # Create BM25 instance
        self.retriever = bm25s.BM25(k1=self.k1, b=self.b)

        # Build index
        self.retriever.index(self.corpus_tokens)

        logger.debug(
            f"Built BM25 index: {len(self.documents)} docs, "
            f"{len(self.qualified_name_index)} qualified names"
        )

    def search(
        self,
        query: str,
        limit: int = 20,
        filter_type: Literal["code", "document", "all"] = "all",
        boost_qualified_names: bool = True,
    ) -> list[tuple[str, float]]:
        """Search with optional type filtering and code boosting.

        Args:
            query: Search query text
            limit: Maximum results to return
            filter_type: Filter by document type ("code", "document", or "all")
            boost_qualified_names: Apply qualified name boost for code (default True)

        Returns:
            List of (doc_id, score) tuples sorted by score (descending)

        Examples:
            >>> index.search("UserService", filter_type="code")
            [("code_1", 0.95), ("code_2", 0.82)]
            >>> index.search("authentication", filter_type="all")
            [("code_1", 0.88), ("doc_1", 0.65)]
        """
        if not self.retriever:
            logger.warning("Index not built")
            return []

        # Tokenize query
        query_tokens = CodeTokenizer.tokenize_text(query)
        if not query_tokens:
            logger.warning(f"Query tokenized to empty: {query!r}")
            return []

        # BM25 search (request more than limit to handle filtering)
        # bm25s.retrieve() returns bm25s.Results object: (indices, scores) NOT (scores, indices)!
        # See: Result[0] contains int64 indices, Result[1] contains float32 scores
        # Cap k to corpus size to avoid bm25s ValueError
        corpus_size = len(self.doc_ids)
        effective_k = min(limit * 3, corpus_size) if corpus_size > 0 else limit
        indices, scores = self.retriever.retrieve([query_tokens], k=effective_k)

        # Safe conversion (numpy → Python types)
        valid_indices, valid_scores = validate_bm25_results(
            indices, scores, max_index=len(self.doc_ids)
        )

        # Filter by type and apply boosting
        results = []
        for idx, score in zip(valid_indices, valid_scores):
            # Type filter
            if filter_type != "all" and self.doc_types[idx] != filter_type:
                continue

            doc_id = self.doc_ids[idx]
            final_score = score

            # Code-specific: qualified name boost
            if boost_qualified_names and self.doc_types[idx] == "code":
                boost = self._compute_qualified_name_boost(query, idx)
                final_score *= 1.0 + boost

            results.append((doc_id, final_score))

        # Re-sort after boosting
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top results
        return results[:limit]

    def _compute_qualified_name_boost(self, query: str, doc_idx: int) -> float:
        """Compute boost factor for qualified name matches.

        Boost strategy:
        - Exact qualified name match (e.g., "UserService.authenticate"): 100% boost (1.0)
        - Segment match (e.g., "authenticate" in "UserService.authenticate"): 30% boost (0.3)

        Args:
            query: Search query (case-insensitive)
            doc_idx: Document index

        Returns:
            Boost factor between 0.0 and 1.0
        """
        query_lower = query.lower()
        max_boost = 0.0

        # Exact qualified name match (with dot notation)
        if "." in query_lower:
            if doc_idx in self.qualified_name_index.get(query_lower, set()):
                return 1.0  # 100% boost for exact qualified name

        # Segment matches
        query_segments = query_lower.replace(".", " ").split()
        for segment in query_segments:
            if len(segment) > 2:  # Skip very short segments
                if doc_idx in self.qualified_name_index.get(segment, set()):
                    max_boost = max(max_boost, 0.3)  # 30% boost for segment match

        return max_boost

    def search_multi(
        self,
        queries: list[str],
        limit: int = 20,
        filter_type: Literal["code", "document", "all"] = "all",
        boost_qualified_names: bool = True,
    ) -> list[tuple[str, float]]:
        """Multi-query BM25 search with result fusion.

        Searches with multiple query variants and fuses results by taking
        the maximum score for each document.

        Args:
            queries: List of query variants (e.g., expanded terms)
            limit: Maximum results to return
            filter_type: Filter by document type
            boost_qualified_names: Apply qualified name boost for code

        Returns:
            List of (doc_id, score) tuples sorted by score (descending)

        Example:
            >>> variants = ["processOrder", "process_order", "process-order"]
            >>> results = index.search_multi(variants, limit=10)
        """
        if not queries:
            logger.warning("Empty query list provided")
            return []

        # Collect results from all query variants
        doc_scores: dict[str, float] = {}

        for query in queries:
            results = self.search(
                query=query,
                limit=limit * 2,  # Get more results for fusion
                filter_type=filter_type,
                boost_qualified_names=boost_qualified_names,
            )

            # Merge: take max score for each doc_id
            for doc_id, score in results:
                doc_scores[doc_id] = max(doc_scores.get(doc_id, 0.0), score)

        # Sort by score and return top results
        sorted_results = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return sorted_results[:limit]

    def get_document_type(self, doc_id: str) -> str | None:
        """Get document type (O(1) lookup).

        Args:
            doc_id: Document ID

        Returns:
            "code", "document", or None if not found
        """
        idx = self.id_to_idx.get(doc_id)
        if idx is None:
            return None
        return self.doc_types[idx]

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics.

        Returns:
            Dictionary with index statistics including:
            - total_documents: Total number of documents
            - code_documents: Number of code documents
            - text_documents: Number of text documents
            - total_tokens: Total number of tokens across all documents
            - qualified_names: Number of indexed qualified name entries
            - indexed: Whether BM25 index is built
        """
        return {
            "total_documents": len(self.documents),
            "code_documents": len(self.type_to_indices["code"]),
            "text_documents": len(self.type_to_indices["document"]),
            "total_tokens": sum(len(tokens) for tokens in self.corpus_tokens),
            "qualified_names": len(self.qualified_name_index),
            "indexed": self.retriever is not None,
        }

    def clear(self) -> None:
        """Clear all index data.

        Useful for resetting the index or freeing memory.
        """
        self.documents.clear()
        self.doc_ids.clear()
        self.doc_types.clear()
        self.corpus_tokens.clear()
        self.id_to_idx.clear()
        self.type_to_indices.clear()
        self.qualified_name_index.clear()
        self.retriever = None

        logger.info("Cleared BM25 index")

    def to_dict(self) -> dict[str, Any]:
        """Serialize index data to dictionary.

        Follows Lucene/Elasticsearch pattern: serialize data, not objects.
        The bm25s.BM25 retriever object is NOT serialized (can't be pickled reliably).
        Instead, we serialize the data and rebuild the retriever on load.

        Returns:
            Dictionary with index data
        """
        return {
            "k1": self.k1,
            "b": self.b,
            "documents": self.documents,
            "doc_ids": self.doc_ids,
            "doc_types": self.doc_types,
            "corpus_tokens": self.corpus_tokens,
            "id_to_idx": self.id_to_idx,
            "type_to_indices": {k: list(v) for k, v in self.type_to_indices.items()},
            "qualified_name_index": {k: list(v) for k, v in self.qualified_name_index.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BM25Index":
        """Deserialize index data from dictionary.

        Follows Lucene/Elasticsearch pattern: rebuild index from data.
        Recreates the bm25s.BM25 retriever from corpus_tokens.

        Args:
            data: Dictionary with index data (from to_dict())

        Returns:
            BM25Index instance with rebuilt retriever
        """
        index = cls(k1=data["k1"], b=data["b"])

        # Restore data structures
        index.documents = data["documents"]
        index.doc_ids = data["doc_ids"]
        index.doc_types = data["doc_types"]
        index.corpus_tokens = data["corpus_tokens"]
        index.id_to_idx = data["id_to_idx"]
        index.type_to_indices = defaultdict(
            set, {k: set(v) for k, v in data["type_to_indices"].items()}
        )
        index.qualified_name_index = defaultdict(
            set, {k: set(v) for k, v in data["qualified_name_index"].items()}
        )

        # Rebuild bm25s.BM25 retriever from corpus_tokens
        index._rebuild_index()

        return index
