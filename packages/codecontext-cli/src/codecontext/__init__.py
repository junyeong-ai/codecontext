"""CodeContext - Intelligent Code Search Engine CLI."""

__version__ = "0.1.0"
__author__ = "CodeContext Contributors"
__description__ = "Intelligent code search engine for indexing and querying codebases"

from codecontext_core.models import (
    CodeObject,
    DocumentNode,
    IndexState,
    Language,
    ObjectType,
    Relationship,
    SearchQuery,
    SearchResult,
)

__all__ = [
    "CodeObject",
    "DocumentNode",
    "IndexState",
    "Language",
    "ObjectType",
    "Relationship",
    "SearchQuery",
    "SearchResult",
    "__author__",
    "__description__",
    "__version__",
]
