"""Java language parser using Tree-sitter with optimization support."""

from pathlib import Path
from typing import Any

from codecontext_core.models import CodeObject, Language
from tree_sitter import Node, Tree

from codecontext.indexer.ast_parser import ParserConfig, TreeSitterParser
from codecontext.parsers.common.parser_factory import TreeSitterParserFactory
from codecontext.parsers.common.utilities.ast_common import (
    calculate_complexity_generic,
    extract_calls_generic,
    extract_references_generic,
)
from codecontext.parsers.languages.jvm_common import JVMCommonParser


class JavaParser(JVMCommonParser):
    """Parser for Java source code with Tree-sitter optimization.

    Features:
    - 5-second default timeout (suitable for most Java files)
    - Graceful error recovery for files with syntax errors
    - Performance monitoring for slow parsing detection
    """

    def __init__(self, parser_config: ParserConfig | None = None) -> None:
        """Initialize Java parser with optimization support.

        Args:
            parser_config: Optional parser configuration. If None, uses defaults.
        """
        parser = TreeSitterParserFactory.create_parser(Language.JAVA, parser_config)
        super().__init__(Language.JAVA, parser)

    def get_file_extensions(self) -> list[str]:
        """Get list[Any] of supported file extensions.

        Returns:
            List of Java file extensions
        """
        return [".java"]

    # JVMCommonParser abstract method implementations

    def _get_name_node(self, node: Node) -> Node | None:
        """Get name node using Java's field-based lookup."""
        return self.parser.find_child_by_field(node, "name")

    def _get_method_node_type(self) -> str:
        """Get Java method node type."""
        return "method_declaration"

    def _format_method_signature(self, name: str, node: Node, source_bytes: bytes) -> str:
        """Format Java method signature with parameters."""
        # Get parameters for signature
        params_node = self.parser.find_child_by_field(node, "parameters")
        if params_node:
            params = self.parser.get_node_text(params_node, source_bytes)
            return f"{name}{params}"
        return f"{name}()"

    # Template Method hooks implementation

    def _extract_functions(
        self, _tree: Tree, _source_bytes: bytes, _file_path: Path, _relative_path: str
    ) -> list[CodeObject]:
        """Java doesn't have top-level functions - return empty list[Any]."""
        return []

    def _extract_enums(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract Java enum definitions using generic pattern.

        Java has explicit "enum_declaration" node type.
        Uses BaseCodeParser._extract_enums_generic() to eliminate duplication.
        """
        return self._extract_enums_generic(
            tree=tree,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            node_types=["enum_declaration"],
            name_field="name",
            members_extractor=lambda node, src, _parser: self._extract_enum_constants(node, src),
            enum_keyword="enum",
            qualified_name_extractor=self._get_enum_qualified_name,
        )

    def _extract_enum_constants(self, enum_node: Node, source_bytes: bytes) -> list[str]:
        """Extract enum constant names from enum body."""
        body_node = self.parser.find_child_by_field(enum_node, "body")
        if not body_node:
            return []

        constants = []
        for child in body_node.children:
            # Java enum constants are "enum_constant" nodes
            if child.type == "enum_constant":
                name_node = self.parser.find_child_by_field(child, "name")
                if name_node:
                    constant_name = self.parser.get_node_text(name_node, source_bytes)
                    constants.append(constant_name)

        return constants

    def extract_ast_metadata(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Extract calls, references, complexity from Java AST node."""

        def get_function_name(call_node: Node, src_bytes: bytes, parser: TreeSitterParser) -> str:
            name_node = call_node.child_by_field_name("name")
            if name_node:
                return parser.get_node_text(name_node, src_bytes)
            return ""

        calls = extract_calls_generic(
            node, source_code, self.parser, ["method_invocation"], get_function_name
        )

        references = extract_references_generic(node, source_code, self.parser, ["field_access"])

        complexity = calculate_complexity_generic(
            node,
            [
                "if_statement",
                "while_statement",
                "for_statement",
                "switch_statement",
                "ternary_expression",
            ],
            ["if_statement", "while_statement", "for_statement"],
        )

        return {
            "calls": calls,
            "references": references,
            "complexity": complexity,
        }
