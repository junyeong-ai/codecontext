"""Base formatter interface and shared utilities."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from codecontext_core.models import Relationship, RelationType, SearchResult

if TYPE_CHECKING:
    from codecontext_core import VectorStore


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
    """Extract callers, callees, contains from Relationships with total counts."""
    if storage is None:
        return {
            "callers": {"items": [], "total_count": 0},
            "callees": {"items": [], "total_count": 0},
            "contains": {"items": [], "total_count": 0},
            "similar": {"items": [], "total_count": 0},
        }

    result_id = result.chunk_id
    rels = storage.get_relationships(result_id)

    callers = []
    callees = []
    contains = []

    # Separate full lists for counting
    all_callers = []
    all_callees = []
    all_contains = []

    for rel in rels:
        if rel.relation_type == RelationType.CALLS and rel.target_id == result_id:
            caller_item = {
                "name": rel.source_type,
                "location": f"{rel.source_id}",
                "type": "direct_call",
            }
            all_callers.append(caller_item)
            callers.append(caller_item)

        if rel.relation_type == RelationType.CALLS and rel.source_id == result_id:
            callee_item = {
                "name": rel.target_type,
                "location": f"{rel.target_id}",
                "external": False,
            }
            all_callees.append(callee_item)
            callees.append(callee_item)

        if rel.relation_type == RelationType.CONTAINS and rel.source_id == result_id:
            contain_item = {"name": rel.target_type, "location": f"{rel.target_id}"}
            all_contains.append(contain_item)
            contains.append(contain_item)

    return {
        "callers": {"items": callers, "total_count": len(all_callers)},
        "callees": {"items": callees, "total_count": len(all_callees)},
        "contains": {"items": contains, "total_count": len(all_contains)},
        "similar": {"items": [], "total_count": 0},
    }


def count_recursive_callers(
    code_object_id: str, relationships: list[Relationship], visited: set[str] | None = None
) -> int:
    """Recursively count all callers (transitive closure)."""
    if visited is None:
        visited = set[Any]()

    if code_object_id in visited:
        return 0

    visited.add(code_object_id)

    direct_callers = [
        r.source_id
        for r in relationships
        if r.relation_type == RelationType.CALLS and r.target_id == code_object_id
    ]

    count = len(direct_callers)
    for caller_id in direct_callers:
        count += count_recursive_callers(caller_id, relationships, visited)

    return count


def calculate_transitive_impact(
    result: SearchResult, storage: "VectorStore | None"
) -> dict[str, Any]:
    """Calculate transitive impact (total callers via recursive traversal)."""
    if storage is None:
        return {"recursive_callers": 0}

    result_id = result.chunk_id
    rels = storage.get_relationships(result_id)

    # Compute recursive caller count (includes indirect callers)
    total_callers = count_recursive_callers(result_id, rels)

    return {"recursive_callers": total_callers}


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
