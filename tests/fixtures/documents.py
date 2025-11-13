"""Document-related test fixtures.

Provides reusable fixtures for DocumentNode and markdown testing,
reducing boilerplate in document and indexer tests.
"""

from typing import Any

import pytest
from codecontext.utils.checksum import calculate_content_checksum
from codecontext_core.models import DocumentNode, NodeType


@pytest.fixture
def sample_markdown_content():
    """Create sample markdown content for testing.

    Returns:
        Multi-section markdown string with headers, code refs, and content
    """
    return """# Main Title

Introduction paragraph with general context.

## Database Layer

We use MongoDB for data persistence.
The connection is managed via `MongoClient` in python/infra/mongodb.py.

### Connection Pooling

Connection pooling improves performance using `AsyncIOMotorClient`.

## API Layer

REST API built with FastAPI framework.
See `OrderController` for order endpoints and `UserController` for user management.

### Authentication

JWT tokens for authentication with refresh mechanism.
Tokens stored in `RefreshTokenRepository`.
"""


@pytest.fixture
def sample_markdown_simple():
    """Create simple markdown content for basic testing.

    Returns:
        Simple markdown with two sections
    """
    return """# Document Title

Some intro text.

## Section 1

Content for section 1.
This has multiple lines.

## Section 2

Content for section 2.
With `CodeReference` and python/file.py references.
"""


@pytest.fixture
def sample_markdown_no_headers():
    """Create markdown content without headers.

    Returns:
        Plain text markdown without any headers
    """
    return """This is plain text content without any markdown headers.
It has multiple lines but no structure.
Just regular paragraphs of text.
"""


@pytest.fixture
def sample_document_node():
    """Create a sample DocumentNode for testing.

    Returns:
        DocumentNode with realistic test data
    """
    content = "## Database Layer\n\nMongoDB persistence with `MongoClient`."
    return DocumentNode(
        file_path="docs/architecture.md",
        relative_path="docs/architecture.md",
        node_type=NodeType.MARKDOWN,
        content=content,
        checksum=calculate_content_checksum(content),
        chunk_index=0,
        total_chunks=3,
        title="Database Layer",
        keywords=["database", "mongodb", "persistence"],
        related_code=[
            {"name": "MongoClient", "confidence": 0.95},
            {"file_path": "python/infra/mongodb.py", "confidence": 0.90},
        ],
    )


def create_document_node(
    file_path: str = "test.md",
    content: str = "Test content",
    title: str | None = None,
    chunk_index: int = 0,
    keywords: list[str] | None = None,
    related_code: list[dict[str, Any]] | None = None,
) -> DocumentNode:
    """Factory function to create DocumentNode with custom values.

    Args:
        file_path: Path to the markdown file
        content: Markdown content
        title: Section title (optional)
        chunk_index: Index of this chunk
        keywords: List of extracted keywords (optional)
        related_code: List of code references (optional)

    Returns:
        DocumentNode instance

    Example:
        >>> doc = create_document_node(
        ...     file_path="docs/api.md",
        ...     content="API documentation",
        ...     title="REST API",
        ...     keywords=["api", "rest"]
        ... )
        >>> assert doc.title == "REST API"
    """
    return DocumentNode(
        file_path=file_path,
        relative_path=file_path,
        node_type=NodeType.MARKDOWN,
        content=content,
        checksum=calculate_content_checksum(content),
        chunk_index=chunk_index,
        total_chunks=1,
        title=title,
        keywords=keywords,
        related_code=related_code,
    )


def create_markdown_sections() -> list[dict]:
    """Factory function to create sample markdown sections.

    Returns:
        List of section dictionaries with title, content, and depth

    Example:
        >>> sections = create_markdown_sections()
        >>> assert len(sections) == 3
        >>> assert sections[0]["title"] == "Introduction"
    """
    return [
        {
            "title": "Introduction",
            "content": "Introduction to the system architecture.",
            "depth": 2,
            "keywords": ["introduction", "system", "architecture"],
        },
        {
            "title": "Database",
            "content": "MongoDB database with connection pooling.",
            "depth": 2,
            "keywords": ["database", "mongodb", "connection"],
        },
        {
            "title": "API Endpoints",
            "content": "REST API with FastAPI framework.",
            "depth": 2,
            "keywords": ["endpoints", "fastapi", "framework"],
        },
    ]


def create_code_reference_content() -> str:
    """Factory function to create content with various code reference patterns.

    Returns:
        Markdown content with backtick refs, file paths, and Class.method patterns

    Example:
        >>> content = create_code_reference_content()
        >>> assert "`MongoClient`" in content
        >>> assert "python/infra/mongodb.py" in content
    """
    return """
# Code References Example

Use `MongoClient` to connect to the database.
The implementation is in python/infra/mongodb.py.

Call `OrderService.createOrder` to create new orders.
Use `UserRepository.findById` for user lookups.

See kotlin/Driver.kt and typescript/api/OrderController.ts for examples.
"""


def create_keywords_content() -> str:
    """Factory function to create content for keyword extraction testing.

    Returns:
        Content with meaningful words, stopwords, and short words

    Example:
        >>> content = create_keywords_content()
        >>> assert "authentication" in content
        >>> assert "implementation" in content
    """
    return """
The system is designed to provide the best performance and security.
It uses the latest technology and follows industry best practices.
The implementation is robust, reliable, and scalable for production use.
Authentication uses JWT tokens with refresh mechanisms.
"""


@pytest.fixture
def temp_markdown_file(tmp_path):
    """Create a temporary markdown file for testing.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        Tuple of (file_path, content)
    """
    content = """# Test Document

## Section 1

Test content for section 1.

## Section 2

Test content for section 2.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content)
    return file_path, content


__all__ = [
    # Fixtures
    "sample_markdown_content",
    "sample_markdown_simple",
    "sample_markdown_no_headers",
    "sample_document_node",
    "temp_markdown_file",
    # Factory functions
    "create_document_node",
    "create_markdown_sections",
    "create_code_reference_content",
    "create_keywords_content",
]
