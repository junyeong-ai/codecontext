"""TypeScript language parser using Tree-sitter with optimization support."""

from pathlib import Path

from codecontext_core.models import CodeObject, Language, ObjectType
from tree_sitter import Node, Tree

from codecontext.indexer.ast_parser import ParserConfig
from codecontext.parsers.common.extractors import extract_name_and_build_object
from codecontext.parsers.common.parser_factory import TreeSitterParserFactory
from codecontext.parsers.languages.js_common import JSCommonParser


class TypeScriptParser(JSCommonParser):
    """Parser for TypeScript source code with Tree-sitter optimization.

    Features:
    - 7-second timeout for complex type resolution
    - TSX grammar support (both .ts and .tsx files)
    - Graceful error recovery for files with syntax errors

    Note: This parser uses the TSX grammar which supports both TypeScript (.ts)
    and TypeScript with JSX (.tsx) files. The TSX grammar is a superset of TypeScript.
    """

    def __init__(self, parser_config: ParserConfig | None = None) -> None:
        """Initialize TypeScript parser with TSX grammar and optimization support.

        Args:
            parser_config: Optional parser configuration. If None, uses defaults
                          with TypeScript-specific 7s timeout override.
        """
        # TreeSitterParserFactory automatically uses TSX grammar for TypeScript
        parser = TreeSitterParserFactory.create_parser(Language.TYPESCRIPT, parser_config)
        super().__init__(Language.TYPESCRIPT, parser)

    def get_file_extensions(self) -> list[str]:
        """Get list of supported file extensions.

        Returns:
            List of TypeScript file extensions
        """
        return [".ts", ".tsx"]

    # Template Method hooks implementation

    def _extract_classes(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract TypeScript class definitions with nested methods.

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
                    language=Language.TYPESCRIPT,
                    parser=self.parser,
                    method_extractor_func=self._extract_method,
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
                            class_obj.deterministic_id,
                        )
                        if method_obj:
                            objects.append(method_obj)

        return objects

    def _extract_interfaces(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract TypeScript interface definitions."""
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

    def _extract_functions(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract top-level TypeScript functions and arrow function components."""
        objects: list[CodeObject] = []

        # Extract top-level function declarations
        function_nodes = self.parser.traverse_tree(tree, ["function_declaration"])
        for func_node in function_nodes:
            if self._is_top_level(func_node):
                func_obj = self._extract_function(func_node, source_bytes, file_path, relative_path)
                if func_obj:
                    objects.append(func_obj)

        # Extract arrow functions assigned to variables (React component pattern)
        # Pattern: const ComponentName = (props) => { ... }
        var_nodes = self.parser.traverse_tree(tree, ["variable_declarator"])
        for var_node in var_nodes:
            name_node = self.parser.find_child_by_field(var_node, "name")
            value_node = self.parser.find_child_by_field(var_node, "value")

            if (
                value_node
                and value_node.type == "arrow_function"
                and name_node
                and self._is_top_level_variable_declarator(var_node)
            ):
                func_obj = self._extract_arrow_function_assignment(
                    var_node, name_node, value_node, source_bytes, file_path, relative_path
                )
                if func_obj:
                    objects.append(func_obj)

        return objects

    def _extract_enums(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract TypeScript enum definitions using generic pattern.

        TypeScript has native enum support with "enum_declaration" node type.
        Uses BaseCodeParser._extract_enums_generic() to eliminate duplication.
        """
        return self._extract_enums_generic(
            tree=tree,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            node_types=["enum_declaration"],
            name_field="name",
            members_extractor=lambda node, src, _parser: self._extract_enum_members_ts(node, src),
            enum_keyword="enum",
            qualified_name_extractor=lambda tree, node, src, name: self._get_enum_qualified_name(
                tree, node, src, name, relative_path
            ),
        )

    def _get_enum_qualified_name(
        self, tree: Tree, enum_node: Node, source_bytes: bytes, enum_name: str, relative_path: str
    ) -> str:
        """Build qualified name for TypeScript enum using module path.

        Args:
            tree: Tree-sitter parse tree (unused)
            enum_node: Enum AST node (unused)
            source_bytes: Source code (unused)
            enum_name: Enum name
            relative_path: Relative file path

        Returns:
            Qualified name (e.g., "utils.types.Status")
        """
        # Convert file path to module path
        # e.g., frontend/web/utils/types.ts -> utils.types.EnumName
        module_path = relative_path.replace(".ts", "").replace(".tsx", "").replace("/", ".")

        # Extract module part after 'src/' if present
        if "/src/" in relative_path:
            module_path = (
                relative_path.split("/src/")[-1]
                .replace(".ts", "")
                .replace(".tsx", "")
                .replace("/", ".")
            )

        return f"{module_path}.{enum_name}"

    def _extract_enum_members_ts(self, enum_node: Node, source_bytes: bytes) -> list[str]:
        """Extract enum member names from enum body."""
        body_node = self.parser.find_child_by_field(enum_node, "body")
        if not body_node:
            return []

        members = []
        for child in body_node.children:
            # TypeScript enum members are "property_identifier" or "enum_assignment" nodes
            if child.type == "property_identifier":
                member_name = self.parser.get_node_text(child, source_bytes)
                members.append(member_name)
            elif child.type == "enum_assignment":
                # Get the name from enum_assignment
                name_node = self.parser.find_child_by_field(child, "name")
                if name_node:
                    member_name = self.parser.get_node_text(name_node, source_bytes)
                    members.append(member_name)

        return members

    def _extract_interface(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        relative_path: str,
    ) -> CodeObject | None:
        """Extract interface declaration."""
        name_node = self.parser.find_child_by_field(node, "name")
        if not name_node:
            return None

        name = self.parser.get_node_text(name_node, source_bytes)
        signature = f"interface {name}"

        # Build qualified name (for top-level interfaces, it's just the name)
        qualified_name = name

        return extract_name_and_build_object(
            node=node,
            source_bytes=source_bytes,
            file_path=file_path,
            relative_path=relative_path,
            object_type=ObjectType.INTERFACE,
            language=Language.TYPESCRIPT,
            signature=signature,
            name=name,
            parser=self.parser,
            language_parser=self,
            qualified_name=qualified_name,
        )

    def _is_top_level(self, node: Node) -> bool:
        """Check if node is at top level (not nested in class/interface/method)."""
        return self._is_top_level_function(
            node, class_types=["class_declaration", "interface_declaration", "method_definition"]
        )
