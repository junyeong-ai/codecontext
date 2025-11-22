"""Common base class for JavaScript and TypeScript parsers.

This module provides shared functionality for JS/TS parsers to reduce code duplication.
"""

from pathlib import Path
from typing import Any
from uuid import UUID

from codecontext_core.models import CodeObject, Language, ObjectType
from tree_sitter import Node

from codecontext.indexer.ast_parser import TreeSitterParser
from codecontext.parsers.base import BaseCodeParser
from codecontext.parsers.common.extractors import extract_name_and_build_object
from codecontext.parsers.common.nl_generator import NLGeneratorMixin
from codecontext.parsers.common.utilities.ast_common import (
    calculate_complexity_generic,
    extract_calls_generic,
    extract_references_generic,
)


class JSCommonParser(BaseCodeParser, NLGeneratorMixin):  # Mixin order is correct
    """Base parser with shared methods for JavaScript and TypeScript.

    This class extracts common patterns between JS and TS parsers to reduce
    duplication (~250 LOC of shared code).
    """

    language: Language

    def _extract_jsdoc(self, node: Node, source_bytes: bytes) -> str | None:
        """Extract JSDoc/TSDoc from node's preceding comment.

        Args:
            node: Tree-sitter node (class, function, method)
            source_bytes: Source code as bytes

        Returns:
            JSDoc text (without comment markers) or None if not found
        """
        prev = node.prev_sibling
        while prev and prev.type == "comment":
            text = self.parser.get_node_text(prev, source_bytes)
            if text.startswith("/**") and text.endswith("*/"):
                lines = text[3:-2].strip().split("\n")
                cleaned = [line.strip().lstrip("* ").rstrip() for line in lines]
                return "\n".join(line for line in cleaned if line).strip()
            prev = prev.prev_sibling
        return None

    def _extract_class(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
    ) -> CodeObject | None:
        """Extract class declaration (shared by JS/TS)."""
        name_node = self.parser.find_child_by_field(node, "name")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)
        signature = f"class {name}"

        docstring = self._extract_jsdoc(node, source_bytes)
        qualified_name = name

        return extract_name_and_build_object(
            node=node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.CLASS,
            language=self.language,
            signature=signature,
            name=name,
            parser=self.parser,
            language_parser=self,
            docstring=docstring,
            qualified_name=qualified_name,
        )

    def _extract_method(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
        parent_id: UUID | str | None,
    ) -> CodeObject | None:
        """Extract method definition (shared by JS/TS)."""
        name_node = self.parser.find_child_by_field(node, "name")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)
        signature = f"{name}()"

        docstring = self._extract_jsdoc(node, source_bytes)
        qualified_name = name
        parent = node.parent
        while parent:
            if parent.type == "class_declaration":
                class_name_node = self.parser.find_child_by_field(parent, "name")
                if class_name_node:
                    class_name = self.parser.get_node_text(class_name_node, source_bytes)
                    qualified_name = f"{class_name}.{name}"
                break
            parent = parent.parent

        return extract_name_and_build_object(
            node=node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.METHOD,
            language=self.language,
            signature=signature,
            name=name,
            parser=self.parser,
            language_parser=self,
            parent_id=parent_id,
            docstring=docstring,
            qualified_name=qualified_name,
        )

    def _extract_function(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
    ) -> CodeObject | None:
        """Extract function declaration (shared by JS/TS)."""
        name_node = self.parser.find_child_by_field(node, "name")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)
        signature = f"function {name}()"

        docstring = self._extract_jsdoc(node, source_bytes)
        qualified_name = name

        return extract_name_and_build_object(
            node=node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.FUNCTION,
            language=self.language,
            signature=signature,
            name=name,
            parser=self.parser,
            language_parser=self,
            docstring=docstring,
            qualified_name=qualified_name,
        )

    def _extract_arrow_function_assignment(
        self,
        var_node: Node,
        name_node: Node,
        arrow_func_node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
    ) -> CodeObject | None:
        """Extract arrow function assigned to a variable (React component pattern).

        This handles the pattern: const ComponentName = (props) => { ... }

        Args:
            var_node: The variable_declarator node
            name_node: The identifier node containing the variable name
            arrow_func_node: The arrow_function node
            source_bytes: Source code as bytes
            file_path: Path to the file
            relative_path: Relative path string

        Returns:
            CodeObject for the arrow function component, or None if extraction fails
        """
        name = self.parser.get_node_text(name_node, source_bytes)

        params_node = self.parser.find_child_by_field(arrow_func_node, "parameters")
        params_text = ""
        if params_node:
            params_text = self.parser.get_node_text(params_node, source_bytes)

        return_type_node = self.parser.find_child_by_field(arrow_func_node, "return_type")
        return_type_text = ""
        if return_type_node:
            return_type_text = ": " + self.parser.get_node_text(return_type_node, source_bytes)

        signature = f"const {name} = {params_text}{return_type_text} => ..."
        docstring = self._extract_jsdoc(var_node, source_bytes)
        qualified_name = name

        return extract_name_and_build_object(
            node=arrow_func_node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.FUNCTION,
            language=self.language,
            signature=signature,
            name=name,
            parser=self.parser,
            language_parser=self,
            docstring=docstring,
            qualified_name=qualified_name,
        )

    def _get_class_methods(self, class_node: Node) -> list[Node]:
        """Get method nodes within a class (shared by JS/TS)."""
        body_node = self.parser.find_child_by_field(class_node, "body")
        if not body_node:
            return []

        methods = []
        for child in body_node.children:
            if child.type == "method_definition":
                methods.append(child)
        return methods

    def _is_top_level_variable_declarator(self, node: Node) -> bool:
        """Check if variable_declarator is at top level (not nested in function/method).

        For React component pattern extraction, we need to ensure the variable is:
        - Not inside a function body
        - Not inside a class method
        - Not inside another arrow function

        The variable_declarator is wrapped in: lexical_declaration -> export_statement/program
        """
        parent = node.parent
        while parent:
            # If we find these, the variable is nested (NOT top-level)
            if parent.type in [
                "function_declaration",
                "arrow_function",
                "method_definition",
                "class_declaration",
            ]:
                return False
            # If we reach program or export_statement, it's top-level
            if parent.type in ["program", "export_statement"]:
                return True
            parent = parent.parent
        return False

    def extract_ast_metadata(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Extract calls, references, complexity from JS/TS AST node (shared logic)."""

        def get_function_name(
            call_node: Node, src_bytes: bytes, parser: TreeSitterParser
        ) -> str | None:
            func_node = call_node.child_by_field_name("function")
            if func_node:
                return parser.get_node_text(func_node, src_bytes)
            return None

        calls = extract_calls_generic(
            node, source_code, self.parser, ["call_expression"], get_function_name
        )

        references = extract_references_generic(
            node, source_code, self.parser, ["member_expression"]
        )

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
