"""Hybrid search retriever with BM25 + Vector fusion.

Architecture:
- BM25 for keyword matching
- Vector embeddings for semantic similarity
- Normalized linear fusion with config weights
- Graph expansion for context
- MMR reranking for diversity
"""

from pathlib import Path
from typing import Any

import numpy as np

from codecontext.config.schema import CodeContextConfig
from codecontext_core.exceptions import SearchError
from codecontext_core.models import (
    SearchQuery,
    SearchResult,
    SearchScoring,
)
from codecontext_core.interfaces import EmbeddingProvider, TranslationProvider
from codecontext.search.bm25_index_store import BM25IndexStore
from codecontext.search.bm25_index import BM25Index
from codecontext.search.diversity_filter import DiversityConfig, FileDiversityFilter
from codecontext.search.fusion import AdaptiveFusion
from codecontext.search.graph_expander import GraphExpander
from codecontext.search.mmr import MMRReranker
import logging

from codecontext.search.query_expander import QueryExpander
from codecontext_core import VectorStore

logger = logging.getLogger(__name__)


class SearchRetriever:
    """Hybrid search retriever with unified BM25 index and intent-aware routing.

    Architecture:
    1. Single BM25Index for both code and documents
    2. QueryRouter classifies intent
    3. Intent-aware search with adaptive weights
    4. Graph expansion for context
    5. MMR re-ranking for diversity

    Design Improvements:
    - Unified index (no duplicate indices)
    - O(1) type lookups
    - Simpler code paths
    - Better maintainability
    """

    def __init__(
        self,
        config: CodeContextConfig,
        embedding_provider: EmbeddingProvider,
        storage: VectorStore,
        translation_provider: TranslationProvider | None = None,
    ) -> None:
        """Initialize hybrid search retriever.

        Args:
            config: CodeContext configuration
            embedding_provider: Embedding provider
            storage: Vector storage
            translation_provider: Optional translation provider
        """
        self.config = config
        self.embedding_provider = embedding_provider
        self.storage = storage
        self.translation_provider = translation_provider

        # Initialize language detector if translation is enabled
        if self.translation_provider:
            from codecontext.utils.language import LanguageDetector

            self.language_detector = LanguageDetector()
        else:
            self.language_detector = None

        self.query_expander = QueryExpander()

        # BM25 index persistence layer
        self.index_store = BM25IndexStore(storage=storage, project_id=storage.project_id)

        # Unified BM25 index (single index for all types)
        self.bm25_index: BM25Index | None = None
        self._index_built = False

        self.fusion = AdaptiveFusion(base_bm25_weight=config.search.bm25_weight)
        self.mmr_reranker = MMRReranker(lambda_param=config.search.mmr_lambda)

        # File diversity filter (Phase 1: Quality optimization)
        diversity_config = DiversityConfig(
            max_chunks_per_file=config.search.max_chunks_per_file,
            preserve_top_n=config.search.diversity_preserve_top_n,
        )
        self.diversity_filter = FileDiversityFilter(diversity_config)

        # Graph expansion
        self.graph_expander = GraphExpander(storage=storage, config=config)

        logger.info(
            "Initialized SearchRetriever with unified BM25 index "
            f"(translation={'enabled' if translation_provider else 'disabled'}, "
            f"graph_expansion={'enabled' if config.search.enable_graph_expansion else 'disabled'})"
        )

    def _ensure_index(self) -> None:
        """Ensure BM25 index is built."""
        if self._index_built:
            return

        try:
            cached_index = self.index_store.load()
            if cached_index:
                self.bm25_index = cached_index
                self._index_built = True
                return

            # Build fresh index
            logger.info(f"Building unified BM25 index (project_id={self.storage.project_id})...")

            # Initialize index
            self.bm25_index = BM25Index()

            # Build code index
            code_objects = self.storage.get_all_code_objects()
            logger.info(
                f"Fetched {len(code_objects)} code objects from storage "
                f"(project_id={self.storage.project_id})"
            )

            # Defensive check: warn on empty corpus
            if not code_objects:
                logger.warning(
                    f"No code objects found in storage (project_id={self.storage.project_id}). "
                    "BM25 index will be empty. Verify project_id matches indexed data."
                )

            code_docs = []
            for obj in code_objects:
                code_docs.append(
                    {
                        "id": obj.deterministic_id,
                        "name": obj.name,
                        "qualified_name": self._build_qualified_name(obj, obj.ast_metadata),
                        "signature": obj.signature or "",
                        "docstring": obj.docstring or "",
                        "parent_context": self._build_parent_context(obj.ast_metadata),
                        "content": obj.content,
                        "file_path": obj.relative_path,
                    }
                )

            self.bm25_index.add_documents(code_docs, doc_type="code")

            # Build document index
            doc_nodes = self.storage.get_all_documents(limit=10000)
            logger.info(
                f"Fetched {len(doc_nodes)} documents from storage "
                f"(project_id={self.storage.project_id})"
            )

            doc_docs = []
            for node in doc_nodes:
                lang = "en"
                if self.language_detector:
                    lang = self.language_detector.detect(node.content)

                title = node.title or ""
                content = node.content

                if lang != "en" and self.translation_provider:
                    try:
                        if title:
                            title = self.translation_provider.translate_text(title, lang, "en")
                        content = self.translation_provider.translate_text(content, lang, "en")
                    except Exception as e:
                        logger.warning(
                            f"Translation failed for {node.deterministic_id}: {e}, using original"
                        )

                doc_docs.append(
                    {
                        "id": node.deterministic_id,
                        "title": title,
                        "headers": self._extract_headers(content),
                        "content": content,
                        "file_path": node.file_path,
                    }
                )

            self.bm25_index.add_documents(doc_docs, doc_type="document")

            self._index_built = True

            logger.info(f"BM25 index built: {self.bm25_index.get_stats()}")

            self.index_store.save(self.bm25_index)

        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            raise SearchError(f"Index building failed: {e}") from e

    def _build_qualified_name(self, obj: Any, metadata: dict[str, Any]) -> str:
        """Build qualified name from object and AST metadata.

        Examples:
        - Python: module.ClassName.method_name
        - Kotlin: com.example.UserService.authenticate
        - Java: com.example.service.UserService.authenticate

        Args:
            obj: Code object
            metadata: AST metadata

        Returns:
            Qualified name string
        """
        parts = []

        if metadata is None:
            metadata = {}

        # Add package/module if available
        if "package" in metadata:
            parts.append(metadata["package"])
        elif "module" in metadata:
            parts.append(metadata["module"])

        # Add parent class if available
        if "parent_class" in metadata:
            parts.append(metadata["parent_class"])

        # Add object name
        name = obj.name if hasattr(obj, "name") else ""
        if name:
            parts.append(name)

        return ".".join(parts) if parts else name

    def _build_parent_context(self, metadata: dict[str, Any]) -> str:
        """Build parent context string for boosting.

        Args:
            metadata: AST metadata

        Returns:
            Parent context string
        """
        if metadata is None:
            return ""

        context_parts = []

        if "parent_class" in metadata:
            context_parts.append(f"In class {metadata['parent_class']}")

        if "module" in metadata:
            context_parts.append(f"of module {metadata['module']}")

        if "package" in metadata:
            context_parts.append(f"in package {metadata['package']}")

        return " ".join(context_parts)

    def _extract_headers(self, content: str) -> str:
        """Extract markdown headers (H2, H3) from content.

        Args:
            content: Document content

        Returns:
            String of extracted headers
        """
        if not content:
            return ""

        headers = []
        for line in content.split("\n"):
            line = line.strip()
            # Match ## Header or ### Header (but not ####)
            if line.startswith("##") and not line.startswith("####"):
                header_text = line.lstrip("#").strip()
                if header_text:
                    headers.append(header_text)

        return " ".join(headers)

    def search(self, query: SearchQuery) -> list[SearchResult]:
        """Hybrid BM25 + Vector search.

        Pipeline:
        1. Translate if non-English
        2. Expand query terms
        3. BM25 search (keyword matching)
        4. Vector search (semantic similarity)
        5. Fuse with config weights
        6. Graph expansion
        7. MMR reranking
        8. Diversity filtering

        Args:
            query: Search query

        Returns:
            Ranked search results
        """
        try:
            self._ensure_index()

            query_text = query.query_text
            if self.translation_provider and self.language_detector:
                lang = self.language_detector.detect(query_text)
                if lang != "en":
                    query_text = self.translation_provider.translate_text(
                        query_text, source_lang=lang, target_lang="en"
                    )
                    logger.info(f"Translated: '{query.query_text}' → '{query_text}'")

            expanded_queries = self.query_expander.expand(query_text)

            bm25_limit = query.limit * self.config.search.bm25_retrieval_multiplier
            bm25_results = self.bm25_index.search_multi(
                queries=expanded_queries,
                limit=bm25_limit,
                filter_type="all",
            )

            vector_results = self._vector_search(query, filter_type=None)

            fused = self._adaptive_fusion(bm25_results, vector_results, bm25_boost=None)

            expanded = self.graph_expander.expand_results(fused, top_k=5)

            mmr_results = self._apply_mmr(expanded, query)

            self.diversity_filter.apply_inplace(mmr_results)

            return mmr_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise SearchError(f"Search failed: {e}") from e

    def _vector_search(
        self, query: SearchQuery, filter_type: str | None = None
    ) -> list[tuple[str, float, dict]]:
        """Perform vector similarity search.

        Args:
            query: Search query
            filter_type: Optional filter ("code", "document", or None for all)

        Returns:
            List of (id, score, metadata) tuples
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_provider.embed_text(query.query_text)

            # Phase 1: Use configurable multiplier instead of hardcoded *2
            vector_limit = query.limit * self.config.search.vector_retrieval_multiplier

            # Search both code and documents
            code_results = self.storage.search_code_objects(
                query_embedding=query_embedding,
                limit=vector_limit,
            )
            doc_results = self.storage.search_documents(
                query_embedding=query_embedding,
                limit=vector_limit,
            )

            # Combine and sort by score, preserving metadata
            combined_results = []

            # Convert code results (format: list[dict] with 'id', 'score', and 'metadata')
            for result in code_results:
                result_id = result.get("id") or result.get("deterministic_id")
                score = result.get("score", 0.0)
                metadata = result.get("metadata", {})
                if result_id:
                    combined_results.append((result_id, score, metadata))

            # Convert document results
            for result in doc_results:
                result_id = result.get("id") or result.get("deterministic_id")
                score = result.get("score", 0.0)
                metadata = result.get("metadata", {})
                if result_id:
                    combined_results.append((result_id, score, metadata))

            # Sort by score (descending)
            combined_results.sort(key=lambda x: x[1], reverse=True)

            # Filter by type if requested
            if filter_type:
                filtered_results = []
                for result_id, score, metadata in combined_results[: query.limit * 3]:
                    doc_type = metadata.get("object_type", metadata.get("node_type", ""))
                    if (
                        (filter_type == "code" and doc_type != "document")
                        or (filter_type == "document" and doc_type == "document")
                        or (filter_type == "all")
                    ):
                        filtered_results.append((result_id, score, metadata))
                return filtered_results[: query.limit * 3]

            return combined_results[: query.limit * 3]

        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []

    def _adaptive_fusion(
        self,
        bm25_results: list[tuple[str, float]],
        vector_results: list[tuple[str, float, dict]],
        bm25_boost: float | None = None,
    ) -> list[SearchResult]:
        """Fuse BM25 and vector results with optional BM25 boosting.

        Args:
            bm25_results: BM25 (id, score) tuples
            vector_results: Vector (id, score, metadata) tuples
            bm25_boost: Optional BM25 weight override (e.g., 0.75 for CODE_NAVIGATION)

        Returns:
            Fused and enriched search results
        """
        # Build metadata map from vector results
        metadata_map = {result[0]: result[2] for result in vector_results}

        # For BM25 results without metadata, fetch from storage
        # Use set to avoid duplicates (ChromaDB doesn't allow duplicate IDs in batch get)
        bm25_doc_ids = list(set(doc_id for doc_id, _ in bm25_results if doc_id not in metadata_map))
        if bm25_doc_ids:
            # Fetch all items from content collection (includes both code and documents)
            collection = self.storage.collections["content"]
            result = collection.get(
                ids=bm25_doc_ids,
                include=["metadatas", "documents"],
            )

            # Process each item based on object_type
            for i, doc_id in enumerate(result["ids"]):
                if i < len(result["metadatas"]) and i < len(result["documents"]):
                    metadata = result["metadatas"][i]
                    content = result["documents"][i]
                    obj_type = metadata.get("object_type", "")

                    if obj_type == "document":
                        # Document node
                        metadata_map[doc_id] = {
                            "file_path": metadata.get("file_path", ""),
                            "content": content,
                            "node_type": "document",
                            "start_line": 0,
                            "end_line": 0,
                            "title": metadata.get("title", ""),
                        }
                    else:
                        # Code object
                        metadata_map[doc_id] = {
                            "relative_path": metadata.get("relative_path", ""),
                            "file_path": metadata.get("file_path", ""),
                            "content": content,
                            "language": metadata.get("language", ""),
                            "object_type": obj_type,
                            "start_line": int(metadata.get("start_line", 0)),
                            "end_line": int(metadata.get("end_line", 0)),
                            "nl_description": metadata.get("nl_description", ""),
                            "name": metadata.get("name", ""),
                        }

        all_results = {}

        for doc_id, score in bm25_results:
            metadata = metadata_map.get(doc_id, {})
            all_results[doc_id] = self._create_search_result(doc_id, metadata, bm25_score=score)

        for doc_id, score, metadata in vector_results:
            if doc_id in all_results:
                all_results[doc_id].scoring.vector_code_score = score
            else:
                all_results[doc_id] = self._create_search_result(
                    doc_id, metadata, vector_score=score
                )

        # Prepare scores for fusion
        bm25_doc_scores = [
            (doc_id, r.scoring.bm25_score or 0.0) for doc_id, r in all_results.items()
        ]
        vector_doc_scores = [
            (doc_id, r.scoring.vector_code_score or 0.0) for doc_id, r in all_results.items()
        ]

        fused_scores = self.fusion.fuse(bm25_doc_scores, vector_doc_scores, bm25_boost=bm25_boost)

        for doc_id, score in fused_scores.items():
            if doc_id in all_results:
                all_results[doc_id].scoring.final_score = score

        results = sorted(all_results.values(), key=lambda x: x.scoring.final_score, reverse=True)
        return results

    def _apply_mmr(self, results: list[SearchResult], query: SearchQuery) -> list[SearchResult]:
        """Apply MMR re-ranking for diversity.

        Args:
            results: Search results to re-rank
            query: Original query

        Returns:
            Re-ranked results
        """
        if len(results) <= 1:
            return results[: query.limit]

        try:
            # Generate query embedding
            query_embedding = self.embedding_provider.embed_text(query.query_text)

            # Get embeddings for MMR
            result_ids = [r.chunk_id for r in results]
            embeddings_dict = self._get_embeddings_for_results(result_ids)

            if not embeddings_dict:
                return results[: query.limit]

            # Apply MMR with actual embeddings
            reranked = self.mmr_reranker.rerank(
                query_embedding=query_embedding,
                results=results,
                embeddings_dict=embeddings_dict,
                top_k=query.limit,
            )

            reranked = self._apply_first_chunk_boost(reranked)

            return reranked

        except Exception as e:
            logger.warning(f"MMR reranking failed: {e}")
            return results[: query.limit]

    def _create_search_result(
        self,
        doc_id: str,
        metadata: dict,
        bm25_score: float = 0.0,
        vector_score: float = 0.0,
    ) -> SearchResult:
        # CodeObject uses 'relative_path', DocumentNode uses 'file_path'
        file_path = metadata.get("relative_path") or metadata.get("file_path", "")
        content = metadata.get("content", "")
        language = metadata.get("language", "")
        node_type = metadata.get("object_type") or metadata.get("node_type", "")
        start_line = metadata.get("start_line", 0)
        end_line = metadata.get("end_line", 0)
        nl_description = metadata.get("nl_description") or metadata.get("title", "")

        if not file_path:
            logger.warning(f"Missing file_path for {doc_id}")

        scoring = SearchScoring(
            bm25_score=bm25_score if bm25_score > 0 else None,
            vector_code_score=vector_score if vector_score > 0 else None,
            final_score=0.0,  # Will be set by fusion
        )

        return SearchResult(
            chunk_id=doc_id,
            file_path=Path(file_path) if file_path else Path(),
            content=content,
            nl_description=nl_description,
            scoring=scoring,
            language=language,
            node_type=node_type,
            start_line=start_line,
            end_line=end_line,
            metadata=metadata,
        )

    def _apply_first_chunk_boost(self, results: list[SearchResult]) -> list[SearchResult]:
        """Apply 1.15x boost to first chunks."""
        for result in results:
            chunk_index = result.metadata.get("chunk_index")
            if chunk_index == 0:
                result.score *= 1.15

        results.sort(key=lambda r: r.score, reverse=True)
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _get_embeddings_for_results(self, result_ids: list[str]) -> dict[str, np.ndarray] | None:
        """Get embeddings for search results using batch queries.

        Uses 2 batch queries instead of N*2 individual queries (~100x faster).
        """
        try:
            embeddings_dict = {}

            code_objects = self.storage.get_code_objects_batch(result_ids)
            for obj in code_objects:
                if hasattr(obj, "embedding") and obj.embedding is not None:
                    embeddings_dict[obj.deterministic_id] = np.array(obj.embedding)

            missing_ids = [rid for rid in result_ids if rid not in embeddings_dict]
            if missing_ids:
                documents = self.storage.get_documents_batch(missing_ids)
                for doc in documents:
                    if hasattr(doc, "embedding") and doc.embedding is not None:
                        embeddings_dict[doc.deterministic_id] = np.array(doc.embedding)

            return embeddings_dict if embeddings_dict else None

        except Exception as e:
            logger.warning(f"Failed to get embeddings: {e}")
            return None
