"""Document utility functions (not pytest fixtures).

This module contains helper functions for creating test documents.
It is separate from documents.py to avoid pytest assertion rewrite warnings.

documents.py contains pytest fixtures and is registered via pytest_plugins.
document_helpers.py contains utility functions and can be safely imported.
"""

from codecontext_core.models import DocumentNode, Language


def create_document_node(
    content: str = "Sample document content",
    file_path: str = "/docs/README.md",
    relative_path: str = "README.md",
    language: Language = Language.MARKDOWN,
    **kwargs,
) -> DocumentNode:
    """Create a DocumentNode with sensible defaults for testing.

    Args:
        content: Document content
        file_path: Full file path
        relative_path: Relative path from project root
        language: Document language
        **kwargs: Additional fields to override

    Returns:
        Configured DocumentNode instance

    Example:
        >>> doc = create_document_node(content="# Hello", file_path="/docs/hello.md")
        >>> assert doc.content == "# Hello"
        >>> assert doc.language == Language.MARKDOWN
    """
    defaults = {
        "content": content,
        "file_path": file_path,
        "relative_path": relative_path,
        "language": language,
        "section_title": kwargs.get("section_title", "Introduction"),
        "keywords": kwargs.get("keywords", ["sample", "test"]),
        "code_references": kwargs.get("code_references", []),
    }
    defaults.update(kwargs)
    return DocumentNode(**defaults)


def create_markdown_sections() -> list[dict]:
    """Create sample markdown sections for testing.

    Returns:
        List of section dictionaries with title, content, and level
    """
    return [
        {"title": "Getting Started", "content": "This is the introduction.", "level": 1},
        {
            "title": "Installation",
            "content": "Run `pip install codecontext` to install.",
            "level": 2,
        },
        {"title": "Usage", "content": "Import and use the library.", "level": 2},
        {
            "title": "Advanced Features",
            "content": "Learn about advanced configurations.",
            "level": 1,
        },
    ]


def create_code_reference_content() -> str:
    """Create markdown content with code references for testing.

    Returns:
        Markdown string containing various code reference formats
    """
    return """
# API Documentation

The `BaseCodeParser` class handles parsing.
See `parser.py:42` for implementation details.

## Methods

- `extract_classes()` - Extracts class definitions
- `extract_functions()` - Extracts function definitions

Reference: `src/parsers/base.py`
"""


def create_keywords_content() -> str:
    """Create markdown content rich in keywords for testing.

    Returns:
        Markdown string with identifiable keywords
    """
    return """
# Python Programming Guide

Python is a high-level programming language. It supports object-oriented,
functional, and procedural programming paradigms. Python is widely used
for web development, data analysis, machine learning, and automation.

## Key Features

- Dynamic typing
- Garbage collection
- Extensive standard library
- Cross-platform compatibility
"""
