"""Document results formatter."""

import json
from typing import TYPE_CHECKING

from codecontext_core.models import SearchResult

from codecontext.formatters.base_formatter import BaseFormatter

if TYPE_CHECKING:
    from codecontext_core import VectorStore


class DocumentFormatter(BaseFormatter):
    """Format markdown section search results."""

    def format(
        self,
        results: list[SearchResult],
        query: str = "",
        storage: "VectorStore | None" = None,
        include_scoring: bool = False,
        expand_fields: set[str] | None = None,
    ) -> str:
        """Format document results as JSON."""
        formatted = []
        for result in results:
            related_code_refs = result.metadata.get("related_code", [])
            related_code = [
                {
                    "name": ref.get("name", ""),
                    "location": ref.get("location", ""),
                    "match_reason": ref.get("match_reason", "mentioned"),
                }
                for ref in related_code_refs
            ]

            formatted_result = {
                "id": str(result.result_id),
                "score": result.score,
                "rank": result.rank,
                "path": str(result.file_path),  # Use direct field
                "location": {
                    "file": str(result.file_path),  # Use direct field
                    "section": result.metadata.get("section_title", ""),
                    "start_line": result.start_line,  # Use direct field
                    "end_line": result.end_line,  # Use direct field
                    "url": (f"{result.file_path}:{result.start_line}-{result.end_line}#section"),
                },
                "metadata": {
                    "title": result.metadata.get("section_title", ""),
                    "type": "markdown_section",
                    "language": "markdown",
                },
                "related_code": related_code,
                "snippet": {
                    "preview": (result.content or "").split("\n")[:5] if result.content else [],
                    "full": None,
                },
            }
            formatted.append(formatted_result)

        output = {"results": formatted, "total": len(results), "query": query}

        return json.dumps(output, indent=2)
