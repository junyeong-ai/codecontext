"""Output formatters for search results - Factory and routing."""

import json
from typing import Any

from codecontext_core.models import SearchResult

from codecontext.formatters.config_formatter import ConfigFormatter
from codecontext.formatters.document_formatter import DocumentFormatter
from codecontext.formatters.json_formatter import JSONFormatter
from codecontext.formatters.text_formatter import TextFormatter

# Type alias for all formatter types
Formatter = ConfigFormatter | DocumentFormatter | JSONFormatter | TextFormatter


def format_results(
    results: list[SearchResult],
    format_type: str = "text",
    query: str = "",
    storage: Any | None = None,
    include_scoring: bool = False,
    expand_fields: set[str] | None = None,
) -> str:
    """Format search results with automatic routing based on result type.

    Args:
        results: List of search results
        format_type: Output format ("text" or "json")
        query: Original search query
        storage: Optional storage provider for relationship queries
        include_scoring: Include detailed scoring breakdown (legacy)
        expand_fields: Fields to expand (content, relationships, complexity, impact, all)

    Returns:
        Formatted output string
    """
    if not results:
        if format_type == "json":
            return json.dumps({"results": [], "total": 0, "query": query})
        return "No results found."

    # Text format always uses TextFormatter
    if format_type == "text":
        formatter: Formatter = TextFormatter()
        return formatter.format(results, query, storage, include_scoring, expand_fields)

    # JSON format: Route based on result types
    result_types = {r.result_type for r in results}

    # Pure document results - check node_type to pick specialized formatter
    if result_types == {"document"}:
        node_types = {r.metadata.get("node_type") for r in results if r.metadata.get("node_type")}

        if node_types == {"config"}:
            formatter = ConfigFormatter()
            return formatter.format(results, query, storage, include_scoring)
        elif node_types == {"markdown"}:
            formatter = DocumentFormatter()
            return formatter.format(results, query, storage, include_scoring)

    # All other cases: pure code, mixed types, or ambiguous documents
    formatter = JSONFormatter()
    return formatter.format(results, query, storage, include_scoring, expand_fields)
