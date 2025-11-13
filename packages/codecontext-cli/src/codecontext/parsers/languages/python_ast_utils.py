"""Python-specific AST utilities and helpers."""

from typing import Any
from tree_sitter import Node

from codecontext.indexer.ast_parser import TreeSitterParser
from codecontext.parsers.common.utilities.ast_common import calculate_complexity_generic


def is_enum_class(class_node: Node, source_bytes: bytes, parser: TreeSitterParser) -> bool:
    """Check if a class inherits from Enum.

    Args:
        class_node: Class definition node
        source_bytes: Source code bytes
        parser: Tree-sitter parser instance

    Returns:
        True if class inherits from Enum
    """
    superclasses_node = parser.find_child_by_field(class_node, "superclasses")
    if not superclasses_node:
        return False

    bases_text = parser.get_node_text(superclasses_node, source_bytes)
    # Check for Enum, IntEnum, StrEnum, etc.
    return "Enum" in bases_text


def extract_enum_members(
    class_node: Node, source_bytes: bytes, parser: TreeSitterParser
) -> list[str]:
    """Extract enum member names from class body.

    Args:
        class_node: Class definition node
        source_bytes: Source code bytes
        parser: Tree-sitter parser instance

    Returns:
        List of enum member names
    """
    body_node = parser.find_child_by_field(class_node, "body")
    if not body_node:
        return []

    members = []
    for child in body_node.children:
        # Enum members are assignments in Python
        if child.type == "expression_statement":
            # Look for assignment nodes
            for subchild in child.children:
                if subchild.type == "assignment":
                    left_node = subchild.child_by_field_name("left")
                    if left_node and left_node.type == "identifier":
                        member_name = parser.get_node_text(left_node, source_bytes)
                        # Skip private/magic methods
                        if not member_name.startswith("_"):
                            members.append(member_name)

    return members


def extract_calls(node: Node, source_code: bytes, parser: TreeSitterParser) -> list[dict[str, Any]]:
    """Extract call expressions from Python AST node.

    Args:
        node: AST node to analyze
        source_code: Source code bytes
        parser: Tree-sitter parser instance

    Returns:
        List of call expression dictionaries
    """
    calls = []

    def traverse(n: Node) -> None:
        if n.type == "call":
            func_node = n.child_by_field_name("function")
            if func_node:
                name = parser.get_node_text(func_node, source_code)
                line = n.start_point[0] + 1
                is_external = "." not in name or name.split(".")[0] not in ["self", "cls"]

                calls.append({"name": name, "line": line, "external": is_external})

        for child in n.children:
            traverse(child)

    traverse(node)
    return calls


def extract_references(
    node: Node, source_code: bytes, parser: TreeSitterParser
) -> list[dict[str, Any]]:
    """Extract attribute access patterns from Python AST node.

    Args:
        node: AST node to analyze
        source_code: Source code bytes
        parser: Tree-sitter parser instance

    Returns:
        List of reference dictionaries
    """
    references = []

    def traverse(n: Node) -> None:
        if n.type == "attribute":
            name = parser.get_node_text(n, source_code)
            line = n.start_point[0] + 1
            ref_type = "config" if "settings" in name or "config" in name else "attribute"

            references.append({"name": name, "line": line, "type": ref_type})

        for child in n.children:
            traverse(child)

    traverse(node)
    return references


def calculate_complexity(node: Node) -> dict[str, Any]:
    """Calculate cyclomatic complexity of Python code.

    Args:
        node: AST node to analyze

    Returns:
        Dictionary with complexity metrics
    """
    # Python-specific decision points and nesting structures
    decision_node_types = [
        "if_statement",
        "elif_clause",
        "while_statement",
        "for_statement",
        "boolean_operator",
    ]
    nesting_node_types = ["if_statement", "while_statement", "for_statement"]

    # Delegate to generic implementation
    return calculate_complexity_generic(node, decision_node_types, nesting_node_types)
