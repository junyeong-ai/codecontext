"""Storage-related test fixtures.

Provides reusable fixtures for ChromaDB and storage testing,
reducing boilerplate in storage unit tests.
"""

from typing import Any
from unittest.mock import Mock

import pytest
from codecontext.config.schema import ChromaDBConfig, StorageConfig

# Import from storage-chromadb package (plugin architecture)
ChromaDBProvider: type[Any] | None = None
try:
    from codecontext_storage_chromadb.provider import ChromaDBVectorStore as _ChromaDBVectorStore

    ChromaDBProvider = _ChromaDBVectorStore
except ImportError:
    # Fallback for tests that don't need actual storage provider
    pass


@pytest.fixture
def mock_chromadb_collection():
    """Create a mock ChromaDB collection.

    Returns:
        Mock Collection with standard methods (get, query, add, upsert, delete)
    """
    collection = Mock()
    collection.get = Mock(return_value={"ids": [], "metadatas": [], "documents": []})
    collection.query = Mock(return_value={"ids": [[]], "metadatas": [[]], "distances": [[]]})
    collection.add = Mock()
    collection.upsert = Mock()
    collection.delete = Mock()
    collection.count = Mock(return_value=0)
    return collection


@pytest.fixture
def chromadb_config():
    """Create ChromaDB configuration for testing.

    Returns:
        ChromaDBConfig with test-friendly settings
    """
    return ChromaDBConfig(host="localhost", port=8000, collection_name="test_collection")


@pytest.fixture
def storage_config():
    """Create storage configuration for testing.

    Returns:
        StorageConfig with ChromaDB provider settings
    """
    return StorageConfig(
        provider="chromadb",
        chromadb=ChromaDBConfig(host="localhost", port=8000, collection_name="test_collection"),
    )


@pytest.fixture
def mock_chromadb_provider(mock_chromadb_collection):
    """Create a mock ChromaDBProvider with initialized collections.

    Args:
        mock_chromadb_collection: Mock collection fixture

    Returns:
        Mock ChromaDBProvider with all collections set up
    """
    provider = Mock(spec=ChromaDBProvider)

    # Mock collections
    provider.collections = Mock()
    provider.collections.code_objects_collection = mock_chromadb_collection
    provider.collections.documents_collection = mock_chromadb_collection
    provider.collections.relationships_collection = mock_chromadb_collection
    provider.collections.state_collection = mock_chromadb_collection

    # Mock stores
    provider.code_objects = Mock()
    provider.relationships = Mock()
    provider.state = Mock()

    # Mock methods
    provider.initialize = Mock()
    provider.close = Mock()
    provider.add_code_objects = Mock()
    provider.add_documents = Mock()
    provider.add_relationships = Mock()
    provider.search_code_objects = Mock(return_value=[])
    provider.search_documents = Mock(return_value=[])
    provider.get_code_object = Mock(return_value=None)
    provider.get_document = Mock(return_value=None)
    provider.get_relationships = Mock(return_value=[])

    return provider


@pytest.fixture
def relationship_store(mock_chromadb_collection):
    """Create mock RelationshipStore for testing.

    Args:
        mock_chromadb_collection: Mock collection fixture

    Returns:
        Mock RelationshipStore with get_batch method
    """
    store = Mock()
    store.collection = mock_chromadb_collection
    store.get_batch = Mock(return_value=[])
    store.add = Mock()
    store.get = Mock(return_value=[])
    return store


def create_mock_chromadb_result(
    ids: list[str], metadatas: list[dict], documents: list[str] | None = None
):
    """Factory function to create mock ChromaDB query result.

    Args:
        ids: List of document IDs
        metadatas: List of metadata dictionaries
        documents: Optional list of document contents

    Returns:
        Dict matching ChromaDB result format

    Example:
        >>> result = create_mock_chromadb_result(
        ...     ids=["id1", "id2"],
        ...     metadatas=[{"name": "obj1"}, {"name": "obj2"}],
        ...     documents=["content1", "content2"]
        ... )
        >>> assert len(result["ids"]) == 2
    """
    result = {
        "ids": ids,
        "metadatas": metadatas,
        "documents": documents or [""] * len(ids),
        "distances": [[0.5] * len(ids)] if ids else [[]],
    }
    return result


def create_empty_chromadb_result():
    """Factory function to create empty ChromaDB result.

    Returns:
        Empty result dict

    Example:
        >>> result = create_empty_chromadb_result()
        >>> assert len(result["ids"]) == 0
    """
    return {
        "ids": [],
        "metadatas": [],
        "documents": [],
        "distances": [[]],
    }


__all__ = [
    "chromadb_config",
    "create_empty_chromadb_result",
    "create_mock_chromadb_result",
    "mock_chromadb_collection",
    "mock_chromadb_provider",
    "relationship_store",
    "storage_config",
]
