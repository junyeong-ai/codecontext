"""Tests for ChromaDB upsert functionality and deterministic IDs.

These tests verify the critical functionality added to prevent duplicate
indexing and ensure data integrity during re-indexing.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest
from codecontext.config.schema import ChromaDBConfig
from codecontext_core.models import ObjectType
from codecontext_storage_chromadb.provider import ChromaDBVectorStore

from tests.helpers import create_test_code_object, create_test_relationship


class TestDeterministicIDs:
    """Test deterministic ID generation for CodeObjects and Relationships."""

    def test_code_object_same_id_for_same_content(self):
        """Same code object properties should generate same ID."""
        obj1 = create_test_code_object(
            name="MyClass", file_path="/test/file.py", start_line=10, end_line=20
        )
        obj2 = create_test_code_object(
            name="MyClass", file_path="/test/file.py", start_line=10, end_line=20
        )

        id1 = obj1.generate_deterministic_id()
        id2 = obj2.generate_deterministic_id()

        assert id1 == id2, "Same object should generate same ID"

    def test_code_object_different_id_for_different_location(self):
        """Different locations should generate different IDs."""
        obj1 = create_test_code_object(name="MyClass", start_line=10)
        obj2 = create_test_code_object(name="MyClass", start_line=20)

        id1 = obj1.generate_deterministic_id()
        id2 = obj2.generate_deterministic_id()

        assert id1 != id2, "Different locations should generate different IDs"

    def test_code_object_different_id_for_different_file(self):
        """Different files should generate different IDs."""
        obj1 = create_test_code_object(file_path="/test/file1.py")
        obj2 = create_test_code_object(file_path="/test/file2.py")

        id1 = obj1.generate_deterministic_id()
        id2 = obj2.generate_deterministic_id()

        assert id1 != id2, "Different files should generate different IDs"

    def test_relationship_same_id_for_same_pair(self):
        """Same relationship pair should generate same ID."""
        source_id = uuid4()
        target_id = uuid4()

        rel1 = create_test_relationship(source_id=str(source_id), target_id=str(target_id))
        rel2 = create_test_relationship(source_id=str(source_id), target_id=str(target_id))

        id1 = rel1.generate_deterministic_id()
        id2 = rel2.generate_deterministic_id()

        assert id1 == id2, "Same relationship should generate same ID"

    def test_id_length_is_32_chars(self):
        """Generated IDs should be 32 characters (truncated SHA256)."""
        obj = create_test_code_object()
        id_str = obj.generate_deterministic_id()

        assert len(id_str) == 32, f"ID length should be 32, got {len(id_str)}"

    def test_id_is_hexadecimal(self):
        """Generated IDs should be valid hexadecimal strings."""
        obj = create_test_code_object()
        id_str = obj.generate_deterministic_id()

        assert all(
            c in "0123456789abcdef" for c in id_str
        ), f"ID should be hexadecimal, got {id_str}"


class TestUpsertBehavior:
    """Test upsert behavior in ChromaDBVectorStore."""

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
        provider.collections["content"] = Mock()
        provider.collections["meta"] = Mock()

        # Initialize stores with mocked collections

        return provider

    @pytest.fixture
    def sample_object_with_embedding(self):
        """Create a sample object with embedding."""
        obj = create_test_code_object(
            name="TestMethod", file_path="/test/sample.py", object_type=ObjectType.METHOD
        )
        # Add dummy embedding (1024 dimensions for Qwen model)
        obj.embedding = [0.1] * 1024
        return obj

    def test_upsert_creates_new_object(
        self, chromadb_provider_with_mocks, sample_object_with_embedding
    ):
        """Upsert should create object if it doesn't exist."""
        obj = sample_object_with_embedding

        # Configure mocks
        chromadb_provider_with_mocks.collections["content"].upsert.return_value = None
        chromadb_provider_with_mocks.collections["content"].get.return_value = {
            "ids": [obj.generate_deterministic_id()],
            "metadatas": [obj.to_metadata()],
            "embeddings": [[0.1] * 1024],
            "documents": [obj.content],
        }

        # Add object
        chromadb_provider_with_mocks.add_code_objects([obj])

        # Verify upsert was called
        chromadb_provider_with_mocks.collections["content"].upsert.assert_called_once()

        # Verify it exists
        result = chromadb_provider_with_mocks.collections["content"].get(
            ids=[obj.generate_deterministic_id()]
        )

        assert len(result["ids"]) == 1
        assert result["metadatas"][0]["name"] == "TestMethod"

    def test_upsert_updates_existing_object(
        self, chromadb_provider_with_mocks, sample_object_with_embedding
    ):
        """Upsert should update object if it already exists."""
        obj1 = sample_object_with_embedding

        # Create updated version with same deterministic ID
        obj2 = create_test_code_object(
            name="TestMethod",
            file_path="/test/sample.py",
            object_type=ObjectType.METHOD,
            content="def test_method(): return 42  # Updated!",
        )
        obj2.embedding = [0.2] * 1024  # Different embedding

        # Configure mocks - first for obj1, then for obj2
        chromadb_provider_with_mocks.collections["content"].upsert.return_value = None
        chromadb_provider_with_mocks.collections["content"].count.return_value = 1
        chromadb_provider_with_mocks.collections["content"].get.return_value = {
            "ids": [obj2.generate_deterministic_id()],
            "metadatas": [obj2.to_metadata()],
            "embeddings": [[0.2] * 1024],
            "documents": ["def test_method(): return 42  # Updated!"],
        }

        # Add object first time
        chromadb_provider_with_mocks.add_code_objects([obj1])

        # Add again (should update)
        chromadb_provider_with_mocks.add_code_objects([obj2])

        # Verify only one object exists with updated content
        collection = chromadb_provider_with_mocks.collections["content"]
        assert collection.count() == 1

        result = collection.get(ids=[obj2.generate_deterministic_id()])
        assert "Updated!" in result["documents"][0]

    def test_multiple_upserts_no_duplicates(
        self, chromadb_provider_with_mocks, sample_object_with_embedding
    ):
        """Multiple upserts should not create duplicates."""
        obj = sample_object_with_embedding

        # Configure mock to always return count of 1 (no duplicates)
        chromadb_provider_with_mocks.collections["content"].upsert.return_value = None
        chromadb_provider_with_mocks.collections["content"].count.return_value = 1

        # Add same object 5 times
        for i in range(5):
            obj.embedding = [0.1 + i * 0.01] * 1024  # Slight variations
            chromadb_provider_with_mocks.add_code_objects([obj])

        # Should still have only 1 object
        collection = chromadb_provider_with_mocks.collections["content"]
        assert collection.count() == 1, "Multiple upserts should not create duplicates"

    def test_upsert_preserves_deterministic_id(self, chromadb_provider_with_mocks):
        """Upsert should use deterministic ID, not random UUID."""
        obj = create_test_code_object(name="MyClass", file_path="/test/file.py")
        obj.embedding = [0.1] * 1024

        expected_id = obj.generate_deterministic_id()

        # Configure mock to return the expected ID
        chromadb_provider_with_mocks.collections["content"].upsert.return_value = None
        chromadb_provider_with_mocks.collections["content"].get.return_value = {
            "ids": [expected_id],
            "metadatas": [obj.to_metadata()],
            "embeddings": [[0.1] * 1024],
            "documents": [obj.content],
        }

        # Add object
        chromadb_provider_with_mocks.add_code_objects([obj])

        # Verify ID matches deterministic ID
        collection = chromadb_provider_with_mocks.collections["content"]
        result = collection.get()

        assert len(result["ids"]) == 1
        assert result["ids"][0] == expected_id


class TestDeletion:
    """Test deletion functionality in ChromaDBVectorStore."""

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
        provider.collections["content"] = Mock()
        provider.collections["meta"] = Mock()

        # Initialize stores with mocked collections

        return provider

    def test_delete_by_file_path(self, chromadb_provider_with_mocks):
        """delete_code_objects_by_file() should remove all objects for a file."""
        # Create 3 objects from same file
        objects = [
            create_test_code_object(name=f"Class{i}", file_path="/test/file.py") for i in range(3)
        ]
        for obj in objects:
            obj.embedding = [0.1] * 1024

        # Configure mock to return 3 objects for the file
        chromadb_provider_with_mocks.collections["content"].get.return_value = {
            "ids": [obj.generate_deterministic_id() for obj in objects],
            "metadatas": [obj.to_metadata() for obj in objects],
        }
        chromadb_provider_with_mocks.collections["content"].delete.return_value = None

        # Mock count to return 3 before delete, 0 after
        chromadb_provider_with_mocks.collections["content"].count.side_effect = [3, 0]

        # Verify they exist
        assert chromadb_provider_with_mocks.collections["content"].count() == 3

        # Delete by file
        count = chromadb_provider_with_mocks.delete_code_objects_by_file("/test/file.py")

        # Verify deletion
        assert count == 3
        assert chromadb_provider_with_mocks.collections["content"].count() == 0

    def test_delete_by_file_path_returns_count(self, chromadb_provider_with_mocks):
        """delete_code_objects_by_file() should return number of deleted objects."""
        objects = [
            create_test_code_object(name=f"Method{i}", file_path="/test/service.py")
            for i in range(5)
        ]
        for obj in objects:
            obj.embedding = [0.1] * 1024

        # Configure mock to return 5 objects for the file
        chromadb_provider_with_mocks.collections["content"].get.return_value = {
            "ids": [obj.generate_deterministic_id() for obj in objects],
            "metadatas": [obj.to_metadata() for obj in objects],
        }
        chromadb_provider_with_mocks.collections["content"].delete.return_value = None

        count = chromadb_provider_with_mocks.delete_code_objects_by_file("/test/service.py")

        assert count == 5, f"Expected to delete 5 objects, deleted {count}"

    def test_delete_nonexistent_file_returns_zero(self, chromadb_provider_with_mocks):
        """Deleting non-existent file should return 0."""
        # Configure mock to return no objects
        chromadb_provider_with_mocks.collections["content"].get.return_value = {
            "ids": [],
            "metadatas": [],
        }

        count = chromadb_provider_with_mocks.delete_code_objects_by_file("/nonexistent/file.py")

        assert count == 0, "Deleting non-existent file should return 0"

    def test_delete_handles_relative_and_absolute_paths(self, chromadb_provider_with_mocks):
        """Deletion should work for both relative and absolute paths."""
        # Create object with relative path
        obj = create_test_code_object(file_path="test/file.py")
        obj.embedding = [0.1] * 1024

        # Configure mock to return 1 object with matching path
        chromadb_provider_with_mocks.collections["content"].get.return_value = {
            "ids": [obj.generate_deterministic_id()],
            "metadatas": [obj.to_metadata()],
        }
        chromadb_provider_with_mocks.collections["content"].delete.return_value = None

        # Delete with exact path match
        count = chromadb_provider_with_mocks.delete_code_objects_by_file("test/file.py")

        assert count == 1, "Should delete with matching path"
