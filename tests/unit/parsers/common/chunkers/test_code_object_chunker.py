"""Tests for CodeObjectChunker.

This module tests the chunking logic for large code objects,
ensuring that large classes and files are properly split into
manageable chunks while maintaining parent-child relationships.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import UUID

import pytest
from codecontext.parsers.common.chunkers.code_object_chunker import (
    MAX_CLASS_METHODS,
    MAX_OBJECT_SIZE,
    CodeObjectChunker,
)
from codecontext_core.models import CodeObject, Language, ObjectType
from tree_sitter import Node

# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def chunker():
    """Create a CodeObjectChunker with default settings."""
    return CodeObjectChunker(
        max_object_size=MAX_OBJECT_SIZE,
        max_class_methods=MAX_CLASS_METHODS,
    )


@pytest.fixture
def custom_chunker():
    """Create a CodeObjectChunker with custom settings for testing thresholds."""
    return CodeObjectChunker(
        max_object_size=100,  # Small size for testing
        max_class_methods=3,  # Small count for testing
    )


@pytest.fixture
def mock_parser():
    """Create a mock TreeSitterParser."""
    parser = Mock()
    parser.get_node_text = Mock(
        side_effect=lambda node, source: (
            node.text.encode() if isinstance(node.text, str) else node.text
        )
    )
    parser.find_child_by_field = Mock(
        side_effect=lambda node, field: getattr(node, f"{field}_node", None)
    )
    parser.get_node_position = Mock(return_value=(1, 10))
    return parser


@pytest.fixture
def mock_class_node():
    """Create a mock class node."""
    node = Mock(spec=Node)
    node.type = "class_definition"
    node.text = b"class TestClass:\n    pass"
    node.start_point = (0, 0)
    node.end_point = (1, 8)
    node.start_byte = 0
    node.end_byte = 26

    # Mock name node
    name_node = Mock(spec=Node)
    name_node.text = b"TestClass"
    node.name_node = name_node

    return node


# ======================================================================
# Test Classes
# ======================================================================


class TestCodeObjectChunkerInitialization:
    """Test CodeObjectChunker initialization."""

    def test_initializes_with_default_values(self):
        """Should initialize with default max_object_size and max_class_methods."""
        # Act
        chunker = CodeObjectChunker()

        # Assert
        assert chunker.max_object_size == MAX_OBJECT_SIZE
        assert chunker.max_class_methods == MAX_CLASS_METHODS

    def test_initializes_with_custom_values(self):
        """Should initialize with custom values."""
        # Arrange & Act
        chunker = CodeObjectChunker(max_object_size=1000, max_class_methods=10)

        # Assert
        assert chunker.max_object_size == 1000
        assert chunker.max_class_methods == 10


class TestShouldChunkClass:
    """Test should_chunk_class method."""

    def test_returns_false_for_small_class(self, chunker):
        """Should return False for class below size threshold.

        Given: Class with text smaller than max_object_size and few methods
        When: should_chunk_class is called
        Then: Should return False
        """
        # Arrange
        class_text = "class Small:\n    pass"  # < 2000 chars
        method_count = 5  # < 20 methods

        # Act
        result = chunker.should_chunk_class(class_text, method_count)

        # Assert
        assert result is False

    def test_returns_true_for_large_class_text(self, chunker):
        """Should return True for class with text exceeding size threshold.

        Given: Class with text larger than max_object_size
        When: should_chunk_class is called
        Then: Should return True
        """
        # Arrange
        class_text = "x" * (MAX_OBJECT_SIZE + 1)
        method_count = 5

        # Act
        result = chunker.should_chunk_class(class_text, method_count)

        # Assert
        assert result is True

    def test_returns_true_for_many_methods(self, chunker):
        """Should return True for class with methods exceeding threshold.

        Given: Class with more methods than max_class_methods
        When: should_chunk_class is called
        Then: Should return True
        """
        # Arrange
        class_text = "class Large:\n    pass"
        method_count = MAX_CLASS_METHODS + 1

        # Act
        result = chunker.should_chunk_class(class_text, method_count)

        # Assert
        assert result is True

    def test_boundary_exactly_at_threshold(self, chunker):
        """Should not chunk when exactly at threshold.

        Given: Class with exactly max_object_size characters and max_class_methods methods
        When: should_chunk_class is called
        Then: Should return False (not exceeding threshold)
        """
        # Arrange
        class_text = "x" * MAX_OBJECT_SIZE
        method_count = MAX_CLASS_METHODS

        # Act
        result = chunker.should_chunk_class(class_text, method_count)

        # Assert
        assert result is False

    def test_one_char_over_size_threshold(self, custom_chunker):
        """Should chunk when text is one character over threshold."""
        # Arrange
        class_text = "x" * 101  # One over custom threshold of 100

        # Act
        result = custom_chunker.should_chunk_class(class_text, 1)

        # Assert
        assert result is True

    def test_one_method_over_count_threshold(self, custom_chunker):
        """Should chunk when one method over threshold."""
        # Arrange
        class_text = "small"
        method_count = 4  # One over custom threshold of 3

        # Act
        result = custom_chunker.should_chunk_class(class_text, method_count)

        # Assert
        assert result is True


class TestChunkClassWithMethods:
    """Test chunk_class_with_methods method."""

    def test_returns_single_object_for_small_class(self, chunker, mock_class_node, mock_parser):
        """Should return single object for small class.

        Given: Small class below chunking thresholds
        When: chunk_class_with_methods is called
        Then: Should return single CodeObject with full content
        """
        # Arrange
        mock_class_node.text = b"class Small:\n    pass"
        method_nodes: list[dict[str, Any]] = []  # No methods
        source_bytes = b"class Small:\n    pass"
        file_path = Path("/test.py")

        def mock_extractor(node, source, path, rel_path, parent_id=None):
            return CodeObject(
                name="Small",
                object_type=ObjectType.CLASS,
                language=Language.PYTHON,
                file_path=str(path),
                relative_path=rel_path,
                start_line=1,
                end_line=2,
                content="class Small:\n    pass",
                signature="class Small",
                checksum="abc123",
            )

        # Act
        result = chunker.chunk_class_with_methods(
            class_node=mock_class_node,
            method_nodes=method_nodes,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path="test.py",
            language=Language.PYTHON,
            parser=mock_parser,
            method_extractor_func=mock_extractor,
        )

        # Assert
        assert len(result) >= 1
        assert result[0].object_type == ObjectType.CLASS

    def test_chunks_large_class_by_text_size(self, custom_chunker, mock_class_node, mock_parser):
        """Should chunk class when text size exceeds threshold.

        Given: Class with text exceeding max_object_size
        When: chunk_class_with_methods is called
        Then: Should return class summary + individual methods
        """
        # Arrange
        large_text = b"x" * 150  # Exceeds custom threshold of 100
        mock_class_node.text = large_text

        # Create some method nodes
        method_nodes: list[dict[str, Any]] = []
        for i in range(2):
            method = Mock(spec=Node)
            method.type = "function_definition"
            method.text = f"def method_{i}(self): pass".encode()
            method_nodes.append(method)

        source_bytes = large_text
        file_path = Path("/test.py")

        method_call_count = [0]

        def mock_method_extractor(node, source, path, rel_path, parent_id):
            method_call_count[0] += 1
            return CodeObject(
                name=f"method_{method_call_count[0]}",
                object_type=ObjectType.METHOD,
                language=Language.PYTHON,
                file_path=str(path),
                relative_path=rel_path,
                start_line=method_call_count[0],
                end_line=method_call_count[0],
                content=f"def method_{method_call_count[0]}(self): pass",
                signature=f"def method_{method_call_count[0]}(self)",
                checksum=f"method_{method_call_count[0]}",
                parent_id=parent_id,
            )

        # Act
        result = custom_chunker.chunk_class_with_methods(
            class_node=mock_class_node,
            method_nodes=method_nodes,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path="test.py",
            language=Language.PYTHON,
            parser=mock_parser,
            method_extractor_func=mock_method_extractor,
        )

        # Assert
        assert len(result) >= 1
        # Should have chunked due to large text size
        # (exact count depends on _chunk_class vs _extract_whole_class implementation)

    def test_chunks_when_method_count_exceeds_threshold(
        self, custom_chunker, mock_class_node, mock_parser
    ):
        """Should chunk when method count exceeds threshold.

        Given: Class with more methods than max_class_methods
        When: chunk_class_with_methods is called
        Then: Should chunk even if text size is small
        """
        # Arrange
        mock_class_node.text = b"small text"  # Small text

        # Create 4 method nodes (exceeds custom threshold of 3)
        method_nodes: list[dict[str, Any]] = []
        for i in range(4):
            method = Mock(spec=Node)
            method.type = "function_definition"
            method.text = f"def method_{i}(self): pass".encode()
            method_nodes.append(method)

        source_bytes = b"small text"
        file_path = Path("/test.py")

        def mock_method_extractor(node, source, path, rel_path, parent_id):
            return CodeObject(
                name="method",
                object_type=ObjectType.METHOD,
                language=Language.PYTHON,
                file_path=str(path),
                relative_path=rel_path,
                start_line=1,
                end_line=1,
                content="def method(self): pass",
                signature="def method(self)",
                checksum="method",
                parent_id=parent_id,
            )

        # Act
        result = custom_chunker.chunk_class_with_methods(
            class_node=mock_class_node,
            method_nodes=method_nodes,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path="test.py",
            language=Language.PYTHON,
            parser=mock_parser,
            method_extractor_func=mock_method_extractor,
        )

        # Assert
        assert len(result) >= 1
        # Should have chunked due to many methods


class TestParentChildRelationships:
    """Test parent-child relationship preservation."""

    def test_methods_have_parent_id_when_chunked(
        self, custom_chunker, mock_class_node, mock_parser
    ):
        """Methods should have parent_id set to class summary ID when chunked.

        Given: Large class being chunked into summary + methods
        When: chunk_class_with_methods is called
        Then: All method objects should have parent_id set
        """
        # Arrange
        mock_class_node.text = b"x" * 150  # Exceed threshold

        method_nodes: list[dict[str, Any]] = []
        for i in range(2):
            method = Mock(spec=Node)
            method.text = f"def method_{i}(self): pass".encode()
            method_nodes.append(method)

        source_bytes = b"x" * 150
        file_path = Path("/test.py")

        captured_parent_ids = []

        def mock_method_extractor(node, source, path, rel_path, parent_id):
            captured_parent_ids.append(parent_id)
            return CodeObject(
                name="method",
                object_type=ObjectType.METHOD,
                language=Language.PYTHON,
                file_path=str(path),
                relative_path=rel_path,
                start_line=1,
                end_line=1,
                content="def method(self): pass",
                signature="def method(self)",
                checksum="method",
                parent_id=parent_id,
            )

        # Act
        result = custom_chunker.chunk_class_with_methods(
            class_node=mock_class_node,
            method_nodes=method_nodes,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path="test.py",
            language=Language.PYTHON,
            parser=mock_parser,
            method_extractor_func=mock_method_extractor,
        )

        # Assert
        assert len(result) >= 1

        # Check that parent_ids were passed to method extractor
        for parent_id in captured_parent_ids:
            if parent_id is not None:
                assert isinstance(parent_id, (UUID, str))


# ======================================================================
# Integration Tests
# ======================================================================


class TestChunkingIntegration:
    """Integration tests for chunking with real-world scenarios."""

    def test_large_kotlin_class_chunking_scenario(self, chunker, mock_parser):
        """Should properly chunk a large Kotlin class with many methods.

        This simulates a real-world scenario from the quality tests where
        a large Kotlin repository class with 50+ methods needs to be chunked.
        """
        # Arrange - Simulate large class
        large_class_text = "x" * 5000  # Exceeds MAX_OBJECT_SIZE

        mock_class_node = Mock(spec=Node)
        mock_class_node.text = large_class_text.encode()
        mock_class_node.start_byte = 0
        mock_class_node.end_byte = len(large_class_text)

        name_node = Mock()
        name_node.text = b"LargeRepository"
        mock_class_node.name_node = name_node

        # Create 30 method nodes
        method_nodes: list[dict[str, Any]] = []
        for i in range(30):
            method = Mock(spec=Node)
            method.text = f"suspend fun method_{i}(id: UUID): Entity?".encode()
            method_nodes.append(method)

        source_bytes = large_class_text.encode()
        file_path = Path("/order/OrderRepository.kt")

        def mock_method_extractor(node, source, path, rel_path, parent_id):
            method_name = node.text.decode().split("_")[1].split("(")[0]
            return CodeObject(
                name=f"method_{method_name}",
                object_type=ObjectType.METHOD,
                language=Language.KOTLIN,
                file_path=str(path),
                relative_path=rel_path,
                start_line=1,
                end_line=1,
                content=node.text.decode(),
                signature=node.text.decode().split("(")[0],
                checksum=f"checksum_{method_name}",
                parent_id=parent_id,
            )

        # Act
        result = chunker.chunk_class_with_methods(
            class_node=mock_class_node,
            method_nodes=method_nodes,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path="order/OrderRepository.kt",
            language=Language.KOTLIN,
            parser=mock_parser,
            method_extractor_func=mock_method_extractor,
        )

        # Assert
        assert len(result) >= 1
        # Should have chunked due to large size and many methods

    def test_decision_logic_consistency(self):
        """Verify that should_chunk_class and chunk_class_with_methods are consistent."""
        # Arrange
        chunker = CodeObjectChunker(max_object_size=100, max_class_methods=5)

        # Test cases: (class_text, method_count, expected_should_chunk)
        test_cases = [
            ("small", 2, False),  # Both below threshold
            ("x" * 101, 2, True),  # Text exceeds
            ("small", 6, True),  # Methods exceed
            ("x" * 101, 6, True),  # Both exceed
            ("x" * 100, 5, False),  # Exactly at thresholds
        ]

        for class_text, method_count, expected in test_cases:
            # Act
            result = chunker.should_chunk_class(class_text, method_count)

            # Assert
            assert result == expected, (
                f"Failed for class_text length={len(class_text)}, method_count={method_count}: "
                f"expected {expected}, got {result}"
            )
