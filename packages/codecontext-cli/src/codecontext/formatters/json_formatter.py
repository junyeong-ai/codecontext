"""JSON output formatter for search results."""

import json
from typing import TYPE_CHECKING, Any

from codecontext_core.models import SearchResult
from codecontext.formatters.base_formatter import (
    BaseFormatter,
    calculate_transitive_impact,
    extract_essential_snippet,
    extract_relationships,
    find_similar_objects,
)

if TYPE_CHECKING:
    from codecontext_core import VectorStore


class JSONFormatter(BaseFormatter):
    """Format search results as JSON."""

    def format(
        self,
        results: list[SearchResult],
        query: str = "",
        storage: "VectorStore | None" = None,
        include_scoring: bool = False,
    ) -> str:
        """Format results as JSON."""
        formatted = []

        for result in results:
            ast_metadata = result.metadata.get("ast_metadata")
            structure = (
                ast_metadata
                if ast_metadata
                else {
                    "calls": [],
                    "references": [],
                    "complexity": {"cyclomatic": 1, "lines": 0, "nesting_depth": 0},
                }
            )

            file_path_str = str(result.file_path) if result.file_path else ""

            formatted_result: dict[str, Any] = {
                "id": str(result.result_id),
                "score": result.score,
                "rank": result.rank,
                "path": file_path_str,
                "location": {
                    "file": file_path_str,
                    "start_line": result.start_line,
                    "end_line": result.end_line,
                    "url": f"{file_path_str}:{result.start_line}-{result.end_line}",
                },
                "metadata": {
                    "name": result.metadata.get("name", ""),
                    "type": result.metadata.get("object_type", ""),
                    "signature": result.metadata.get("signature", ""),
                    "language": result.metadata.get("language", ""),
                    "parent": result.metadata.get("parent_id") or None,
                },
                "structure": structure,
                "snippet": {
                    "essential": extract_essential_snippet(result.content or ""),
                    "full": None,
                },
            }

            if include_scoring:
                formatted_result["scoring"] = {
                    "bm25_score": result.scoring.bm25_score,
                    "vector_code_score": result.scoring.vector_code_score,
                    "vector_desc_score": result.scoring.vector_desc_score,
                    "graph_score": result.scoring.graph_score,
                    "final_score": result.scoring.final_score,
                }

            if storage:
                relationships = extract_relationships(result, storage)
                formatted_result["relationships"] = relationships
                formatted_result["impact"] = calculate_transitive_impact(result, storage)
                # Update similar items (already initialized in extract_relationships)
                similar_items = find_similar_objects(result, storage)
                relationships["similar"]["items"] = similar_items

            formatted.append(formatted_result)

        output = {"results": formatted, "total": len(results), "query": query}

        return json.dumps(output, indent=2)
