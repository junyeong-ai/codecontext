"""Common base class for JavaScript and TypeScript parsers.

This module provides shared functionality for JS/TS parsers to reduce code duplication.
"""

from typing import Any
from pathlib import Path
from uuid import UUID

from tree_sitter import Node

from codecontext_core.models import CodeObject, Language, ObjectType
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

    # Subclasses must set[Any] this
    language: Language

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

        # Count methods for NL description
        method_nodes = self._get_class_methods(node)
        methods_count = len(method_nodes)

        # Generate natural language description
        nl_desc = self._generate_class_nl(name=name, methods_count=methods_count)

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
            nl_description=nl_desc,
        )

    def _extract_method(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
        parent_id: UUID | None,
    ) -> CodeObject | None:
        """Extract method definition (shared by JS/TS)."""
        name_node = self.parser.find_child_by_field(node, "name")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)
        signature = f"{name}()"

        # Check if it's a constructor
        is_constructor = name == "constructor"

        # Generate natural language description
        nl_desc = self._generate_function_nl(name=name, is_constructor=is_constructor)

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
            nl_description=nl_desc,
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

        # Generate natural language description
        nl_desc = self._generate_function_nl(name=name)

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
            nl_description=nl_desc,
        )

    def _extract_arrow_function_assignment(
        self,
        _var_node: Node,
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

        # Extract parameters for signature
        params_node = self.parser.find_child_by_field(arrow_func_node, "parameters")
        params_text = ""
        if params_node:
            params_text = self.parser.get_node_text(params_node, source_bytes)

        # Extract return type if present (TypeScript)
        return_type_node = self.parser.find_child_by_field(arrow_func_node, "return_type")
        return_type_text = ""
        if return_type_node:
            return_type_text = ": " + self.parser.get_node_text(return_type_node, source_bytes)

        # Build signature
        signature = f"const {name} = {params_text}{return_type_text} => ..."

        # Generate natural language description
        nl_desc = self._generate_function_nl(name=name)

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
            nl_description=nl_desc,
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
