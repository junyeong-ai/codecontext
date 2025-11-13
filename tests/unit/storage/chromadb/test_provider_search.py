"""Tests for ChromaDB retrieval functionality.

These tests verify the retrieval methods for code objects, relationships,
and search functionality in ChromaDBVectorStore.
"""

from unittest.mock import Mock

import pytest
from codecontext.config.schema import ChromaDBConfig
from codecontext_core.exceptions import StorageError
from codecontext_core.models import Language, ObjectType, RelationType
from codecontext_storage_chromadb.provider import ChromaDBVectorStore

from tests.helpers import create_test_code_object, create_test_relationship


class TestCodeObjectRetrieval:
    """Test code object retrieval methods."""

    @pytest.fixture
    def chromadb_provider_with_mocks(self):
        """Create a ChromaDBVectorStore with mocked collections for testing."""
        config = ChromaDBConfig(host="localhost", port=8000)
        provider = ChromaDBVectorStore(config, project_id="test_project")

        # Mock client
        provider.client = Mock()

        # Mock collections (no HTTP calls)
        provider.collections["content"] = Mock()
        provider.collections["meta"] = Mock()

        # Initialize stores with mocked collections

        return provider

    def test_get_code_object_by_id(self, chromadb_provider_with_mocks):
        """Should retrieve code object by its ID."""
        # Create test object
        obj = create_test_code_object(
            name="TestClass", file_path="/test/file.py", object_type=ObjectType.CLASS
        )
        obj.embedding = [0.1] * 1024
        obj_id = obj.generate_deterministic_id()

        # Configure mock to return the object
        chromadb_provider_with_mocks.collections["content"].get.return_value = {
            "ids": [obj_id],
            "metadatas": [obj.to_metadata()],
            "embeddings": [[0.1] * 1024],
            "documents": [obj.content],
        }

        # Retrieve by deterministic ID
        retrieved = chromadb_provider_with_mocks.get_code_object(obj_id)

        # Verify
        assert retrieved is not None
        assert retrieved.name == "TestClass"
        assert retrieved.file_path == "/test/file.py"
        assert retrieved.object_type == ObjectType.CLASS

    def test_get_nonexistent_object_returns_none(self, chromadb_provider_with_mocks):
        """Should return None for non-existent object ID."""
        fake_id = "nonexistent_id_12345678901234567890123456789012"

        # Configure mock to return empty result
        chromadb_provider_with_mocks.collections["content"].get.return_value = {
            "ids": [],
            "metadatas": [],
            "embeddings": [],
            "documents": [],
        }

        result = chromadb_provider_with_mocks.get_code_object(fake_id)

        assert result is None

    def test_search_code_objects_by_embedding(self, chromadb_provider_with_mocks):
        """Should search and return similar code objects."""
        # Create test objects
        objects = []
        for i in range(3):
            obj = create_test_code_object(
                name=f"Class{i}", file_path=f"/test/file{i}.py", object_type=ObjectType.CLASS
            )
            obj.embedding = [0.1 + i * 0.01] * 1024
            objects.append(obj)

        # Configure mock to return search results
        chromadb_provider_with_mocks.collections["content"].query.return_value = {
            "ids": [[obj.generate_deterministic_id() for obj in objects]],
            "metadatas": [[obj.to_metadata() for obj in objects]],
            "embeddings": [[obj.embedding for obj in objects]],
            "distances": [[0.1, 0.2, 0.3]],
            "documents": [[obj.content for obj in objects]],
        }

        # Search with similar embedding
        query_embedding = [0.12] * 1024
        results = chromadb_provider_with_mocks.search_code_objects(
            query_embedding=query_embedding, limit=3
        )

        # Verify
        assert len(results) <= 3
        assert len(results) > 0
        # Results should be sorted by similarity
        assert all("id" in r for r in results)
        assert all("metadata" in r for r in results)

    def test_search_with_language_filter(self, chromadb_provider_with_mocks):
        """Should filter search results by language."""
        # Create test object with Python language
        py_obj = create_test_code_object(
            name="PythonClass", language=Language.PYTHON, file_path="/test/file.py"
        )
        py_obj.embedding = [0.1] * 1024

        # Configure mock to return only Python results
        chromadb_provider_with_mocks.collections["content"].query.return_value = {
            "ids": [[py_obj.generate_deterministic_id()]],
            "metadatas": [[py_obj.to_metadata()]],
            "embeddings": [[py_obj.embedding]],
            "distances": [[0.1]],
            "documents": [[py_obj.content]],
        }

        # Search with language filter
        query_embedding = [0.1] * 1024
        results = chromadb_provider_with_mocks.search_code_objects(
            query_embedding=query_embedding, limit=10, language_filter="python"
        )

        # Verify only Python results
        assert len(results) == 1
        assert results[0]["metadata"]["language"] == "python"

    def test_search_with_file_filter(self, chromadb_provider_with_mocks):
        """Should filter search results by file path."""
        # Create test object with specific file path
        obj1 = create_test_code_object(name="Class1", file_path="/project/src/main.py")
        obj1.embedding = [0.1] * 1024

        # Configure mock to return only filtered results
        chromadb_provider_with_mocks.collections["content"].query.return_value = {
            "ids": [[obj1.generate_deterministic_id()]],
            "metadatas": [[obj1.to_metadata()]],
            "embeddings": [[obj1.embedding]],
            "distances": [[0.1]],
            "documents": [[obj1.content]],
        }

        # Search with exact file filter
        query_embedding = [0.1] * 1024
        results = chromadb_provider_with_mocks.search_code_objects(
            query_embedding=query_embedding, limit=10, file_filter="/project/src/main.py"
        )

        # Verify filtered results
        assert len(results) == 1
        assert results[0]["metadata"]["file_path"] == "/project/src/main.py"


class TestRelationshipRetrieval:
    """Test relationship retrieval methods."""

    @pytest.fixture
    def chromadb_provider_with_mocks(self):
        """Create a ChromaDBVectorStore with mocked collections for testing."""
        config = ChromaDBConfig(host="localhost", port=8000)
        provider = ChromaDBVectorStore(config, project_id="test_project")

        # Mock client
        provider.client = Mock()

        # Mock collections (no HTTP calls)
        provider.collections["content"] = Mock()
        provider.collections["meta"] = Mock()

        # Initialize stores with mocked collections

        return provider

    def test_get_relationships_for_object(self, chromadb_provider_with_mocks):
        """Should retrieve all relationships for a source object."""
        # Create test objects
        source_obj = create_test_code_object(name="SourceClass")
        target_objs = [create_test_code_object(name=f"TargetClass{i}") for i in range(3)]

        # Create relationships
        relationships = []
        for target_obj in target_objs:
            rel = create_test_relationship(
                source_id=source_obj.deterministic_id,
                target_id=target_obj.deterministic_id,
                relation_type=RelationType.CALLS,
            )
            relationships.append(rel)

        # Configure mock to return relationships
        chromadb_provider_with_mocks.collections["meta"].get.return_value = {
            "ids": [f"rel{i}" for i in range(3)],
            "metadatas": [rel.to_metadata() for rel in relationships],
        }

        # Retrieve
        retrieved = chromadb_provider_with_mocks.get_relationships(source_obj.deterministic_id)

        # Verify
        assert len(retrieved) == 3
        assert all(str(r.source_id) == source_obj.deterministic_id for r in retrieved)

    def test_get_relationships_with_type_filter(self, chromadb_provider_with_mocks):
        """Should filter relationships by type."""
        # Create test objects
        source_obj = create_test_code_object(name="SourceClass")
        target1_obj = create_test_code_object(name="Target1Class")

        # Create CALLS relationship
        rel1 = create_test_relationship(
            source_id=source_obj.deterministic_id,
            target_id=target1_obj.deterministic_id,
            relation_type=RelationType.CALLS,
        )

        # Configure mock to return only CALLS relationships
        chromadb_provider_with_mocks.collections["meta"].get.return_value = {
            "ids": ["rel1"],
            "metadatas": [rel1.to_metadata()],
        }

        # Retrieve with filter
        retrieved = chromadb_provider_with_mocks.get_relationships(
            source_id=source_obj.deterministic_id, relation_type="calls"
        )

        # Verify
        assert len(retrieved) == 1
        assert retrieved[0].relation_type == RelationType.CALLS

    def test_get_relationships_for_nonexistent_object(self, chromadb_provider_with_mocks):
        """Should return empty list for object with no relationships."""
        # Create a fake object but don't add any relationships for it
        fake_obj = create_test_code_object(name="FakeClass")
        fake_id = fake_obj.deterministic_id

        # Configure mock to return empty results
        chromadb_provider_with_mocks.collections["meta"].get.return_value = {
            "ids": [],
            "metadatas": [],
        }

        retrieved = chromadb_provider_with_mocks.get_relationships(fake_id)

        assert retrieved == []


class TestStorageErrors:
    """Test error handling in storage operations."""

    def test_search_without_initialization_raises_error(self):
        """Should raise error when searching before initialization."""
        config = ChromaDBConfig(host="localhost", port=8000)
        provider = ChromaDBVectorStore(config, project_id="test_project")
        # Don't initialize

        query_embedding = [0.1] * 1024

        with pytest.raises(StorageError, match="not initialized"):
            provider.search_code_objects(query_embedding)

    def test_get_code_object_without_initialization_raises_error(self):
        """Should raise error when retrieving before initialization."""
        config = ChromaDBConfig(host="localhost", port=8000)
        provider = ChromaDBVectorStore(config, project_id="test_project")
        # Don't initialize

        with pytest.raises(StorageError, match="not initialized"):
            provider.get_code_object("some_id")

    def test_get_relationships_without_initialization_raises_error(self):
        """Should raise error when getting relationships before initialization."""
        config = ChromaDBConfig(host="localhost", port=8000)
        provider = ChromaDBVectorStore(config, project_id="test_project")
        # Don't initialize

        # Create a test object for the ID
        test_obj = create_test_code_object(name="TestClass")

        with pytest.raises(StorageError, match="not initialized"):
            provider.get_relationships(test_obj.deterministic_id)
