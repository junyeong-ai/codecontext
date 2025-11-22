"""Parser interfaces following Interface Segregation Principle."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from codecontext_core.models import CodeObject, DocumentNode, Language
from tree_sitter import Node

from codecontext.indexer.ast_parser import TreeSitterParser


class Parser(ABC):
    """
    Base parser interface following ISP principle.

    All parsers must implement basic language detection and file support checks.
    """

    @abstractmethod
    def get_language(self) -> Language:
        """Get the language this parser handles."""
        ...

    @abstractmethod
    def supports_file(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        ...

    @abstractmethod
    def get_file_extensions(self) -> list[str]:
        """Get list[Any] of supported file extensions."""
        ...


class CodeParser(Parser):
    """
    Parser interface for source code files.

    Code parsers extract structured code objects (classes, functions, etc.)
    using tree-sitter AST parsing.
    """

    # Required attributes
    parser: TreeSitterParser
    language: Language

    @abstractmethod
    def extract_code_objects(self, file_path: Path, source: str) -> list[CodeObject]:
        """
        Extract code objects from source file.

        Args:
            file_path: Path to the source file
            source: Source code content

        Returns:
            List of extracted code objects with AST metadata
        """
        ...

    @abstractmethod
    def extract_relationships(
        self, file_path: Path, source: str, objects: list[CodeObject]
    ) -> list[tuple[str, str, str]]:
        """
        Extract relationships between code objects.

        Args:
            file_path: Path to the source file
            source: Source code content
            objects: Previously extracted code objects

        Returns:
            List of (source_id, target_id, relation_type) tuples
        """
        ...

    @abstractmethod
    def extract_ast_metadata(self, node: Node, source_bytes: bytes) -> dict[str, Any]:
        """
        Extract language-specific AST metadata.

        Args:
            node: Tree-sitter node
            source_bytes: Source code as bytes

        Returns:
            Dictionary containing AST metadata (complexity, depth, etc.)
        """
        ...


class DocumentParser(Parser):
    """
    Parser interface for documentation and configuration files.

    Document parsers extract structured documentation nodes and config metadata.
    """

    @abstractmethod
    def parse_file(self, file_path: Path) -> list[DocumentNode]:
        """
        Parse document file into structured nodes.

        Args:
            file_path: Path to the document file

        Returns:
            List of document nodes with metadata
        """
        ...

    @abstractmethod
    def extract_code_references(self, content: str) -> list[dict[str, Any]]:
        """
        Extract references to code from documentation.

        Args:
            content: Document content

        Returns:
            List of code references with context
        """
        ...

    @abstractmethod
    def chunk_document(
        self, content: str, max_chunk_size: int = 1500
    ) -> list[tuple[str, int, int]]:
        """
        Split large documents into chunks for embedding.

        Args:
            content: Document content
            max_chunk_size: Maximum characters per chunk

        Returns:
            List of (chunk_content, start_index, end_index) tuples
        """
        ...


class ConfigParser(DocumentParser):
    """
    Specialized parser for configuration files.

    Extends DocumentParser with config-specific extraction capabilities.
    """

    @abstractmethod
    def extract_config_keys(self, content: str) -> list[str]:
        """Extract configuration key paths."""
        ...

    @abstractmethod
    def extract_env_references(self, content: str) -> list[str]:
        """Extract environment variable references."""
        ...

    @abstractmethod
    def get_config_format(self) -> str:
        """Get configuration format (yaml/json/properties/ini)."""
        ...

    @abstractmethod
    def extract_dependencies(self, content: str) -> list[dict[str, Any]]:
        """
        Extract dependency information from config files.

        Returns:
            List of dependencies with versions and metadata
        """
        ...
