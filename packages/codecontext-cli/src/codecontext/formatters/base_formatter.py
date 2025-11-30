"""Base formatter interface and shared utilities."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from codecontext_core.models import RelationType, SearchResult

if TYPE_CHECKING:
    from codecontext_core import VectorStore


def _normalize_id(id_str: str) -> str:
    """Normalize ID by removing dashes (UUID format to hex string)."""
    return id_str.replace("-", "")


def _add_rel(output: dict[str, dict[str, Any]], key: str, name: str, location: str) -> None:
    """Add a relationship item to the output dictionary."""
    if key not in output:
        output[key] = {"items": [], "total_count": 0}
    output[key]["items"].append({"name": name, "location": location})
    output[key]["total_count"] += 1


class BaseFormatter(ABC):
    """Abstract base class for all formatters."""

    @abstractmethod
    def format(
        self,
        results: list[SearchResult],
        query: str = "",
        storage: "VectorStore | None" = None,
        include_scoring: bool = False,
        expand_fields: set[str] | None = None,
    ) -> str:
        """Format search results.

        Args:
            results: List of search results to format
            query: Original search query
            storage: Optional storage provider for relationship queries
            include_scoring: Include detailed scoring breakdown (BM25, Vector, etc.)
            expand_fields: Fields to expand (signature, snippet, content, relationships, complexity, impact, all)

        Returns:
            Formatted output string
        """
        pass


def extract_relationships(result: SearchResult, storage: "VectorStore | None") -> dict[str, Any]:
    """Extract all relationship types from storage."""
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
                _add_rel(output, "callers", rel.source_type, rel.source_id)
            elif is_source:
                _add_rel(output, "callees", rel.target_type, rel.target_id)

        elif rel_type == RelationType.CONTAINS:
            if is_source:
                _add_rel(output, "contains", rel.target_type, rel.target_id)
            elif is_target:
                _add_rel(output, "contained_by", rel.source_type, rel.source_id)

        elif rel_type == RelationType.EXTENDS:
            if is_source:
                _add_rel(output, "extends", rel.target_type, rel.target_id)
            elif is_target:
                _add_rel(output, "extended_by", rel.source_type, rel.source_id)

        elif rel_type == RelationType.IMPLEMENTS:
            if is_source:
                _add_rel(output, "implements", rel.target_type, rel.target_id)
            elif is_target:
                _add_rel(output, "implemented_by", rel.source_type, rel.source_id)

        elif rel_type == RelationType.REFERENCES:
            if is_source:
                _add_rel(output, "references", rel.target_type, rel.target_id)
            elif is_target:
                _add_rel(output, "referenced_by", rel.source_type, rel.source_id)

        elif rel_type == RelationType.IMPORTS:
            if is_source:
                _add_rel(output, "imports", rel.target_type, rel.target_id)
            elif is_target:
                _add_rel(output, "imported_by", rel.source_type, rel.source_id)

    return output


def calculate_direct_callers(result: SearchResult, storage: "VectorStore | None") -> dict[str, Any]:
    """Count direct callers for the given result."""
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
    """Extract signature + 2-3 key lines from code content."""
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


def find_similar_objects(
    result: SearchResult,
    storage: "VectorStore | None",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find top N similar code objects using vector similarity.

    Args:
        result: Search result containing the code object
        storage: Vector storage provider for similarity search
        limit: Maximum number of similar objects to return

    Returns:
        List of similar objects with name, file, score, and location
    """
    if storage is None:
        return []

    # Get deterministic ID of current result to filter it out
    result_id = result.chunk_id

    # Get code object to access its embedding
    code_object = storage.get_code_object(result_id)
    if code_object is None or code_object.embedding is None:
        return []

    # Search for similar objects using the embedding
    similar_results = storage.search_code_objects(
        query_embedding=code_object.embedding,
        limit=limit + 1,  # Request extra to account for filtering self
    )

    # Convert to formatter-friendly format and filter out self
    similar_objects = []
    for raw_result in similar_results:
        # Skip the current object itself
        if raw_result.get("id") == result_id:
            continue

        metadata = raw_result.get("metadata", {})
        similar_objects.append(
            {
                "name": metadata.get("name", ""),
                "file": metadata.get("file_path", ""),
                "score": round(raw_result.get("score", 0.0), 3),
                "location": f"{metadata.get('start_line', 0)}-{metadata.get('end_line', 0)}",
            }
        )

        if len(similar_objects) >= limit:
            break

    return similar_objects


def find_related_sections(
    result: SearchResult,
    storage: "VectorStore | None",
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Find related document sections using vector similarity.

    Args:
        result: Search result containing the code object
        storage: Vector storage provider for similarity search
        limit: Maximum number of related sections to return

    Returns:
        List of related document sections with title, file, score, and snippet
    """
    if storage is None:
        return []

    # Get deterministic ID of current result
    result_id = result.chunk_id

    # Get code object to access its embedding
    code_object = storage.get_code_object(result_id)
    if code_object is None or code_object.embedding is None:
        return []

    # Search for similar documents using the embedding
    similar_docs = storage.search_documents(
        query_embedding=code_object.embedding,
        limit=limit,
    )

    # Convert to formatter-friendly format
    related_sections = []
    for doc_result in similar_docs:
        metadata = doc_result.get("metadata", {})
        content = doc_result.get("content", "")

        # Extract snippet (first 200 chars)
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
