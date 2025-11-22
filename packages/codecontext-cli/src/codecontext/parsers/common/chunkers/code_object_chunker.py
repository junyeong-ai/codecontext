"""Code object chunking strategy for large files and classes."""

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from codecontext_core.models import CodeObject, Language, ObjectType
from tree_sitter import Node

from codecontext.indexer.ast_parser import TreeSitterParser
from codecontext.parsers.common.extractors import extract_name_and_build_object

if TYPE_CHECKING:
    from codecontext.parsers.base import BaseCodeParser

# Configuration constants
MAX_OBJECT_SIZE = 2000  # Maximum characters per code object
MAX_CLASS_METHODS = 20  # Maximum methods before splitting class


class CodeObjectChunker:
    """Chunk large code objects into smaller, manageable pieces."""

    def __init__(
        self,
        max_object_size: int = MAX_OBJECT_SIZE,
        max_class_methods: int = MAX_CLASS_METHODS,
    ) -> None:
        """
        Initialize chunker with size limits.

        Args:
            max_object_size: Maximum characters per object
            max_class_methods: Maximum methods before splitting
        """
        self.max_object_size = max_object_size
        self.max_class_methods = max_class_methods

    def should_chunk_class(self, class_text: str, method_count: int) -> bool:
        """
        Determine if a class should be chunked based on size and method count.

        A class should be chunked if:
        1. Text size exceeds max_object_size, OR
        2. Method count exceeds max_class_methods

        Args:
            class_text: Full text content of the class
            method_count: Number of methods in the class

        Returns:
            True if class should be chunked, False otherwise

        Examples:
            >>> chunker = CodeObjectChunker(max_object_size=100, max_class_methods=5)
            >>> chunker.should_chunk_class("x" * 50, 3)  # Small class
            False
            >>> chunker.should_chunk_class("x" * 150, 3)  # Large text
            True
            >>> chunker.should_chunk_class("x" * 50, 10)  # Many methods
            True
        """
        return len(class_text) > self.max_object_size or method_count > self.max_class_methods

    def chunk_class_with_methods(
        self,
        class_node: Node,
        method_nodes: list[Node],
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
        language: Language,
        parser: TreeSitterParser,
        method_extractor_func: Callable[
            [Node, bytes, Path, str, UUID | str | None], CodeObject | None
        ],
        language_parser: "BaseCodeParser | None" = None,
    ) -> list[CodeObject]:
        """
        Chunk a large class into class summary + individual methods.

        If a class has many methods or is very large, split it into:
        1. Class summary (signature + docstring, no method bodies)
        2. Individual method objects (each as separate code object)

        Args:
            class_node: AST node for the class
            method_nodes: List of method nodes within the class
            source_bytes: Source code bytes
            file_path: File path
            relative_path: Relative file path
            language: Programming language
            parser: TreeSitterParser instance
            method_extractor_func: Function to extract individual methods
            language_parser: Optional language parser instance for name extraction

        Returns:
            List of code objects (class summary + methods if chunked, or single class if not)
        """
        # Get class text
        class_text = parser.get_node_text(class_node, source_bytes)

        # Check if chunking needed using dedicated method
        if not self.should_chunk_class(class_text, len(method_nodes)):
            # Return single class object with all content
            return self._extract_whole_class(
                class_node,
                source_bytes,
                file_path,
                relative_path,
                language,
                parser,
                method_extractor_func,
                method_nodes,
                language_parser,
            )

        # Chunk: Create class summary + individual methods
        return self._chunk_class(
            class_node,
            method_nodes,
            source_bytes,
            file_path,
            relative_path,
            language,
            parser,
            method_extractor_func,
            language_parser,
        )

    def _extract_whole_class(
        self,
        class_node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
        language: Language,
        parser: TreeSitterParser,
        method_extractor_func: Callable[
            [Node, bytes, Path, str, UUID | str | None], CodeObject | None
        ],
        method_nodes: list[Node],
        language_parser: "BaseCodeParser | None" = None,
    ) -> list[CodeObject]:
        """Extract class as single object with nested methods."""
        # Extract class name using language-specific method if available
        if language_parser and hasattr(language_parser, "_get_name_node"):
            name_node = language_parser._get_name_node(class_node)
        else:
            # Fallback: try Java-style field lookup
            name_node = parser.find_child_by_field(class_node, "name")

        if not name_node:
            return []

        class_name = parser.get_node_text(name_node, source_bytes)

        # Extract docstring using language parser
        docstring = None
        if language_parser and hasattr(language_parser, "_extract_javadoc"):
            docstring = language_parser._extract_javadoc(class_node, source_bytes)

        # Create class object
        class_obj = extract_name_and_build_object(
            node=class_node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.CLASS,
            language=language,
            signature=self._extract_class_signature(class_node, source_bytes, parser),
            name=class_name,
            parser=parser,
            docstring=docstring,
        )

        # Extract methods as children
        methods = []
        for method_node in method_nodes:
            method_obj = method_extractor_func(
                method_node,
                source_bytes,
                file_path,
                relative_path,
                class_obj.deterministic_id,
            )
            if method_obj:
                methods.append(method_obj)

        return [class_obj, *methods]

    def _chunk_class(
        self,
        class_node: Node,
        method_nodes: list[Node],
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
        language: Language,
        parser: TreeSitterParser,
        method_extractor_func: Callable[
            [Node, bytes, Path, str, UUID | str | None], CodeObject | None
        ],
        language_parser: "BaseCodeParser | None" = None,
    ) -> list[CodeObject]:
        """Chunk class into summary + individual methods.

        Creates:
        1. Class summary (signature, docstring, fields - without method bodies)
        2. Each method as separate object
        """
        # Extract class name using language-specific method if available
        if language_parser and hasattr(language_parser, "_get_name_node"):
            name_node = language_parser._get_name_node(class_node)
        else:
            # Fallback: try Java-style field lookup
            name_node = parser.find_child_by_field(class_node, "name")

        if not name_node:
            return []

        class_name = parser.get_node_text(name_node, source_bytes)

        # Create class summary object
        class_summary = self._create_class_summary(
            class_node,
            source_bytes,
            file_path,
            relative_path,
            language,
            parser,
            class_name,
            language_parser,
        )

        # Extract each method as separate object
        methods = []
        for method_node in method_nodes:
            method_obj = method_extractor_func(
                method_node,
                source_bytes,
                file_path,
                relative_path,
                class_summary.deterministic_id,
            )
            if method_obj:
                methods.append(method_obj)

        return [class_summary, *methods]

    def _create_class_summary(
        self,
        class_node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
        language: Language,
        parser: TreeSitterParser,
        class_name: str,
        language_parser: "BaseCodeParser | None" = None,
    ) -> CodeObject:
        """Create class summary without method bodies.

        Includes:
        - Class signature
        - Docstring/comments
        - Field declarations
        - Method signatures (without bodies)
        """
        signature = self._extract_class_signature(class_node, source_bytes, parser)
        summary_content = self._extract_class_summary_content(class_node, source_bytes, parser)

        # Extract docstring using language parser
        docstring = None
        if language_parser and hasattr(language_parser, "_extract_javadoc"):
            docstring = language_parser._extract_javadoc(class_node, source_bytes)

        start_line, end_line = parser.get_node_position(class_node)

        from codecontext.utils.checksum import ChecksumCalculator

        checksum = ChecksumCalculator.calculate_content_checksum(summary_content)

        return CodeObject(
            file_path=str(file_path),
            relative_path=relative_path,
            name=class_name,
            object_type=ObjectType.CLASS,
            content=summary_content,
            language=language,
            signature=signature,
            docstring=docstring,
            start_line=start_line,
            end_line=end_line,
            checksum=checksum,
            ast_metadata={
                "is_summary": True,
                "has_chunked_methods": True,
            },
        )

    def _extract_class_signature(
        self, class_node: Node, source_bytes: bytes, _parser: TreeSitterParser
    ) -> str:
        """
        Extract class signature (declaration line).

        Example: "class OrderService(BaseService):"
        """
        # For most languages, first line is the signature
        first_line_end = class_node.start_byte
        for i, byte in enumerate(source_bytes[class_node.start_byte :]):
            if byte == ord("\n"):
                first_line_end = class_node.start_byte + i
                break

        signature_bytes = source_bytes[class_node.start_byte : first_line_end]
        return signature_bytes.decode("utf8").strip()

    def _extract_class_summary_content(
        self, class_node: Node, source_bytes: bytes, parser: TreeSitterParser
    ) -> str:
        """
        Extract class content without method bodies.

        Includes:
        - Class declaration
        - Docstring
        - Fields
        - Method signatures only
        """
        # Get body node
        body_node = parser.find_child_by_field(class_node, "body") or parser.find_child_by_field(
            class_node, "class_body"
        )

        if not body_node:
            # No body, return whole class
            return str(parser.get_node_text(class_node, source_bytes))

        # Extract parts
        parts = []

        # Add class signature
        parts.append(self._extract_class_signature(class_node, source_bytes, parser))

        # Add docstring if present
        docstring = self._extract_docstring(body_node, source_bytes, parser)
        if docstring:
            parts.append(docstring)

        # Add field declarations
        fields = self._extract_fields(body_node, source_bytes, parser)
        if fields:
            parts.extend(fields)

        # Add method signatures (without bodies)
        method_signatures = self._extract_method_signatures(body_node, source_bytes, parser)
        if method_signatures:
            parts.extend(method_signatures)

        return "\n\n".join(parts)

    def _extract_docstring(
        self, body_node: Node, source_bytes: bytes, parser: TreeSitterParser
    ) -> str | None:
        """Extract class docstring if present."""
        # Look for first string/comment node
        for child in body_node.children:
            if child.type in [
                "string",
                "string_literal",
                "comment",
                "block_comment",
                "line_comment",
            ]:
                return str(parser.get_node_text(child, source_bytes))
        return None

    def _extract_fields(
        self, body_node: Node, source_bytes: bytes, parser: TreeSitterParser
    ) -> list[str]:
        """Extract field declarations from class body."""
        fields = []
        for child in body_node.children:
            if child.type in [
                "field_declaration",
                "property_declaration",
                "assignment",
            ]:
                fields.append(parser.get_node_text(child, source_bytes))
        return fields

    def _extract_method_signatures(
        self, body_node: Node, source_bytes: bytes, _parser: TreeSitterParser
    ) -> list[str]:
        """Extract method signatures without bodies."""
        signatures = []
        for child in body_node.children:
            if child.type in [
                "function_definition",
                "function_declaration",
                "method_declaration",
            ]:
                # Extract just the signature line
                signature = self._extract_function_signature(child, source_bytes)
                signatures.append(signature)
        return signatures

    def _extract_function_signature(self, func_node: Node, source_bytes: bytes) -> str:
        """Extract function/method signature (declaration line only)."""
        # Find first line (up to opening brace or colon)
        start = func_node.start_byte
        end = func_node.start_byte

        for i, byte in enumerate(source_bytes[start:]):
            char = chr(byte)
            if char in ["{", ":", "\n"]:
                end = start + i
                break

        signature_bytes = source_bytes[start:end]
        return signature_bytes.decode("utf8").strip()
