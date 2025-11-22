"""JSON output formatter for search results."""

import json
from typing import TYPE_CHECKING, Any

from codecontext_core.models import SearchResult

from codecontext.formatters.base_formatter import (
    BaseFormatter,
    calculate_transitive_impact,
    extract_essential_snippet,
    extract_relationships,
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
        expand_fields: set[str] | None = None,
    ) -> str:
        """Format results as JSON.

        Args:
            results: Search results to format
            query: Original search query
            storage: Storage provider for relationships
            include_scoring: Legacy parameter (ignored)
            expand_fields: Fields to expand (signature, content, relationships, complexity, impact, all)
        """
        formatted = []

        for result in results:
            if expand_fields:
                formatted_result = self._format_expanded(result, storage, expand_fields)
            else:
                formatted_result = self._format_minimal(result)

            formatted.append(formatted_result)

        output = {"results": formatted, "total": len(results), "query": query}
        return json.dumps(output, indent=2)

    def _format_minimal(self, result: SearchResult) -> dict[str, Any]:
        """Minimal fields: name, type, file, lines, language, score."""
        # Use relative_path if available, otherwise file_path
        file_path = result.metadata.get("relative_path") or str(result.file_path)

        # For documents, prefer node_type (markdown, config) over object_type (document)
        obj_type = result.metadata.get("node_type") or result.metadata.get("object_type", "")

        minimal = {
            "name": result.metadata.get("name", ""),
            "type": obj_type,
            "file": file_path,
        }

        if result.result_type == "code":
            minimal["lines"] = f"{result.start_line}-{result.end_line}"
        elif result.result_type == "document":
            start_line = result.metadata.get("start_line")
            end_line = result.metadata.get("end_line")
            if start_line and end_line and start_line != 0 and end_line != 0:
                minimal["lines"] = f"{start_line}-{end_line}"

        # Add language if available
        language = result.metadata.get("language", "")
        if language:
            minimal["language"] = language

        # Add score (rounded)
        if result.score:
            minimal["score"] = round(result.score, 2)

        return minimal

    def _format_expanded(
        self,
        result: SearchResult,
        storage: "VectorStore | None",
        expand_fields: set[str],
    ) -> dict[str, Any]:
        """Add fields: signature, snippet, content, relationships, complexity, impact, all."""
        # Start with minimal fields
        expanded = self._format_minimal(result)

        # Expand all fields if 'all' is specified
        expand_all = "all" in expand_fields

        # Add signature
        if expand_all or "signature" in expand_fields:
            signature = result.metadata.get("signature", "")
            if signature and signature != expanded["name"]:
                expanded["signature"] = signature

        # Add snippet
        if expand_all or "snippet" in expand_fields:
            snippet = extract_essential_snippet(result.content or "")
            if snippet:
                expanded["snippet"] = snippet[0] if len(snippet) == 1 else snippet

        # Add content
        if expand_all or "content" in expand_fields:
            if result.content:
                expanded["content"] = result.content

        # Add parent if exists
        parent = result.metadata.get("parent_id")
        if parent:
            expanded["parent"] = parent

        # Add complexity
        if expand_all or "complexity" in expand_fields:
            ast_metadata = result.metadata.get("ast_metadata", {})
            complexity = ast_metadata.get("complexity", {})
            cyclomatic = complexity.get("cyclomatic", 1)
            lines = complexity.get("lines", 0)

            if cyclomatic > 1 or lines > 0:
                expanded["complexity"] = {
                    "cyclomatic": cyclomatic,
                    "lines": lines,
                }

        # Add relationships
        if (expand_all or "relationships" in expand_fields) and storage:
            relationships = extract_relationships(result, storage)

            # Filter out empty relationships
            filtered_rels = {}
            for key in ["callers", "callees", "contains"]:
                if relationships.get(key, {}).get("items"):
                    filtered_rels[key] = relationships[key]

            if filtered_rels:
                expanded["relationships"] = filtered_rels

        # Add impact
        if (expand_all or "impact" in expand_fields) and storage:
            impact = calculate_transitive_impact(result, storage)
            if impact.get("recursive_callers", 0) > 0:
                expanded["impact"] = impact

        return expanded
