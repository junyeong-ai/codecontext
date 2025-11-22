"""Python language parser using Tree-sitter with optimization support."""

from pathlib import Path
from typing import Any
from uuid import UUID

from codecontext_core.models import CodeObject, Language, ObjectType
from tree_sitter import Node, Tree

from codecontext.indexer.ast_parser import ParserConfig, TreeSitterParser
from codecontext.parsers.base import BaseCodeParser
from codecontext.parsers.common.extractors import extract_name_and_build_object
from codecontext.parsers.common.nl_generator import NLGeneratorMixin
from codecontext.parsers.common.parser_factory import TreeSitterParserFactory
from codecontext.parsers.common.utilities.ast_common import (
    calculate_complexity_generic,
    extract_calls_generic,
    extract_references_generic,
    extract_single_class_with_methods,
)


def _is_enum_class(class_node: Node, source_bytes: bytes, parser: TreeSitterParser) -> bool:
    """Check if a class inherits from Enum."""
    superclasses_node = parser.find_child_by_field(class_node, "superclasses")
    if not superclasses_node:
        return False
    bases_text = parser.get_node_text(superclasses_node, source_bytes)
    return "Enum" in bases_text


def _extract_enum_members(
    class_node: Node, source_bytes: bytes, parser: TreeSitterParser
) -> list[str]:
    """Extract enum member names from class body."""
    body_node = parser.find_child_by_field(class_node, "body")
    if not body_node:
        return []

    members = []
    for child in body_node.children:
        if child.type == "expression_statement":
            for subchild in child.children:
                if subchild.type == "assignment":
                    left_node = subchild.child_by_field_name("left")
                    if left_node and left_node.type == "identifier":
                        member_name = parser.get_node_text(left_node, source_bytes)
                        if not member_name.startswith("_"):
                            members.append(member_name)
    return members


def _get_enum_qualified_name(
    tree: Tree, enum_node: Node, source_bytes: bytes, enum_name: str, relative_path: str
) -> str:
    """Build qualified name for Python enum using module path.

    Args:
        tree: Tree-sitter parse tree (unused for Python)
        enum_node: Enum AST node (unused for Python)
        source_bytes: Source code as bytes (unused for Python)
        enum_name: Enum name
        relative_path: Relative file path

    Returns:
        Qualified name (e.g., "models.payment.PaymentStatus")
    """
    # Convert file path to module path
    # e.g., services/payment-service/src/models/payment.py -> models.payment.EnumName
    module_path = relative_path.replace(".py", "").replace("/", ".")

    # Extract module part after 'src/' if present
    if "/src/" in relative_path:
        module_path = relative_path.split("/src/")[-1].replace(".py", "").replace("/", ".")

    return f"{module_path}.{enum_name}"


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
            is_enum_checker=lambda node, src: _is_enum_class(node, src, self.parser),
            name_field="name",
            members_extractor=lambda node, src, parser: _extract_enum_members(node, src, parser),
            enum_keyword="enum",
            qualified_name_extractor=lambda tree, node, src, name: _get_enum_qualified_name(
                tree, node, src, name, relative_path
            ),
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

        superclasses_node = self.parser.find_child_by_field(node, "superclasses")
        signature = f"class {name}"
        if superclasses_node:
            bases = self.parser.get_node_text(superclasses_node, source_bytes)
            signature = f"class {name}{bases}"

        docstring = self._extract_python_docstring(node, source_bytes)
        qualified_name = name

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
        """Extract method definition."""
        name_node = self.parser.find_child_by_field(node, "name")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)

        params_node = self.parser.find_child_by_field(node, "parameters")
        signature = f"def {name}()"
        if params_node:
            params = self.parser.get_node_text(params_node, source_bytes)
            signature = f"def {name}{params}"

        docstring = self._extract_python_docstring(node, source_bytes)
        qualified_name = name
        parent = node.parent
        while parent:
            if parent.type == "class_definition":
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
            language=Language.PYTHON,
            signature=signature,
            name=name,
            parser=self.parser,
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
        """Extract function definition."""
        name_node = self.parser.find_child_by_field(node, "name")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)

        params_node = self.parser.find_child_by_field(node, "parameters")
        signature = f"def {name}()"
        if params_node:
            params = self.parser.get_node_text(params_node, source_bytes)
            signature = f"def {name}{params}"

        docstring = self._extract_python_docstring(node, source_bytes)
        qualified_name = name

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
            docstring=docstring,
            qualified_name=qualified_name,
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

        def get_function_name(
            call_node: Node, src_bytes: bytes, parser: TreeSitterParser
        ) -> str | None:
            func_node = call_node.child_by_field_name("function")
            return parser.get_node_text(func_node, src_bytes) if func_node else None

        return {
            "calls": extract_calls_generic(
                node,
                source_code,
                self.parser,
                call_node_types=["call"],
                get_function_name=get_function_name,
            ),
            "references": extract_references_generic(
                node, source_code, self.parser, reference_node_types=["attribute"]
            ),
            "complexity": calculate_complexity_generic(
                node,
                decision_node_types=[
                    "if_statement",
                    "for_statement",
                    "while_statement",
                    "except_clause",
                ],
                nesting_node_types=[
                    "function_definition",
                    "class_definition",
                    "for_statement",
                    "while_statement",
                ],
            ),
        }
