"""Common AST traversal and analysis utilities for all language parsers."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from tree_sitter import Node, Tree

from codecontext.indexer.ast_parser import TreeSitterParser


def extract_calls_generic(
    node: Node,
    source_code: bytes,
    parser: TreeSitterParser,
    call_node_types: list[str],
    get_function_name: Callable[[Node, bytes, TreeSitterParser], str | None],
) -> list[dict[str, Any]]:
    """Generic call extraction for any language.

    Args:
        node: AST node to analyze
        source_code: Source code bytes
        parser: Tree-sitter parser instance
        call_node_types: List of node types that represent calls (e.g., ["call", "call_expression"])
        get_function_name: Function to extract the called function name from a call node

    Returns:
        List of call dictionaries with name, line, and external flag
    """
    calls = []

    def traverse(n: Node) -> None:
        if n.type in call_node_types:
            name = get_function_name(n, source_code, parser)
            if name:
                line = n.start_point[0] + 1
                is_external = "." not in name
                calls.append({"name": name, "line": line, "external": is_external})

        for child in n.children:
            traverse(child)

    traverse(node)
    return calls


def extract_references_generic(
    node: Node,
    source_code: bytes,
    parser: TreeSitterParser,
    reference_node_types: list[str],
) -> list[dict[str, Any]]:
    """Generic reference extraction for any language.

    Args:
        node: AST node to analyze
        source_code: Source code bytes
        parser: Tree-sitter parser instance
        reference_node_types: List of node types that represent references
            (e.g., ["attribute", "member_expression"])

    Returns:
        List of reference dictionaries
    """
    references = []

    def traverse(n: Node) -> None:
        if n.type in reference_node_types:
            name = parser.get_node_text(n, source_code)
            line = n.start_point[0] + 1
            ref_type = "config" if "settings" in name or "config" in name else "attribute"
            references.append({"name": name, "line": line, "type": ref_type})

        for child in n.children:
            traverse(child)

    traverse(node)
    return references


def calculate_complexity_generic(
    node: Node,
    decision_node_types: list[str],
    nesting_node_types: list[str],
) -> dict[str, Any]:
    """Generic complexity calculation for any language.

    Args:
        node: AST node to analyze
        decision_node_types: Node types that represent decision points
        nesting_node_types: Node types that increase nesting depth

    Returns:
        Dictionary with cyclomatic complexity, lines, and nesting depth
    """
    decision_nodes = 0
    max_nesting = 0

    def traverse(n: Node, depth: int = 0) -> None:
        nonlocal decision_nodes, max_nesting

        if n.type in decision_node_types:
            decision_nodes += 1
            max_nesting = max(max_nesting, depth + 1)

        for child in n.children:
            new_depth = depth + 1 if n.type in nesting_node_types else depth
            traverse(child, new_depth)

    traverse(node)
    lines = node.end_point[0] - node.start_point[0] + 1

    return {
        "cyclomatic": 1 + decision_nodes,
        "lines": lines,
        "nesting_depth": max_nesting,
    }


def extract_single_class_with_methods(
    class_obj: Any,
    method_nodes: list[Any],
    extract_method_fn: Callable[..., Any],
    source_bytes: bytes,
    file_path: Path,
    relative_path: str,
) -> list[Any]:
    """Extract a single class and its methods (traditional extraction).

    This helper function extracts a class object and all its method objects,
    used by language parsers when chunking is disabled.

    Args:
        class_obj: Already extracted class CodeObject (or None)
        method_nodes: List of method AST nodes
        extract_method_fn: Function to extract a single method
        source_bytes: Source code bytes
        file_path: File path
        relative_path: Relative file path

    Returns:
        List of code objects (class + methods)
    """
    objects = []

    if class_obj:
        objects.append(class_obj)

        # Extract methods within the class
        for method_node in method_nodes:
            method_obj = extract_method_fn(
                method_node,
                source_bytes,
                file_path,
                relative_path,
                class_obj.deterministic_id,
            )
            if method_obj:
                objects.append(method_obj)

    return objects


def extract_class_with_methods(
    tree: Tree,
    source_bytes: bytes,
    file_path: Path,
    relative_path: str,
    parser: TreeSitterParser,
    class_node_type: str,
    extract_class_fn: Callable[..., Any],
    get_methods_fn: Callable[..., Any],
    extract_method_fn: Callable[..., Any],
) -> list[Any]:
    """Generic class extraction with nested methods for OOP languages.

    Args:
        tree: Parse tree
        source_bytes: Source code bytes
        file_path: File path
        relative_path: Relative file path
        parser: Tree-sitter parser
        class_node_type: Node type for class declarations
        extract_class_fn: Function to extract a single class
        get_methods_fn: Function to get method nodes from a class
        extract_method_fn: Function to extract a single method

    Returns:
        List of code objects (classes and methods)
    """
    objects = []

    class_nodes = parser.traverse_tree(tree, [class_node_type])
    for class_node in class_nodes:
        class_obj = extract_class_fn(class_node, source_bytes, file_path, relative_path)

        # Use helper function for traditional extraction
        method_nodes = get_methods_fn(class_node)
        objects.extend(
            extract_single_class_with_methods(
                class_obj, method_nodes, extract_method_fn, source_bytes, file_path, relative_path
            )
        )

    return objects
