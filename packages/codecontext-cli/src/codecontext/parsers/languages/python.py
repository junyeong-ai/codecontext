"""Python language parser using Tree-sitter with optimization support."""

from typing import Any
from pathlib import Path
from uuid import UUID

from tree_sitter import Node, Tree

from codecontext_core.models import CodeObject, Language, ObjectType
from codecontext.indexer.ast_parser import ParserConfig
from codecontext.parsers.base import BaseCodeParser
from codecontext.parsers.common.extractors import extract_name_and_build_object
from codecontext.parsers.common.nl_generator import NLGeneratorMixin
from codecontext.parsers.common.parser_factory import TreeSitterParserFactory
from codecontext.parsers.common.utilities.ast_common import extract_single_class_with_methods
from codecontext.parsers.languages.python_ast_utils import (
    calculate_complexity,
    extract_calls,
    extract_enum_members,
    extract_references,
    is_enum_class,
)


class PythonParser(BaseCodeParser, NLGeneratorMixin):  # Mixin order is correct
    """Parser for Python source code with Tree-sitter optimization.

    Features:
    - 5-second default timeout (suitable for most Python files)
    - Graceful error recovery for files with syntax errors
    - Performance monitoring for slow parsing detection
    """

    def __init__(self, parser_config: ParserConfig | None = None) -> None:
        """Initialize Python parser with optimization support.

        Args:
            parser_config: Optional parser configuration. If None, uses defaults.
        """
        parser = TreeSitterParserFactory.create_parser(Language.PYTHON, parser_config)
        super().__init__(Language.PYTHON, parser)

    def get_file_extensions(self) -> list[str]:
        """Get list[Any] of supported file extensions.

        Returns:
            List of Python file extensions
        """
        return [".py"]

    # Template Method hooks implementation

    def _extract_classes(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract Python class definitions with nested methods.

        Uses chunking strategy to split large classes into summary + methods.
        """
        objects: list[CodeObject] = []

        # Extract all class nodes
        class_nodes = self.parser.traverse_tree(tree, ["class_definition"])
        for class_node in class_nodes:
            # Get method nodes for this class
            method_nodes = self._get_class_methods(class_node)

            if self.enable_chunking:
                # Use chunking strategy for large classes
                chunked_objects = self.chunker.chunk_class_with_methods(
                    class_node=class_node,
                    method_nodes=method_nodes,
                    source_bytes=source_bytes,
                    file_path=file_path,
                    relative_path=relative_path,
                    language=Language.PYTHON,
                    parser=self.parser,
                    method_extractor_func=self._extract_method,
                )
                objects.extend(chunked_objects)
            else:
                # Traditional extraction: whole class + methods (delegated to common utility)
                class_obj = self._extract_class(class_node, source_bytes, file_path, relative_path)
                objects.extend(
                    extract_single_class_with_methods(
                        class_obj,
                        method_nodes,
                        self._extract_method,
                        source_bytes,
                        file_path,
                        relative_path,
                    )
                )

        return objects

    def _extract_interfaces(
        self, _tree: Tree, _source_bytes: bytes, _file_path: Path, _relative_path: str
    ) -> list[CodeObject]:
        """Python doesn't have interfaces - return empty list[Any]."""
        return []

    def _extract_functions(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract top-level Python functions."""
        objects: list[CodeObject] = []

        # Extract top-level functions (not inside classes)
        function_nodes = self._get_top_level_functions(tree)
        for func_node in function_nodes:
            func_obj = self._extract_function(func_node, source_bytes, file_path, relative_path)
            if func_obj:
                objects.append(func_obj)

        return objects

    def _extract_enums(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract Python enum definitions using generic pattern.

        Identifies classes that inherit from Enum and extracts their members.
        Uses BaseCodeParser._extract_enums_generic() to eliminate duplication.
        """
        return self._extract_enums_generic(
            tree=tree,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            node_types=["class_definition"],
            is_enum_checker=lambda node, src: is_enum_class(node, src, self.parser),
            name_field="name",
            members_extractor=lambda node, src, parser: extract_enum_members(node, src, parser),
            enum_keyword="enum",
        )

    def _extract_class(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
    ) -> CodeObject | None:
        """Extract class definition."""
        name_node = self.parser.find_child_by_field(node, "name")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)

        # Extract base classes for signature and NL generation
        base_classes = []
        superclasses_node = self.parser.find_child_by_field(node, "superclasses")
        signature = f"class {name}"
        if superclasses_node:
            bases = self.parser.get_node_text(superclasses_node, source_bytes)
            signature = f"class {name}{bases}"
            # Parse base class names (remove parentheses and split by comma)
            bases_clean = bases.strip("()").replace(" ", "")
            if bases_clean:
                base_classes = [b.strip() for b in bases_clean.split(",")]

        # Count methods for NL description
        method_nodes = self._get_class_methods(node)
        methods_count = len(method_nodes)

        # Extract docstring
        docstring = self._extract_python_docstring(node, source_bytes)

        # Generate natural language description
        nl_desc = self._generate_class_nl(
            name=name,
            base_classes=base_classes if base_classes else None,
            methods_count=methods_count,
            docstring=docstring,
        )

        return extract_name_and_build_object(
            node=node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.CLASS,
            language=Language.PYTHON,
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
        """Extract method definition."""
        name_node = self.parser.find_child_by_field(node, "name")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)

        # Extract parameters for signature and NL generation
        param_names = []
        params_node = self.parser.find_child_by_field(node, "parameters")
        signature = f"def {name}()"
        if params_node:
            params = self.parser.get_node_text(params_node, source_bytes)
            signature = f"def {name}{params}"
            # Parse parameter names (skip 'self'/'cls')
            params_clean = params.strip("()").replace(" ", "")
            if params_clean:
                param_names = [
                    p.split(":")[0].split("=")[0].strip()
                    for p in params_clean.split(",")
                    if p and p not in ("self", "cls")
                ]

        # Check if it's a constructor
        is_constructor = name in ("__init__", "__new__")

        # Extract docstring
        docstring = self._extract_python_docstring(node, source_bytes)

        # Generate natural language description
        nl_desc = self._generate_function_nl(
            name=name,
            params=param_names if param_names else None,
            is_constructor=is_constructor,
            docstring=docstring,
        )

        return extract_name_and_build_object(
            node=node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.METHOD,
            language=Language.PYTHON,
            signature=signature,
            name=name,
            parser=self.parser,
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
        """Extract function definition."""
        name_node = self.parser.find_child_by_field(node, "name")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)

        # Extract parameters for signature and NL generation
        param_names = []
        params_node = self.parser.find_child_by_field(node, "parameters")
        signature = f"def {name}()"
        if params_node:
            params = self.parser.get_node_text(params_node, source_bytes)
            signature = f"def {name}{params}"
            # Parse parameter names
            params_clean = params.strip("()").replace(" ", "")
            if params_clean:
                param_names = [
                    p.split(":")[0].split("=")[0].strip() for p in params_clean.split(",") if p
                ]

        # Extract docstring
        docstring = self._extract_python_docstring(node, source_bytes)

        # Generate natural language description
        nl_desc = self._generate_function_nl(
            name=name, params=param_names if param_names else None, docstring=docstring
        )

        return extract_name_and_build_object(
            node=node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.FUNCTION,
            language=Language.PYTHON,
            signature=signature,
            name=name,
            parser=self.parser,
            nl_description=nl_desc,
        )

    def _extract_python_docstring(self, node: Node, source_bytes: bytes) -> str | None:
        """Extract docstring from a Python class or function node.

        Args:
            node: Tree-sitter node (class_definition or function_definition)
            source_bytes: Source code as bytes

        Returns:
            Docstring text (without quotes) or None if not found
        """
        # Find body node
        body_node = self.parser.find_child_by_field(node, "body")
        if not body_node:
            return None

        # Look for first expression statement with string
        for child in body_node.children:
            if child.type == "expression_statement":
                # Check if it contains a string node
                for expr_child in child.children:
                    if expr_child.type == "string":
                        docstring_raw = self.parser.get_node_text(expr_child, source_bytes)
                        # Remove quotes (""", ''', ", ')
                        docstring = docstring_raw.strip()
                        for quote in ['"""', "'''", '"', "'"]:
                            if docstring.startswith(quote) and docstring.endswith(quote):
                                docstring = docstring[len(quote) : -len(quote)]
                                break
                        return docstring.strip()
                break  # Only check first statement

        return None

    def _get_class_methods(self, class_node: Node) -> list[Node]:
        """Get method nodes within a class."""
        body_node = self.parser.find_child_by_field(class_node, "body")
        if not body_node:
            return []

        methods = []
        for child in body_node.children:
            if child.type == "function_definition":
                methods.append(child)
        return methods

    def _get_top_level_functions(self, tree: Tree) -> list[Node]:
        """Get top-level function nodes (not inside classes)."""
        all_functions = self.parser.traverse_tree(tree, ["function_definition"])
        top_level = []

        for func_node in all_functions:
            # Check if parent is module (root) or not inside a class
            parent = func_node.parent
            while parent:
                if parent.type == "class_definition":
                    break
                if parent.type == "module":
                    top_level.append(func_node)
                    break
                parent = parent.parent

        return top_level

    def extract_ast_metadata(self, node: Node, source_code: bytes) -> dict[str, Any]:
        """Extract calls, references, complexity from Python AST node."""
        return {
            "calls": extract_calls(node, source_code, self.parser),
            "references": extract_references(node, source_code, self.parser),
            "complexity": calculate_complexity(node),
        }
