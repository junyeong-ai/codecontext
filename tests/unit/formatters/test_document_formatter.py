"""Unit tests for document response formatting."""

import json
from pathlib import Path

import pytest
from codecontext.formatters.document_formatter import DocumentFormatter
from codecontext_core.models import SearchResult, SearchScoring


@pytest.fixture
def sample_document_result():
    """Create sample document search result."""
    return SearchResult(
        chunk_id="doc_arch_123",
        file_path=Path("docs/architecture.md"),
        content="""## Database Architecture

We use MongoDB for data persistence.
The connection is managed via `MongoClient`.
See python/infra/mongodb.py for implementation.""",
        nl_description="Database architecture documentation",
        scoring=SearchScoring(final_score=0.85),
        node_type="document",
        language="markdown",
        start_line=10,
        end_line=25,
        metadata={
            "section_title": "Database Architecture",
            "keywords": ["database", "mongodb", "connection", "pooling"],
            "related_code": [
                {"name": "MongoClient", "type": "code_ref", "match_reason": "backtick reference"},
                {
                    "name": "python/infra/mongodb.py",
                    "type": "file_ref",
                    "match_reason": "file reference",
                },
            ],
            "rank": 1,
        },
    )


def test_format_document_results(sample_document_result):
    """Test basic document result formatting."""
    results = [sample_document_result]
    query = "database architecture"

    formatter = DocumentFormatter()
    output = formatter.format(results, query, storage=None)
    response = json.loads(output)

    assert response["total"] == 1
    assert response["query"] == query
    assert len(response["results"]) == 1


def test_related_code_populated(sample_document_result):
    """Test that related_code is populated."""
    results = [sample_document_result]

    formatter = DocumentFormatter()
    output = formatter.format(results, "test query", storage=None)
    response = json.loads(output)

    result = response["results"][0]
    assert "related_code" in result
    assert len(result["related_code"]) == 2

    # Check structure
    assert result["related_code"][0]["name"] == "MongoClient"
    assert result["related_code"][0]["match_reason"] == "backtick reference"


def test_document_result_structure(sample_document_result):
    """Test that document result has expected structure without related_sections.

    Note: related_sections is not included for document results because it was
    designed to find related documents for CODE results using code object embeddings.
    Documents already have related_code for code references.
    """
    results = [sample_document_result]

    formatter = DocumentFormatter()
    output = formatter.format(results, "test query", storage=None)
    response = json.loads(output)

    result = response["results"][0]
    # Documents have related_code but not related_sections
    assert "related_code" in result
    assert "related_sections" not in result


def test_document_response_schema_valid(sample_document_result):
    """Test that document response matches expected schema."""
    results = [sample_document_result]

    formatter = DocumentFormatter()
    output = formatter.format(results, "test query", storage=None)
    response = json.loads(output)

    result = response["results"][0]

    # Check location structure
    assert "location" in result
    assert result["location"]["file"] == "docs/architecture.md"
    assert result["location"]["section"] == "Database Architecture"


def test_snippet_preview_lines(sample_document_result):
    """Test that snippet preview is limited to 5 lines."""
    results = [sample_document_result]

    formatter = DocumentFormatter()
    output = formatter.format(results, "test query", storage=None)
    response = json.loads(output)

    result = response["results"][0]
    preview = result["snippet"]["preview"]

    assert len(preview) <= 5
    assert isinstance(preview, list)


def test_multiple_document_results():
    """Test formatting multiple document results."""
    results = [
        SearchResult(
            chunk_id="doc_api_123",
            file_path=Path("docs/api.md"),
            content="## API Endpoints\n\nList of endpoints...",
            scoring=SearchScoring(final_score=0.9),
            node_type="document",
            language="markdown",
            start_line=5,
            end_line=15,
            metadata={
                "section_title": "API Endpoints",
                "keywords": ["api", "endpoints"],
                "related_code": [],
                "rank": 1,
            },
        ),
        SearchResult(
            chunk_id="doc_auth_456",
            file_path=Path("docs/auth.md"),
            content="## Authentication\n\nJWT tokens...",
            scoring=SearchScoring(final_score=0.75),
            node_type="document",
            language="markdown",
            start_line=20,
            end_line=35,
            metadata={
                "section_title": "Authentication",
                "keywords": ["auth", "jwt"],
                "related_code": [],
                "rank": 2,
            },
        ),
    ]

    formatter = DocumentFormatter()
    output = formatter.format(results, "test query", storage=None)
    response = json.loads(output)

    assert response["total"] == 2
    assert len(response["results"]) == 2


def test_empty_related_code():
    """Test handling empty related_code."""
    result = SearchResult(
        chunk_id="doc_no_code_ref",
        file_path=Path("docs/plain.md"),
        content="## Plain Section\n\nNo code references.",
        scoring=SearchScoring(final_score=0.8),
        node_type="document",
        language="markdown",
        start_line=1,
        end_line=5,
        metadata={
            "section_title": "Plain",
            "keywords": [],
            "related_code": [],
            "rank": 1,
        },
    )

    formatter = DocumentFormatter()
    output = formatter.format([result], "test", storage=None)
    response = json.loads(output)

    assert response["results"][0]["related_code"] == []
