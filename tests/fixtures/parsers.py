"""Parser-related test fixtures.

Provides reusable fixtures for BaseCodeParser testing,
reducing boilerplate in parser unit tests.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from codecontext.indexer.ast_parser import TreeSitterParser
from codecontext.parsers.base import BaseCodeParser
from codecontext_core.models import CodeObject, Language
from tree_sitter import Node


@pytest.fixture
def mock_tree_sitter_parser():
    """Create a mock TreeSitterParser.

    Returns:
        Mock TreeSitterParser with find_child_by_field method
    """
    parser = Mock(spec=TreeSitterParser)
    parser.find_child_by_field = Mock(return_value=None)
    return parser


@pytest.fixture
def mock_node():
    """Create a mock Tree-sitter Node.

    Returns:
        Mock Node with common attributes
    """
    node = Mock(spec=Node)
    node.type = "function_definition"
    node.parent = None
    node.children = []
    node.start_point = (0, 0)
    node.end_point = (10, 0)
    return node


@pytest.fixture
def base_parser_with_ast_metadata(mock_tree_sitter_parser):
    """Create a concrete BaseCodeParser implementation with ast_metadata support.

    Args:
        mock_tree_sitter_parser: Mock TreeSitterParser fixture

    Returns:
        TestParser instance that implements all abstract methods
    """

    class TestParser(BaseCodeParser):
        """Concrete parser for testing."""

        def _extract_classes(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            """Stub implementation."""
            return []

        def _extract_interfaces(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            """Stub implementation."""
            return []

        def _extract_functions(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            """Stub implementation."""
            return []

        def _extract_enums(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            """Stub implementation."""
            return []

        def extract_ast_metadata(self, node: Node, source_bytes: bytes) -> dict[str, Any]:
            """Stub implementation for testing."""
            return {"complexity": 1, "calls": [], "references": []}

        def get_file_extensions(self) -> list[str]:
            """Return supported file extensions."""
            return [".py"]

    return TestParser(Language.PYTHON, mock_tree_sitter_parser)


@pytest.fixture
def concrete_parser(mock_tree_sitter_parser):
    """Create a minimal concrete BaseCodeParser for basic testing.

    Args:
        mock_tree_sitter_parser: Mock TreeSitterParser fixture

    Returns:
        Simple TestParser instance
    """

    class TestParser(BaseCodeParser):
        """Minimal concrete parser for testing."""

        def _extract_classes(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            return []

        def _extract_interfaces(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            return []

        def _extract_functions(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            return []

        def _extract_enums(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            return []

        def extract_ast_metadata(self, node: Node, source_bytes: bytes) -> dict[str, Any]:
            return {}

        def get_file_extensions(self) -> list[str]:
            """Return supported file extensions."""
            return [".py"]

    return TestParser(Language.PYTHON, mock_tree_sitter_parser)


def create_test_parser_for_language(language: Language, mock_parser: Mock) -> BaseCodeParser:
    """Factory function to create parser for specific language.

    Args:
        language: Language enum value
        mock_parser: Mock TreeSitterParser instance

    Returns:
        BaseCodeParser implementation for the language

    Example:
        >>> mock = Mock(spec=TreeSitterParser)
        >>> parser = create_test_parser_for_language(Language.JAVA, mock)
        >>> assert parser.get_language() == Language.JAVA
    """

    class TestLanguageParser(BaseCodeParser):
        def _extract_classes(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            return []

        def _extract_interfaces(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            return []

        def _extract_functions(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            return []

        def _extract_enums(
            self, tree, source_bytes: bytes, file_path: Path, relative_path: str
        ) -> list[CodeObject]:
            return []

        def extract_ast_metadata(self, node: Node, source_bytes: bytes) -> dict[str, Any]:
            return {}

        def get_file_extensions(self) -> list[str]:
            """Return supported file extensions."""
            return [".py"]

    return TestLanguageParser(language, mock_parser)


__all__ = [
    "base_parser_with_ast_metadata",
    "concrete_parser",
    "create_test_parser_for_language",
    "mock_node",
    "mock_tree_sitter_parser",
]
