import json
from typing import TYPE_CHECKING, Any

from codecontext_core.models import SearchResult

from codecontext.formatters.base_formatter import (
    BaseFormatter,
    calculate_direct_callers,
    extract_essential_snippet,
    extract_relationships,
)

if TYPE_CHECKING:
    from codecontext_core import VectorStore


class JSONFormatter(BaseFormatter):
    def format(
        self,
        results: list[SearchResult],
        query: str = "",
        storage: "VectorStore | None" = None,
        include_scoring: bool = False,
        expand_fields: set[str] | None = None,
    ) -> str:
        formatted = [
            self._format_expanded(result, storage, expand_fields)
            if expand_fields
            else self._format_minimal(result)
            for result in results
        ]

        return json.dumps({"results": formatted, "total": len(results), "query": query}, indent=2)

    def _format_minimal(self, result: SearchResult) -> dict[str, Any]:
        file_path = result.metadata.get("relative_path") or str(result.file_path)
        obj_type = result.metadata.get("node_type") or result.metadata.get("object_type", "")

        minimal: dict[str, Any] = {
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

        language = result.metadata.get("language", "")
        if language:
            minimal["language"] = language

        if result.score:
            minimal["score"] = round(result.score, 2)

        return minimal

    def _format_expanded(
        self,
        result: SearchResult,
        storage: "VectorStore | None",
        expand_fields: set[str],
    ) -> dict[str, Any]:
        expanded = self._format_minimal(result)
        expand_all = "all" in expand_fields

        if expand_all or "signature" in expand_fields:
            signature = result.metadata.get("signature", "")
            if signature and signature != expanded["name"]:
                expanded["signature"] = signature

        if expand_all or "snippet" in expand_fields:
            snippet = extract_essential_snippet(result.content or "")
            if snippet:
                expanded["snippet"] = snippet[0] if len(snippet) == 1 else snippet

        if expand_all or "content" in expand_fields:
            if result.content:
                expanded["content"] = result.content

        parent = result.metadata.get("parent_id")
        if parent:
            expanded["parent"] = parent

        if expand_all or "complexity" in expand_fields:
            ast_metadata = result.metadata.get("ast_metadata", {})
            complexity = ast_metadata.get("complexity", {})
            cyclomatic = complexity.get("cyclomatic", 1)
            lines = complexity.get("lines", 0)

            if cyclomatic > 1 or lines > 0:
                expanded["complexity"] = {"cyclomatic": cyclomatic, "lines": lines}

        if (expand_all or "relationships" in expand_fields) and storage:
            relationships = extract_relationships(result, storage)
            if relationships:
                expanded["relationships"] = relationships

        if (expand_all or "impact" in expand_fields) and storage:
            impact = calculate_direct_callers(result, storage)
            if impact.get("direct_callers", 0) > 0:
                expanded["impact"] = impact

        return expanded
