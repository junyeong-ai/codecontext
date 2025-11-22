"""Text output formatter for search results."""

from typing import TYPE_CHECKING

from codecontext_core.models import SearchResult

from codecontext.formatters.base_formatter import (
    BaseFormatter,
    calculate_transitive_impact,
    extract_essential_snippet,
    extract_relationships,
)

if TYPE_CHECKING:
    from codecontext_core import VectorStore


class TextFormatter(BaseFormatter):
    """Format search results as human-readable text."""

    def format(
        self,
        results: list[SearchResult],
        _query: str = "",
        storage: "VectorStore | None" = None,
        include_scoring: bool = False,
        expand_fields: set[str] | None = None,
    ) -> str:
        """Format results as plain text."""
        if not results:
            return "No results found."

        lines = [f"Search Results ({len(results)} found)\n"]

        for i, result in enumerate(results, 1):
            if expand_fields:
                result_lines = self._format_expanded(
                    result, storage, expand_fields, include_scoring
                )
            else:
                result_lines = self._format_minimal(result, include_scoring)

            lines.append(f"{i}. {result_lines}")

            if i < len(results):
                lines.append("")

        return "\n".join(lines)

    def _format_minimal(self, result: SearchResult, include_scoring: bool = False) -> str:
        """Format minimal result information."""
        metadata = result.metadata
        name = metadata.get("name", "")
        obj_type = metadata.get("node_type") or metadata.get("object_type", "")
        language = metadata.get("language", "")

        context = ""
        if result.result_type == "document":
            title = metadata.get("title")
            if title and title != name:
                context = f" > {title}"

        file_path = metadata.get("relative_path") or str(result.file_path)

        if result.result_type == "document":
            start_line = metadata.get("start_line")
            end_line = metadata.get("end_line")

            if start_line and end_line and start_line != 0 and end_line != 0:
                location = f"{file_path}:{start_line}-{end_line}"
            else:
                chunk_info = ""
                chunk_idx = metadata.get("chunk_index")
                total_chunks = metadata.get("total_chunks")
                if chunk_idx is not None and total_chunks and total_chunks > 1:
                    chunk_info = f" (chunk {chunk_idx + 1}/{total_chunks})"
                location = f"{file_path}{chunk_info}"
        else:
            location = f"{file_path}:{result.start_line}-{result.end_line}"

        score = result.score

        lines = []
        lines.append(f"{name}{context} (score: {score:.2f})")
        lines.append(f"   Type: {obj_type}")
        if language:
            lines.append(f"   Language: {language}")
        lines.append(f"   File: {location}")

        if include_scoring:
            bm25 = result.scoring.bm25_score or 0.0
            vector = result.scoring.vector_code_score or 0.0
            lines.append(f"   Scoring: BM25={bm25:.3f}, Vector={vector:.3f}")

        return "\n".join(lines)

    def _format_expanded(
        self,
        result: SearchResult,
        storage: "VectorStore | None",
        expand_fields: set[str],
        include_scoring: bool = False,
    ) -> str:
        """Format expanded result with additional fields."""
        lines = [self._format_minimal(result, include_scoring)]

        expand_all = "all" in expand_fields
        metadata = result.metadata

        # Signature
        if expand_all or "signature" in expand_fields:
            signature = metadata.get("signature", "")
            if signature and signature != metadata.get("name", ""):
                lines.append(f"   Signature: {signature}")

        # Complexity
        if expand_all or "complexity" in expand_fields:
            ast_metadata = metadata.get("ast_metadata")
            if ast_metadata:
                complexity = ast_metadata.get("complexity", {})
                cyclomatic = complexity.get("cyclomatic", 1)
                code_lines = complexity.get("lines", 0)

                if cyclomatic > 1 or code_lines > 0:
                    lines.append(f"   Complexity: cyclomatic={cyclomatic}, lines={code_lines}")

        # Snippet
        if expand_all or "snippet" in expand_fields:
            if result.content:
                snippet = extract_essential_snippet(result.content)
                if snippet:
                    lines.append("")
                    lines.append("   Snippet:")
                    for line in snippet:
                        lines.append(f"   │ {line}")

        # Relationships
        if (expand_all or "relationships" in expand_fields) and storage:
            relationships = extract_relationships(result, storage)

            rel_lines = []
            for rel_type, rel_data in [
                ("Callers", relationships.get("callers", {})),
                ("Callees", relationships.get("callees", {})),
                ("Contains", relationships.get("contains", {})),
            ]:
                items = rel_data.get("items", [])
                total = rel_data.get("total_count", 0)

                if items:
                    names = [item.get("name", "") for item in items[:3]]
                    if total > 3:
                        rel_lines.append(f"   • {rel_type} ({total}): {', '.join(names)}, ...")
                    else:
                        rel_lines.append(f"   • {rel_type} ({total}): {', '.join(names)}")

            if rel_lines:
                lines.append("")
                lines.append("   Relationships:")
                lines.extend(rel_lines)

        # Impact
        if (expand_all or "impact" in expand_fields) and storage:
            impact = calculate_transitive_impact(result, storage)
            recursive_callers = impact.get("recursive_callers", 0)
            if recursive_callers > 0:
                lines.append("")
                lines.append(f"   Impact: {recursive_callers} recursive callers")

        # Content
        if expand_all or "content" in expand_fields:
            if result.content:
                lines.append("")
                lines.append("   Content:")
                for line in result.content.split("\n"):
                    lines.append(f"   │ {line}")

        return "\n".join(lines)
