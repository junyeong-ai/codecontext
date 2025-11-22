"""Parser utility functions (not pytest fixtures).

This module contains helper functions for creating test parsers.
It is separate from parsers.py to avoid pytest assertion rewrite warnings.

parsers.py contains pytest fixtures and is registered via pytest_plugins.
parser_helpers.py contains utility functions and can be safely imported.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

from codecontext.parsers.base import BaseCodeParser
from codecontext_core.models import CodeObject, Language
from tree_sitter import Node


def create_test_parser_for_language(language: Language, mock_parser: Mock) -> BaseCodeParser:
    """Factory function to create parser for specific language.

    Args:
        language: Language enum value
        mock_parser: Mock TreeSitterParser instance

    Returns:
        BaseCodeParser implementation for the language

    Example:
        >>> from unittest.mock import Mock
        >>> from codecontext.indexer.ast_parser import TreeSitterParser
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
