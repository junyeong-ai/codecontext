"""Common extraction functions for parsing code objects."""

from pathlib import Path
from typing import Any
from uuid import UUID

from tree_sitter import Node

from codecontext_core.models import CodeObject, Language, ObjectType
from codecontext.indexer.ast_parser import TreeSitterParser
from codecontext.utils.checksum import ChecksumCalculator


def extract_code_object(
    node: Node,
    source_bytes: bytes,
    file_path: Path,
    relative_path: str,
    object_type: ObjectType,
    language: Language,
    signature: str,
    parser: TreeSitterParser,
    parent_id: UUID | None = None,
    docstring: str | None = None,
    nl_description: str | None = None,
) -> CodeObject:
    """
    Extract a code object from a tree-sitter node.

    This is the common extraction logic used by all language parsers.

    Args:
        node: Tree-sitter node to extract
        source_bytes: Source code as bytes
        file_path: Absolute file path
        relative_path: Relative file path
        object_type: Type of code object (CLASS, METHOD, etc.)
        language: Programming language
        signature: Code signature (e.g., "def foo(x, y)")
        parser: Tree-sitter parser instance
        parent_id: Optional parent object ID
        docstring: Optional docstring/comment
        nl_description: Optional natural language description

    Returns:
        CodeObject instance
    """
    content = parser.get_node_text(node, source_bytes)
    start_line, end_line = parser.get_node_position(node)
    content_str = content if isinstance(content, str) else content.decode("utf-8", errors="ignore")
    checksum = ChecksumCalculator.calculate_content_checksum(content_str)

    return CodeObject(
        file_path=str(file_path),
        relative_path=relative_path,
        object_type=object_type,
        name="",
        language=language,
        start_line=start_line,
        end_line=end_line,
        content=content,
        signature=signature,
        docstring=docstring,
        nl_description=nl_description,
        checksum=checksum,
        parent_id=parent_id,
    )


def extract_name_and_build_object(
    node: Node,
    source_bytes: bytes,
    file_path: Path,
    relative_path: str,
    object_type: ObjectType,
    language: Language,
    signature: str,
    name: str,
    parser: TreeSitterParser,
    parent_id: UUID | None = None,
    language_parser: Any | None = None,
    docstring: str | None = None,
    nl_description: str | None = None,
) -> CodeObject:
    """
    Extract a complete code object with name.

    Args:
        node: Tree-sitter node to extract
        source_bytes: Source code as bytes
        file_path: Absolute file path
        relative_path: Relative file path
        object_type: Type of code object
        language: Programming language
        signature: Code signature
        name: Object name (already extracted)
        parser: Tree-sitter parser instance
        parent_id: Optional parent object ID
        language_parser: Language-specific parser for AST metadata extraction
        docstring: Optional docstring/comment
        nl_description: Optional natural language description

    Returns:
        CodeObject instance
    """
    obj = extract_code_object(
        node=node,
        source_bytes=source_bytes,
        file_path=file_path,
        relative_path=relative_path,
        object_type=object_type,
        language=language,
        signature=signature,
        parser=parser,
        parent_id=parent_id,
        docstring=docstring,
        nl_description=nl_description,
    )
    object.__setattr__(obj, "name", name)

    return obj
