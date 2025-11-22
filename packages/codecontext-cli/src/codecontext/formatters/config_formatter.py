"""Configuration file results formatter."""

import json
from typing import TYPE_CHECKING

from codecontext_core.models import SearchResult

from codecontext.formatters.base_formatter import BaseFormatter

if TYPE_CHECKING:
    from codecontext_core import VectorStore


class ConfigFormatter(BaseFormatter):
    """Format configuration file search results."""

    def format(
        self,
        results: list[SearchResult],
        query: str = "",
        _storage: "VectorStore | None" = None,
        include_scoring: bool = False,
        expand_fields: set[str] | None = None,
    ) -> str:
        """Format config results as JSON."""
        formatted = []
        for result in results:
            # Metadata is already parsed by retriever
            config_keys = result.metadata.get("config_keys", [])
            env_refs = result.metadata.get("env_references", [])
            section_depth = result.metadata.get("section_depth", 1)

            formatted_result = {
                "id": str(result.result_id),
                "score": result.score,
                "rank": result.rank,
                "path": result.metadata.get("file_path", ""),  # Shorthand for convenience
                "location": {
                    "file": result.metadata.get("file_path", ""),
                    "section": result.metadata.get("title", ""),
                    "url": f"{result.metadata.get('file_path', '')}#config",
                },
                "metadata": {
                    "title": result.metadata.get("title", ""),
                    "config_format": result.metadata.get("config_format", ""),
                    "section_depth": section_depth,
                    "type": "config",
                },
                "config_keys": config_keys or [],
                "env_references": env_refs or [],
                "snippet": {
                    "preview": (result.content or "").split("\n")[:8] if result.content else [],
                    "full": None,
                },
            }
            formatted.append(formatted_result)

        output = {"results": formatted, "total": len(results), "query": query}

        return json.dumps(output, indent=2)
