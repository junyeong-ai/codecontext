import json
import logging
from pathlib import Path
from typing import Any

from codecontext_core import VectorStore
from codecontext_core.interfaces import EmbeddingProvider, InstructionType
from codecontext_core.models import SearchQuery, SearchResult, SearchScoring
from codecontext_core.tokenizer import CodeTokenizer

from codecontext.config.schema import SearchConfig
from codecontext.search.graph_expander import GraphExpander

logger = logging.getLogger(__name__)


class SearchRetriever:
    def __init__(
        self, storage: VectorStore, embedding_provider: EmbeddingProvider, config: SearchConfig
    ):
        self.storage = storage
        self.embedding_provider = embedding_provider
        self.config = config

        self.graph_expander = (
            GraphExpander(storage, config) if config.enable_graph_expansion else None
        )

    def search(
        self,
        query: SearchQuery,
        instruction_type: InstructionType = InstructionType.NL2CODE_QUERY,
    ) -> list[SearchResult]:
        limit = query.limit or self.config.default_limit

        # Use pre-computed embedding or generate new one
        query_embedding = query.query_embedding or self.embedding_provider.embed_text(
            query.query_text, instruction_type=instruction_type
        )

        results = self.storage._search_hybrid(  # type: ignore[attr-defined]
            query_embedding=query_embedding,
            query_text=query.query_text,
            limit=limit * 3,
            type_filter=query.type_filter,
            language_filter=query.language_filter,
            file_filter=query.file_filter,
        )

        search_results = []

        for point in results:
            payload = point.payload
            chunk_id = str(point.id)
            result_type = payload.get("type", "code")

            if result_type == "document":
                display_name = (
                    payload.get("title")
                    or payload.get("file_path", "").split("/")[-1]
                    or "Untitled"
                )

                metadata = {
                    "name": display_name,
                    "title": payload.get("title"),
                    "node_type": payload.get("node_type", "markdown"),
                    "chunk_index": payload.get("chunk_index", 0),
                    "total_chunks": payload.get("total_chunks", 1),
                    "start_line": payload.get("start_line", 0),
                    "end_line": payload.get("end_line", 0),
                    "relative_path": self._normalize_path(
                        payload.get("relative_path", payload.get("file_path", ""))
                    ),
                }

                if payload.get("node_type") == "markdown":
                    metadata["related_code"] = self._parse_json_field(
                        payload.get("related_code", ""), []
                    )
                elif payload.get("node_type") == "config":
                    metadata["config_keys"] = self._parse_json_field(
                        payload.get("config_keys", ""), []
                    )
                    metadata["env_references"] = self._parse_json_field(
                        payload.get("env_references", ""), []
                    )
                    metadata["section_depth"] = payload.get("section_depth", 1)
                    metadata["config_format"] = payload.get("config_format", "")
            else:
                display_name = payload.get("qualified_name") or payload.get("name") or "Anonymous"

                metadata = {
                    "name": display_name,
                    "qualified_name": payload.get("qualified_name"),
                    "signature": payload.get("signature"),
                    "object_type": payload.get("object_type"),
                    "language": payload.get("language", ""),
                    "parent_id": payload.get("parent_id"),
                    "ast_metadata": self._parse_json_field(payload.get("ast_metadata", ""), {}),
                    "score_weight": payload.get("score_weight", 1.0),
                    "relative_path": self._normalize_path(
                        payload.get("relative_path", payload.get("file_path", ""))
                    ),
                }

            result = SearchResult(
                chunk_id=chunk_id,
                file_path=Path(payload.get("file_path", "")),
                content=payload.get("content", ""),
                scoring=SearchScoring(final_score=point.score),
                language=payload.get("language", ""),
                node_type=payload.get("object_type", payload.get("node_type", "")),
                start_line=payload.get("start_line", 0),
                end_line=payload.get("end_line", 0),
                metadata=metadata,
                result_type=result_type,
            )
            search_results.append(result)

        if self.graph_expander:
            search_results = self.graph_expander.expand_results(search_results)

        search_results = self._apply_boosting(search_results, query.query_text)
        search_results = sorted(search_results, key=lambda r: r.score, reverse=True)
        search_results = self._apply_diversity_filter(search_results)

        # Apply min_score filter if specified
        if query.min_score > 0.0:
            search_results = [r for r in search_results if r.score >= query.min_score]

        return search_results[:limit]

    def _apply_boosting(self, results: list[SearchResult], query: str) -> list[SearchResult]:
        query_lower = query.lower().strip()
        query_tokens = set(CodeTokenizer.tokenize_text(query))
        boosting = self.config.type_boosting

        for result in results:
            base = result.scoring.final_score
            boost = 0.0

            if result.result_type == "document":
                type_val = getattr(boosting, result.node_type.lower(), 0.0)
            else:
                object_type = result.node_type.lower()
                type_val = getattr(boosting, object_type.replace("class", "class_"), 0.0)
            boost += type_val

            name = (result.metadata.get("name") or "").lower()
            qualified = (result.metadata.get("qualified_name") or "").lower()
            name_tokens = set(CodeTokenizer.tokenize_text(name))

            if query_lower == name:
                boost += 0.25
            elif query_lower in qualified:
                boost += 0.20
            elif query_tokens and name_tokens:
                if name_tokens.issubset(query_tokens):
                    boost += 0.15
                elif query_tokens.issubset(name_tokens):
                    boost += 0.12
                elif overlap := query_tokens & name_tokens:
                    ratio = len(overlap) / len(query_tokens)
                    boost += ratio * 0.05

            weight = result.metadata.get("score_weight", 1.0)
            result.scoring.final_score = base * (1.0 + boost) * weight

        return results

    def _apply_diversity_filter(self, results: list[SearchResult]) -> list[SearchResult]:
        if not results:
            return results

        preserve_n = self.config.diversity_preserve_top_n
        max_per_file = self.config.max_chunks_per_file

        preserved = results[:preserve_n]
        to_filter = results[preserve_n:]

        doc_seen: dict[str, bool] = {}
        file_counts: dict[str, int] = {}
        filtered = []

        for result in to_filter:
            if result.result_type == "document":
                parent_id = result.metadata.get("parent_doc_id", str(result.file_path))
                if parent_id not in doc_seen:
                    filtered.append(result)
                    doc_seen[parent_id] = True
            else:
                file_path = str(result.file_path)
                count = file_counts.get(file_path, 0)
                if count < max_per_file:
                    filtered.append(result)
                    file_counts[file_path] = count + 1

        return preserved + filtered

    def _normalize_path(self, path: str) -> str:
        if path.startswith("../"):
            return path[3:]
        return path

    @staticmethod
    def _parse_json_field(
        value: str, default: dict[str, Any] | list[Any]
    ) -> dict[str, Any] | list[Any]:
        """Parse JSON string from storage to structured data."""
        if not value:
            return default
        try:
            parsed: dict[str, Any] | list[Any] = json.loads(value)
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Malformed JSON in storage: {e}")
            return default
