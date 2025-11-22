"""Kotlin language parser using Tree-sitter with optimization support."""

from pathlib import Path
from typing import Any

from codecontext_core.models import CodeObject, Language, ObjectType
from tree_sitter import Node, Tree

from codecontext.indexer.ast_parser import ParserConfig, TreeSitterParser
from codecontext.parsers.common.extractors import extract_name_and_build_object
from codecontext.parsers.common.parser_factory import TreeSitterParserFactory
from codecontext.parsers.common.utilities.ast_common import (
    calculate_complexity_generic,
    extract_calls_generic,
    extract_references_generic,
)
from codecontext.parsers.languages.jvm_common import JVMCommonParser


class KotlinParser(JVMCommonParser):
    """Parser for Kotlin source code with Tree-sitter optimization.

    Features:
    - 10-second timeout for complex DSL patterns (Elasticsearch, Gradle, etc.)
    - Graceful error recovery for files with syntax errors
    - Performance monitoring for slow parsing detection
    """

    def __init__(self, parser_config: ParserConfig | None = None) -> None:
        """Initialize Kotlin parser with optimization support.

        Args:
            parser_config: Optional parser configuration. If None, uses defaults
                          with Kotlin-specific 10s timeout override.
        """
        parser = TreeSitterParserFactory.create_parser(Language.KOTLIN, parser_config)
        super().__init__(Language.KOTLIN, parser)

    def get_file_extensions(self) -> list[str]:
        """Get list[Any] of supported file extensions.

        Returns:
            List of Kotlin file extensions
        """
        return [".kt", ".kts"]

    # JVMCommonParser abstract method implementations

    def _get_name_node(self, node: Node) -> Node | None:
        """Get name node using Kotlin's type-based lookup.

        Kotlin uses different identifier types:
        - Classes/Interfaces: "type_identifier"
        - Functions/Methods: "simple_identifier"
        """
        # Try type_identifier first (for classes/interfaces)
        name_node = self.parser.find_child_by_type(node, "type_identifier")
        if name_node:
            return name_node
        # Fall back to simple_identifier (for functions/methods)
        return self.parser.find_child_by_type(node, "simple_identifier")

    def _get_method_node_type(self) -> str:
        """Get Kotlin method node type."""
        return "function_declaration"

    def _format_method_signature(self, name: str, _node: Node, _source_bytes: bytes) -> str:
        """Format Kotlin method signature (simplified, without params)."""
        return f"fun {name}()"

    # Template Method hooks implementation

    def _extract_functions(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract top-level Kotlin functions."""
        objects: list[CodeObject] = []

        # Extract top-level functions (not inside classes/interfaces)
        function_nodes = self.parser.traverse_tree(tree, ["function_declaration"])
        for func_node in function_nodes:
            if self._is_top_level(func_node):
                func_obj = self._extract_function(func_node, source_bytes, file_path, relative_path)
                if func_obj:
                    objects.append(func_obj)

        return objects

    def _extract_function(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
    ) -> CodeObject | None:
        """Extract function declaration."""
        name_node = self.parser.find_child_by_type(node, "simple_identifier")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)
        signature = f"fun {name}()"

        # For top-level functions, qualified_name is just the name
        qualified_name = name

        return extract_name_and_build_object(
            node=node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.FUNCTION,
            language=Language.KOTLIN,
            signature=signature,
            name=name,
            parser=self.parser,
            language_parser=self,
            qualified_name=qualified_name,
        )

    def _extract_enums(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract Kotlin enum definitions using generic pattern.

        Kotlin enum classes have explicit "enum" modifier.
        Uses BaseCodeParser._extract_enums_generic() to eliminate duplication.
        """
        return self._extract_enums_generic(
            tree=tree,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            node_types=["class_declaration"],
            is_enum_checker=self._has_enum_modifier,
            name_field="type_identifier",  # Will trigger type_identifier fallback in base
            members_extractor=lambda node, src, _parser: self._extract_enum_entries(node, src),
            enum_keyword="enum class",
            qualified_name_extractor=self._get_enum_qualified_name,
        )

    def _has_enum_modifier(self, class_node: Node, source_bytes: bytes) -> bool:
        """Check if a class has the 'enum' modifier."""
        for child in class_node.children:
            if child.type == "modifiers":
                modifiers_text = self.parser.get_node_text(child, source_bytes)
                if "enum" in modifiers_text:
                    return True
        return False

    def _extract_enum_entries(self, class_node: Node, source_bytes: bytes) -> list[str]:
        """Extract enum entry names from class body."""
        body_node = self.parser.find_child_by_type(class_node, "enum_class_body")
        if not body_node:
            # Try regular class_body
            body_node = self.parser.find_child_by_type(class_node, "class_body")
        if not body_node:
            return []

        entries = []
        for child in body_node.children:
            # Kotlin enum entries are "enum_entry" nodes
            if child.type == "enum_entry":
                # Get the identifier from enum_entry
                for subchild in child.children:
                    if subchild.type == "simple_identifier":
                        entry_name = self.parser.get_node_text(subchild, source_bytes)
                        entries.append(entry_name)
                        break

        return entries

    def _is_top_level(self, node: Node) -> bool:
        """Check if node is at top level (not inside class/interface)."""
        return self._is_top_level_function(
            node, class_types=["class_declaration", "interface_declaration"]
        )

    def extract_ast_metadata(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Extract calls, references, complexity from Kotlin AST node."""

        def get_function_name(call_node: Node, src_bytes: bytes, parser: TreeSitterParser) -> str:
            func_node = call_node.child_by_field_name("function")
            if func_node:
                return parser.get_node_text(func_node, src_bytes)
            return ""

        calls = extract_calls_generic(
            node, source_code, self.parser, ["call_expression"], get_function_name
        )

        references = extract_references_generic(
            node, source_code, self.parser, ["navigation_expression"]
        )

        complexity = calculate_complexity_generic(
            node,
            [
                "if_expression",
                "when_expression",
                "while_statement",
                "for_statement",
                "binary_expression",
            ],
            ["if_expression", "while_statement", "for_statement"],
        )

        return {
            "calls": calls,
            "references": references,
            "complexity": complexity,
        }
