from pathlib import Path
from unittest.mock import Mock

import pytest
from codecontext.formatters.base_formatter import find_related_sections
from codecontext_core.models import SearchResult, SearchScoring


@pytest.fixture
def sample_search_result():
    return SearchResult(
        chunk_id="abc123deterministic",
        file_path=Path("src/main.py"),
        content="def calculate_tax(amount): return amount * 0.15",
        nl_description="Calculate tax based on amount",
        scoring=SearchScoring(final_score=0.9),
        node_type="function",
        language="python",
        start_line=10,
        end_line=20,
        metadata={
            "deterministic_id": "abc123deterministic",
            "name": "calculate_tax",
            "object_type": "function",
            "rank": 1,
        },
    )


@pytest.fixture
def mock_code_object():
    code_obj = Mock()
    code_obj.embedding = [0.1, 0.2, 0.3] * 256
    return code_obj


@pytest.fixture
def mock_storage(mock_code_object):
    storage = Mock()
    storage.get_code_object.return_value = mock_code_object
    storage.search_documents.return_value = [
        {
            "id": "doc1",
            "score": 0.88,
            "content": "This is a tax calculation guide. " * 10,
            "metadata": {
                "title": "Tax Calculation Guide",
                "file_path": "docs/tax.md",
            },
        },
        {
            "id": "doc2",
            "score": 0.75,
            "content": "Short doc",
            "metadata": {
                "title": "Tax Overview",
                "file_path": "docs/overview.md",
            },
        },
    ]
    return storage


class TestFindRelatedSections:
    """Test find_related_sections function."""

    def test_returns_empty_when_no_storage(self, sample_search_result):
        """Test returns empty list when storage is None."""
        result = find_related_sections(sample_search_result, None)
        assert result == []

    def test_returns_empty_when_code_object_not_found(self, sample_search_result):
        """Test returns empty when code object doesn't exist."""
        storage = Mock()
        storage.get_code_object.return_value = None

        result = find_related_sections(sample_search_result, storage)
        assert result == []

    def test_returns_empty_when_no_embedding(self, sample_search_result):
        """Test returns empty when code object has no embedding."""
        storage = Mock()
        code_obj = Mock()
        code_obj.embedding = None
        storage.get_code_object.return_value = code_obj

        result = find_related_sections(sample_search_result, storage)
        assert result == []

    def test_result_structure(self, sample_search_result, mock_storage):
        """Test that results have correct structure."""
        result = find_related_sections(sample_search_result, mock_storage, limit=3)

        assert len(result) == 2  # Mock returns 2 documents
        for item in result:
            assert "title" in item
            assert "file" in item
            assert "score" in item
            assert "snippet" in item
            assert isinstance(item["score"], float)

    def test_snippet_truncation(self, sample_search_result, mock_storage):
        """Test that long content is truncated."""
        result = find_related_sections(sample_search_result, mock_storage)

        # First doc has long content (>200 chars)
        assert "..." in result[0]["snippet"]
        assert len(result[0]["snippet"]) <= 203  # 200 + "..."

        # Second doc has short content
        assert result[1]["snippet"] == "Short doc"

    def test_respects_limit(self, sample_search_result, mock_storage):
        """Test that result limit is passed to search."""
        find_related_sections(sample_search_result, mock_storage, limit=5)

        # Verify search_documents was called with correct limit
        mock_storage.search_documents.assert_called_once()
        call_args = mock_storage.search_documents.call_args
        assert call_args.kwargs["limit"] == 5

    def test_uses_code_object_embedding(self, sample_search_result, mock_storage, mock_code_object):
        """Test that code object embedding is used for document search."""
        find_related_sections(sample_search_result, mock_storage)

        # Verify search_documents was called with correct embedding
        call_args = mock_storage.search_documents.call_args
        assert call_args.kwargs["query_embedding"] == mock_code_object.embedding
