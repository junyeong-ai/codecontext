"""Storage-related test fixtures.

Provides reusable fixtures for Qdrant and storage testing,
reducing boilerplate in storage unit tests.
"""

from unittest.mock import Mock

import pytest
from codecontext.config.schema import QdrantConfig, StorageConfig


@pytest.fixture
def qdrant_config():
    """Create Qdrant configuration for testing.

    Returns:
        QdrantConfig with test-friendly settings
    """
    return QdrantConfig(mode="embedded", path=":memory:", collection_name="test_collection")


@pytest.fixture
def storage_config():
    """Create storage configuration for testing.

    Returns:
        StorageConfig with Qdrant provider settings
    """
    return StorageConfig(
        provider="qdrant",
        qdrant=QdrantConfig(mode="embedded", path=":memory:", collection_name="test_collection"),
    )


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client.

    Returns:
        Mock QdrantClient with standard methods
    """
    client = Mock()
    client.get_collection = Mock(return_value=Mock(points_count=0))
    client.retrieve = Mock(return_value=[])
    client.query = Mock(return_value=[])
    client.query_points = Mock(return_value=Mock(points=[]))
    client.upsert = Mock()
    client.delete = Mock()
    client.count = Mock(return_value=Mock(count=0))
    client.close = Mock()
    return client


@pytest.fixture
def mock_qdrant_provider(mock_qdrant_client):
    """Create a mock QdrantProvider.

    Args:
        mock_qdrant_client: Mock Qdrant client fixture

    Returns:
        Mock QdrantProvider with all methods set up
    """
    provider = Mock()
    provider.client = mock_qdrant_client

    # Mock methods
    provider.initialize = Mock()
    provider.close = Mock()
    provider.add_code_objects = Mock()
    provider.add_documents = Mock()
    provider.add_relationships = Mock()
    provider.search = Mock(return_value=[])
    provider.get_code_object = Mock(return_value=None)
    provider.get_code_objects_batch = Mock(return_value=[])
    provider.get_relationships = Mock(return_value=[])
    provider.delete_code_objects = Mock()

    return provider


@pytest.fixture
def relationship_store(mock_qdrant_client):
    """Create mock relationship store for testing.

    Args:
        mock_qdrant_client: Mock Qdrant client fixture

    Returns:
        Mock relationship store with get_batch method
    """
    store = Mock()
    store.client = mock_qdrant_client
    store.get_batch = Mock(return_value=[])
    store.add = Mock()
    store.get = Mock(return_value=[])
    return store


def create_mock_search_result(
    ids: list[str],
    metadatas: list[dict],
    contents: list[str] | None = None,
    scores: list[float] | None = None,
):
    """Factory function to create mock search result.

    Args:
        ids: List of object IDs
        metadatas: List of metadata dictionaries
        contents: Optional list of content strings
        scores: Optional list of relevance scores

    Returns:
        List of search result dicts

    Example:
        >>> result = create_mock_search_result(
        ...     ids=["id1", "id2"],
        ...     metadatas=[{"name": "obj1"}, {"name": "obj2"}],
        ...     contents=["content1", "content2"],
        ...     scores=[0.9, 0.8]
        ... )
        >>> assert len(result) == 2
    """
    results = []
    for i, obj_id in enumerate(ids):
        results.append(
            {
                "id": obj_id,
                "metadata": metadatas[i],
                "content": contents[i] if contents else "",
                "score": scores[i] if scores else 0.5,
            }
        )
    return results


def create_empty_search_result():
    """Factory function to create empty search result.

    Returns:
        Empty result list

    Example:
        >>> result = create_empty_search_result()
        >>> assert len(result) == 0
    """
    return []


__all__ = [
    "create_empty_search_result",
    "create_mock_search_result",
    "mock_qdrant_client",
    "mock_qdrant_provider",
    "qdrant_config",
    "relationship_store",
    "storage_config",
]
