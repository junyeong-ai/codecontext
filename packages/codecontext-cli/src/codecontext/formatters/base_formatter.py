from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from codecontext_core.models import RelationType, SearchResult

if TYPE_CHECKING:
    from codecontext_core import VectorStore


def _normalize_id(id_str: str) -> str:
    return id_str.replace("-", "")


def _add_rel(
    output: dict[str, dict[str, Any]], key: str, name: str, obj_type: str, file: str, line: int
) -> None:
    if key not in output:
        output[key] = {"items": [], "total_count": 0}
    output[key]["items"].append({"name": name, "type": obj_type, "file": file, "line": line})
    output[key]["total_count"] += 1


class BaseFormatter(ABC):
    @abstractmethod
    def format(
        self,
        results: list[SearchResult],
        query: str = "",
        storage: "VectorStore | None" = None,
        include_scoring: bool = False,
        expand_fields: set[str] | None = None,
    ) -> str:
        pass


def extract_relationships(result: SearchResult, storage: "VectorStore | None") -> dict[str, Any]:
    if storage is None:
        return {}

    result_id = _normalize_id(result.chunk_id)
    rels = storage.get_relationships(result.chunk_id)
    if not rels:
        return {}

    output: dict[str, dict[str, Any]] = {}

    for rel in rels:
        rel_type = rel.relation_type
        is_source = _normalize_id(rel.source_id) == result_id
        is_target = _normalize_id(rel.target_id) == result_id

        if rel_type == RelationType.CALLS:
            if is_target:
                _add_rel(
                    output,
                    "callers",
                    rel.source_name,
                    rel.source_type,
                    rel.source_file,
                    rel.source_line,
                )
            elif is_source:
                _add_rel(
                    output,
                    "callees",
                    rel.target_name,
                    rel.target_type,
                    rel.target_file,
                    rel.target_line,
                )

        elif rel_type == RelationType.CONTAINS:
            if is_source:
                _add_rel(
                    output,
                    "contains",
                    rel.target_name,
                    rel.target_type,
                    rel.target_file,
                    rel.target_line,
                )
            elif is_target:
                _add_rel(
                    output,
                    "contained_by",
                    rel.source_name,
                    rel.source_type,
                    rel.source_file,
                    rel.source_line,
                )

        elif rel_type == RelationType.EXTENDS:
            if is_source:
                _add_rel(
                    output,
                    "extends",
                    rel.target_name,
                    rel.target_type,
                    rel.target_file,
                    rel.target_line,
                )
            elif is_target:
                _add_rel(
                    output,
                    "extended_by",
                    rel.source_name,
                    rel.source_type,
                    rel.source_file,
                    rel.source_line,
                )

        elif rel_type == RelationType.IMPLEMENTS:
            if is_source:
                _add_rel(
                    output,
                    "implements",
                    rel.target_name,
                    rel.target_type,
                    rel.target_file,
                    rel.target_line,
                )
            elif is_target:
                _add_rel(
                    output,
                    "implemented_by",
                    rel.source_name,
                    rel.source_type,
                    rel.source_file,
                    rel.source_line,
                )

        elif rel_type == RelationType.REFERENCES:
            if is_source:
                _add_rel(
                    output,
                    "references",
                    rel.target_name,
                    rel.target_type,
                    rel.target_file,
                    rel.target_line,
                )
            elif is_target:
                _add_rel(
                    output,
                    "referenced_by",
                    rel.source_name,
                    rel.source_type,
                    rel.source_file,
                    rel.source_line,
                )

        elif rel_type == RelationType.IMPORTS:
            if is_source:
                _add_rel(
                    output,
                    "imports",
                    rel.target_name,
                    rel.target_type,
                    rel.target_file,
                    rel.target_line,
                )
            elif is_target:
                _add_rel(
                    output,
                    "imported_by",
                    rel.source_name,
                    rel.source_type,
                    rel.source_file,
                    rel.source_line,
                )

    return output


def calculate_direct_callers(result: SearchResult, storage: "VectorStore | None") -> dict[str, Any]:
    if storage is None:
        return {"direct_callers": 0}

    result_id = _normalize_id(result.chunk_id)
    rels = storage.get_relationships(result.chunk_id)

    caller_count = sum(
        1
        for r in rels
        if r.relation_type == RelationType.CALLS and _normalize_id(r.target_id) == result_id
    )

    return {"direct_callers": caller_count}


def extract_essential_snippet(content: str) -> list[str]:
    if not content:
        return []

    lines = content.split("\n")
    essential = [lines[0]] if lines else []

    key_lines = []
    for line in lines[1:]:
        stripped = line.strip()
        if any(keyword in stripped for keyword in ["return", "=", "await", "raise", "yield"]):
            key_lines.append(line)
            if len(key_lines) >= 2:
                break

    essential.extend(key_lines[:2])
    return essential[:5]


def find_related_sections(
    result: SearchResult,
    storage: "VectorStore | None",
    limit: int = 3,
) -> list[dict[str, Any]]:
    if storage is None:
        return []

    code_object = storage.get_code_object(result.chunk_id)
    if code_object is None or code_object.embedding is None:
        return []

    similar_docs = storage.search_documents(
        query_embedding=code_object.embedding,
        limit=limit,
    )

    related_sections = []
    for doc_result in similar_docs:
        metadata = doc_result.get("metadata", {})
        content = doc_result.get("content", "")
        snippet = content[:200] + "..." if len(content) > 200 else content

        related_sections.append(
            {
                "title": metadata.get("title", "Untitled"),
                "file": metadata.get("file_path", ""),
                "score": round(doc_result.get("score", 0.0), 3),
                "snippet": snippet,
            }
        )

    return related_sections
