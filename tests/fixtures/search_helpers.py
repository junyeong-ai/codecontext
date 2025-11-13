"""Search result test fixtures and helpers."""

from pathlib import Path
from typing import Any

from codecontext_core.models.search_results import SearchResult, SearchScoring


def create_hybrid_search_result(
    chunk_id: str = "test_chunk_001",
    file_path: str | Path = "src/test.py",
    content: str = "def test():\n    pass",
    nl_description: str = "Test function",
    bm25_score: float | None = 0.8,
    vector_code_score: float | None = 0.7,
    final_score: float = 0.75,
    language: str = "python",
    node_type: str = "function",
    start_line: int = 1,
    end_line: int = 2,
    metadata: dict | None = None,
) -> SearchResult:
    """Create a SearchResult for testing.

    Args:
        chunk_id: Unique identifier for the chunk
        file_path: Path to the source file
        content: Code content
        nl_description: Natural language description
        bm25_score: BM25 keyword search score
        vector_code_score: Vector similarity score
        final_score: Final fused score
        language: Programming language
        node_type: Type of code node
        start_line: Starting line number
        end_line: Ending line number
        metadata: Additional metadata

    Returns:
        SearchResult instance
    """
    scoring = SearchScoring(
        bm25_score=bm25_score,
        vector_code_score=vector_code_score,
        final_score=final_score,
    )

    if metadata is None:
        metadata = {
            "deterministic_id": chunk_id,
            "file_path": str(file_path),
            "object_type": node_type,
            "language": language,
        }

    return SearchResult(
        chunk_id=chunk_id,
        file_path=Path(file_path) if isinstance(file_path, str) else file_path,
        content=content,
        nl_description=nl_description,
        scoring=scoring,
        language=language,
        node_type=node_type,
        start_line=start_line,
        end_line=end_line,
        metadata=metadata,
    )


def create_code_search_result(
    name: str = "test_function",
    file_path: str = "src/module.py",
    score: float = 0.85,
    chunk_id: str | None = None,
    content: str | None = None,
    **kwargs: dict[str, Any],
) -> HybridSearchResult:
    """Create a code-specific HybridSearchResult.

    Args:
        name: Name of the code entity
        file_path: Path to source file
        score: Search score
        chunk_id: Optional chunk ID (defaults to f"code_{name}")
        content: Optional code content (defaults to simple function definition)
        **kwargs: Additional arguments for create_hybrid_search_result

    Returns:
        HybridSearchResult configured for code results
    """
    if chunk_id is None:
        chunk_id = f"code_{name}"

    if content is None:
        content = f"def {name}():\n    pass"

    # Merge name into metadata (allow override via kwargs)
    metadata = kwargs.pop("metadata", {})
    metadata.setdefault("name", name)
    metadata.setdefault("deterministic_id", chunk_id)

    # Allow node_type override via kwargs, default to "function"
    node_type = kwargs.pop("node_type", "function")

    # Allow nl_description override via kwargs
    nl_description = kwargs.pop("nl_description", f"{name} function")

    return create_hybrid_search_result(
        chunk_id=chunk_id,
        file_path=file_path,
        content=content,
        nl_description=nl_description,
        final_score=score,
        node_type=node_type,
        metadata=metadata,
        **kwargs,
    )


def create_document_search_result(
    title: str = "Introduction",
    file_path: str = "docs/README.md",
    score: float = 0.75,
    content: str | None = None,
    **kwargs: dict[str, Any],
) -> HybridSearchResult:
    """Create a document-specific HybridSearchResult.

    Args:
        title: Document section title
        file_path: Path to document file
        score: Search score
        content: Optional document content (defaults to simple header)
        **kwargs: Additional arguments for create_hybrid_search_result

    Returns:
        HybridSearchResult configured for document results
    """
    metadata = kwargs.pop("metadata", {})
    metadata.update(
        {
            "title": title,
            "section_title": title,
            "node_type": "markdown",
        }
    )

    if content is None:
        content = f"# {title}\n\nDocument content..."

    return create_hybrid_search_result(
        chunk_id=f"doc_{title}",
        file_path=file_path,
        content=content,
        nl_description=title,
        final_score=score,
        node_type="markdown",
        metadata=metadata,
        **kwargs,
    )


def create_config_search_result(
    config_key: str = "database.host",
    file_path: str = "config/application.yaml",
    score: float = 0.70,
    title: str | None = None,
    content: str | None = None,
    **kwargs: dict[str, Any],
) -> HybridSearchResult:
    """Create a config-specific HybridSearchResult.

    Args:
        config_key: Configuration key path
        file_path: Path to config file
        score: Search score
        title: Optional section title (defaults to config_key)
        content: Optional config content
        **kwargs: Additional arguments for create_hybrid_search_result

    Returns:
        HybridSearchResult configured for config results
    """
    if title is None:
        title = config_key

    if content is None:
        content = f"{config_key}: value"

    chunk_id = f"config_{config_key}"
    metadata = kwargs.pop("metadata", {})

    # Set defaults (can be overridden by metadata param)
    metadata.setdefault("config_keys", [config_key])
    metadata.setdefault("config_format", "yaml")
    metadata.setdefault("title", title)
    metadata.setdefault("file_path", file_path)
    metadata.setdefault("deterministic_id", chunk_id)

    return create_hybrid_search_result(
        chunk_id=chunk_id,
        file_path=file_path,
        content=content,
        nl_description=f"Configuration for {config_key}",
        final_score=score,
        node_type="config",
        metadata=metadata,
        **kwargs,
    )
