"""ChromaDB utility functions."""

from typing import Any


def format_query_results(results: dict[str, Any]) -> list[dict[str, Any]]:
    """Format ChromaDB query results into standardized format.

    Args:
        results: Raw results from ChromaDB query

    Returns:
        List of formatted result dictionaries with id, score, metadata, document
    """
    formatted_results = []
    if results["ids"] and len(results["ids"]) > 0:
        for i in range(len(results["ids"][0])):
            formatted_results.append(
                {
                    "id": results["ids"][0][i],
                    "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "document": results["documents"][0][i] if results["documents"] else "",
                }
            )
    return formatted_results
