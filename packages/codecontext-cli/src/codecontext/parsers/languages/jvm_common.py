"""Common base class for JVM language parsers (Java, Kotlin).

This module provides shared functionality for JVM parsers to reduce code duplication.
The main differences between Java and Kotlin parsers are:
1. AST node type extraction methods (field vs type lookups)
2. Method signature formatting
3. Enum extraction (different AST structures)
4. Top-level function support (Kotlin only)
"""

from abc import abstractmethod
from pathlib import Path
from uuid import UUID

from codecontext_core.models import CodeObject, Language, ObjectType
from tree_sitter import Node, Tree

from codecontext.parsers.base import BaseCodeParser
from codecontext.parsers.common.extractors import extract_name_and_build_object
from codecontext.parsers.common.nl_generator import NLGeneratorMixin


class JVMCommonParser(BaseCodeParser, NLGeneratorMixin):  # Mixin order is correct
    """Base parser with shared methods for Java and Kotlin.

    This class extracts common patterns between Java and Kotlin parsers to reduce
    duplication (~140 LOC of shared code).

    Subclasses must implement abstract methods for language-specific behaviors:
    - _get_name_node: Extract name node from AST (field vs type lookup)
    - _get_method_node_type: Get the AST node type for methods
    - _format_method_signature: Format method signature (Java vs Kotlin style)
    """

    # Subclasses must set this
    language: Language

    def _extract_javadoc(self, node: Node, source_bytes: bytes) -> str | None:
        """Extract Javadoc/KDoc from node's preceding comment."""
        prev = node.prev_sibling
        while prev and prev.type in ("comment", "block_comment", "line_comment"):
            if prev.type in ("block_comment", "comment"):
                text = self.parser.get_node_text(prev, source_bytes)
                if text.startswith("/**") and text.endswith("*/"):
                    lines = text[3:-2].strip().split("\n")
                    cleaned = [line.strip().lstrip("* ").rstrip() for line in lines]
                    return "\n".join(line for line in cleaned if line).strip()
            prev = prev.prev_sibling
        return None

    @abstractmethod
    def _get_name_node(self, node: Node) -> Node | None:
        """Get name node from a class/interface/method node.

        Java uses: find_child_by_field(node, "name")
        Kotlin uses: find_child_by_type(node, "type_identifier" or "simple_identifier")

        Args:
            node: The AST node to extract name from

        Returns:
            The name node, or None if not found
        """
        pass

    @abstractmethod
    def _get_method_node_type(self) -> str:
        """Get the AST node type for methods.

        Java: "method_declaration"
        Kotlin: "function_declaration"

        Returns:
            The node type string for methods
        """
        pass

    @abstractmethod
    def _format_method_signature(self, name: str, node: Node, source_bytes: bytes) -> str:
        """Format method signature in language-specific style.

        Java: "methodName(params)" or "methodName()"
        Kotlin: "fun methodName()" (without params for simplicity)

        Args:
            name: Method name
            node: Method node
            source_bytes: Source code as bytes

        Returns:
            Formatted method signature
        """
        pass

    def _extract_classes(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract class definitions with nested methods (shared by Java/Kotlin).

        Uses chunking strategy to split large classes into summary + methods.
        """
        objects: list[CodeObject] = []

        # Extract all class nodes
        class_nodes = self.parser.traverse_tree(tree, ["class_declaration"])
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
                    language=self.language,
                    parser=self.parser,
                    method_extractor_func=self._extract_method,
                    language_parser=self,
                )
                objects.extend(chunked_objects)
            else:
                # Traditional extraction: whole class + methods
                class_obj = self._extract_class(class_node, source_bytes, file_path, relative_path)
                if class_obj:
                    objects.append(class_obj)

                    # Extract methods within the class
                    for method_node in method_nodes:
                        method_obj = self._extract_method(
                            method_node,
                            source_bytes,
                            file_path,
                            relative_path,
                            class_obj.id,
                        )
                        if method_obj:
                            objects.append(method_obj)

        return objects

    def _extract_interfaces(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract interface definitions (shared by Java/Kotlin)."""
        objects: list[CodeObject] = []

        # Extract all interface nodes
        interface_nodes = self.parser.traverse_tree(tree, ["interface_declaration"])
        for interface_node in interface_nodes:
            interface_obj = self._extract_interface(
                interface_node, source_bytes, file_path, relative_path
            )
            if interface_obj:
                objects.append(interface_obj)

        return objects

    def _extract_class(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
    ) -> CodeObject | None:
        """Extract class declaration (shared by Java/Kotlin).

        Note: For Kotlin, this skips enum classes which are handled by _extract_enums.
        """
        # Skip Kotlin enum classes (handled by _extract_enums instead)
        if hasattr(self, "_has_enum_modifier") and self._has_enum_modifier(node, source_bytes):
            return None

        name_node = self._get_name_node(node)
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)
        signature = f"class {name}"

        method_nodes = self._get_class_methods(node)
        methods_count = len(method_nodes)

        docstring = self._extract_javadoc(node, source_bytes)
        self._generate_class_nl(name=name, methods_count=methods_count, docstring=docstring)

        # Build qualified name (for top-level classes, it's just the name)
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

    def _extract_interface(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
    ) -> CodeObject | None:
        """Extract interface declaration (shared by Java/Kotlin)."""
        name_node = self._get_name_node(node)
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)
        signature = f"interface {name}"

        docstring = self._extract_javadoc(node, source_bytes)
        self._generate_interface_nl(name=name, docstring=docstring)

        # Build qualified name (for top-level interfaces, it's just the name)
        qualified_name = name

        return extract_name_and_build_object(
            node=node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.INTERFACE,
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
        """Extract method declaration (shared by Java/Kotlin)."""
        name_node = self._get_name_node(node)
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)
        signature = self._format_method_signature(name, node, source_bytes)

        is_constructor = name in ["<init>", "constructor"] or (
            self.language == Language.JAVA and name == name[0].upper() + name[1:]
        )

        docstring = self._extract_javadoc(node, source_bytes)
        self._generate_function_nl(name=name, is_constructor=is_constructor, docstring=docstring)

        # Build qualified name by finding parent class/interface
        qualified_name = name
        parent = node.parent
        while parent:
            if parent.type in ["class_declaration", "interface_declaration"]:
                parent_name_node = self._get_name_node(parent)
                if parent_name_node:
                    parent_name = self.parser.get_node_text(parent_name_node, source_bytes)
                    qualified_name = f"{parent_name}.{name}"
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

    def _get_class_methods(self, class_node: Node) -> list[Node]:
        """Get method nodes within a class (shared by Java/Kotlin)."""
        # Java uses "body" field, Kotlin uses "class_body" type
        body_node = self.parser.find_child_by_field(class_node, "body")
        if not body_node:
            # Try Kotlin's class_body type
            body_node = self.parser.find_child_by_type(class_node, "class_body")
        if not body_node:
            return []

        methods = []
        method_node_type = self._get_method_node_type()
        for child in body_node.children:
            if child.type == method_node_type:
                methods.append(child)
        return methods

    def _extract_package_name(self, tree: Tree, source_bytes: bytes) -> str | None:
        """Extract package declaration from JVM source file.

        Args:
            tree: Tree-sitter parse tree
            source_bytes: Source code as bytes

        Returns:
            Package name (e.g., "com.ecommerce.order.domain") or None if not found
        """
        package_nodes = self.parser.traverse_tree(tree, ["package_declaration"])
        if not package_nodes:
            return None

        package_node = package_nodes[0]
        # Get package identifier (scoped_identifier or identifier)
        for child in package_node.children:
            if child.type in ["scoped_identifier", "identifier"]:
                return self.parser.get_node_text(child, source_bytes)
        return None

    def _get_enum_qualified_name(
        self, tree: Tree, enum_node: Node, source_bytes: bytes, enum_name: str
    ) -> str:
        """Build qualified name for enum: package.EnumName

        Args:
            tree: Tree-sitter parse tree
            enum_node: Enum AST node
            source_bytes: Source code as bytes
            enum_name: Enum name

        Returns:
            Qualified name (e.g., "com.ecommerce.order.domain.OrderStatus")
        """
        package = self._extract_package_name(tree, source_bytes)
        if package:
            return f"{package}.{enum_name}"
        return enum_name
