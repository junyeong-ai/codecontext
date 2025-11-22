"""JavaScript language parser using Tree-sitter with optimization support."""

from pathlib import Path

from codecontext_core.models import CodeObject, Language
from tree_sitter import Node, Tree

from codecontext.indexer.ast_parser import ParserConfig
from codecontext.parsers.common.parser_factory import TreeSitterParserFactory
from codecontext.parsers.common.utilities.ast_common import extract_single_class_with_methods
from codecontext.parsers.languages.js_common import JSCommonParser


class JavaScriptParser(JSCommonParser):
    """Parser for JavaScript source code with Tree-sitter optimization.

    Features:
    - 5-second default timeout (suitable for most JavaScript files)
    - Graceful error recovery for files with syntax errors
    - Performance monitoring for slow parsing detection
    """

    def __init__(self, parser_config: ParserConfig | None = None) -> None:
        """Initialize JavaScript parser with optimization support.

        Args:
            parser_config: Optional parser configuration. If None, uses defaults.
        """
        parser = TreeSitterParserFactory.create_parser(Language.JAVASCRIPT, parser_config)
        super().__init__(Language.JAVASCRIPT, parser)

    def get_file_extensions(self) -> list[str]:
        """Get list of supported file extensions.

        Returns:
            List of JavaScript file extensions
        """
        return [".js", ".jsx"]

    # Template Method hooks implementation

    def _extract_classes(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract JavaScript class definitions with nested methods.

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
                    language=Language.JAVASCRIPT,
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
        """JavaScript doesn't have interfaces - return empty list."""
        return []

    def _extract_functions(
        self, tree: Tree, source_bytes: bytes, file_path: Path, relative_path: str
    ) -> list[CodeObject]:
        """Extract top-level JavaScript functions and arrow function components."""
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
        self, _tree: Tree, _source_bytes: bytes, _file_path: Path, _relative_path: str
    ) -> list[CodeObject]:
        """JavaScript doesn't have native enums.

        JavaScript uses objects or classes for enum-like patterns, but these are
        better captured as regular classes or constants. Return empty list.
        """
        return []

    def _is_top_level(self, node: Node) -> bool:
        """Check if node is at top level (not nested in class/method)."""
        return self._is_top_level_function(
            node, class_types=["class_declaration", "method_definition"]
        )
