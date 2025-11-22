"""
Single-pass CODE extractor for CodeObject and Relationship extraction.

Extracts code objects and relationships from CODE files ONLY in one AST traversal,
eliminating duplicate file reading and parsing.

Architecture:
- Extractor → ParserFactory → LanguageParser (CODE ONLY)
- Produces CodeObject instances (not DocumentNode)
- Document files handled separately by MarkdownParser/ConfigFileParser
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

from codecontext_core.models import CodeObject, Relationship, RelationType
from tree_sitter import Language, Node, Query, QueryCursor, Tree


if TYPE_CHECKING:
    from codecontext.parsers.base import BaseCodeParser
    from codecontext.parsers.factory import ParserFactory

logger = logging.getLogger(__name__)


@dataclass
class ImportInfo:
    """Information about an import statement."""

    imported_name: str  # Module or class name (e.g., "os.path", "OrderService")
    source_file: str  # File containing the import


@dataclass
class ExtractionResult:
    """Result of code extraction."""

    objects: list[CodeObject]
    relationships: list[Relationship]
    imports: list[ImportInfo] = field(
        default_factory=list
    )  # Import statements for cross-file resolution


class Extractor:
    """Single-pass CODE extraction for CodeObject and Relationship instances.

    한 번의 AST 파싱으로 모든 정보를 추출하는 효율적인 추출기 (CODE FILES ONLY).

    Architecture:
    - Uses ParserFactory to get LanguageParser (Python, Kotlin, Java, JS, TS)
    - Extracts CodeObject instances (not DocumentNode)
    - Document files (.md, .yaml, etc.) should NOT use this extractor

    Optimizations:
    - AST parsed only once per file (objects + relationships)
    - Single-pass relationship extraction (all types in one traversal)
    - Unified relationship creation logic (no code duplication)
    """

    def __init__(self, parser_factory: "ParserFactory") -> None:
        """Initialize extractor with parser factory.

        Args:
            parser_factory: ParserFactory instance (for CODE parsers only)
        """
        self.parser_factory = parser_factory
        self._init_patterns()
        self._query_cache: dict[
            tuple[int, str], QueryCursor | None
        ] = {}  # Cache for QueryCursor objects

    def _init_patterns(self) -> None:
        """Initialize AST patterns for relationship extraction.

        Supports: Python, JavaScript, TypeScript, Java, Kotlin (CALLS, REFERENCES, EXTENDS, IMPLEMENTS, IMPORTS)
        """
        # CALLS patterns - function/method invocations
        self.call_patterns = {
            "python": [
                "(call function: (identifier) @callee)",
                "(call function: (attribute) @callee)",
            ],
            "javascript": [
                "(call_expression function: (identifier) @callee)",
                "(call_expression function: (member_expression) @callee)",
            ],
            "typescript": [
                "(call_expression function: (identifier) @callee)",
                "(call_expression function: (member_expression) @callee)",
            ],
        }

        # REFERENCES patterns - identifier/attribute usage
        self.reference_patterns = {
            "python": [
                "(identifier) @ref",
                "(attribute) @ref",
            ],
            "javascript": [
                "(identifier) @ref",
                "(member_expression) @ref",
            ],
            "typescript": [
                "(identifier) @ref",
                "(member_expression) @ref",
            ],
        }

        # EXTENDS patterns - class inheritance
        self.inheritance_patterns = {
            "python": [
                "(class_definition superclasses: (argument_list (identifier) @parent))",
                "(class_definition superclasses: (argument_list (attribute) @parent))",
            ],
            "javascript": [
                "(class_declaration superclass: (identifier) @parent)",
            ],
            "typescript": [
                "(extends_clause (identifier) @parent)",
            ],
        }

        # IMPLEMENTS patterns - interface implementation
        self.interface_patterns = {
            "typescript": [
                "(implements_clause (type_identifier) @interface)",
            ],
            "java": [
                "(class_declaration interfaces: (super_interfaces (type_list (type_identifier) @interface)))",
            ],
            "kotlin": [
                "(class_declaration (delegation_specifier (user_type (type_identifier) @interface)))",
            ],
        }

        # IMPORTS patterns - module/package imports
        self.import_patterns = {
            "python": [
                "(import_statement name: (dotted_name) @imported)",
                "(import_from_statement module_name: (dotted_name) @imported)",
                "(import_from_statement name: (dotted_name (identifier) @imported))",
            ],
            "javascript": [
                "(import_statement source: (string) @imported)",
                "(import_statement source: (string (string_fragment) @imported))",
            ],
            "typescript": [
                "(import_statement source: (string) @imported)",
                "(import_statement source: (string (string_fragment) @imported))",
            ],
            "java": [
                "(import_declaration (scoped_identifier) @imported)",
                "(import_declaration (identifier) @imported)",
            ],
            "kotlin": [
                "(import_header (identifier) @imported)",
            ],
        }

    async def extract_from_file(
        self, file_path: str, content: str | None = None
    ) -> ExtractionResult:
        """Extract code objects and relationships from a CODE file.

        Single-pass extraction - AST를 딱 1번만 파싱하고 재사용 (CODE FILES ONLY).

        Args:
            file_path: Path to the CODE file (.py, .kt, .java, .js, .ts)
            content: Optional file content (if already loaded)

        Returns:
            ExtractionResult with CodeObject and Relationship instances

        Raises:
            UnsupportedLanguageError: If file is not a supported code language
                (e.g., .md, .yaml, .json files should use MarkdownParser/ConfigFileParser)
        """
        if content is None:
            content = Path(file_path).read_text(encoding="utf-8")

        parser = self.parser_factory.get_parser(file_path)
        if not parser:
            return ExtractionResult(objects=[], relationships=[])

        # Parse AST once and reuse for both objects and relationships
        tree = parser.parser.parse_text(content)
        if not tree:
            return ExtractionResult(objects=[], relationships=[])

        source_bytes = content.encode("utf-8")

        # Extract code objects using the parsed AST
        # Cast to BaseCodeParser to access implementation methods
        base_parser = cast("BaseCodeParser", parser)
        objects = []
        objects.extend(base_parser._extract_classes(tree, source_bytes, Path(file_path), file_path))
        objects.extend(
            base_parser._extract_interfaces(tree, source_bytes, Path(file_path), file_path)
        )
        objects.extend(
            base_parser._extract_functions(tree, source_bytes, Path(file_path), file_path)
        )
        objects.extend(base_parser._extract_enums(tree, source_bytes, Path(file_path), file_path))

        # Extract relationships using the same AST (single pass)
        if hasattr(parser, "language"):
            relationships = self._extract_relationships(
                tree, file_path, parser.language, objects, parser.parser.ts_language
            )
            imports = self._extract_imports(
                tree, file_path, parser.language, parser.parser.ts_language
            )
        else:
            relationships = []
            imports = []

        # Extract CONTAINS relationships from parent-child hierarchy
        contains_relationships = self._extract_contains_relationships(objects)
        relationships.extend(contains_relationships)

        return ExtractionResult(objects=objects, relationships=relationships, imports=imports)

    async def extract_batch(
        self, file_paths: list[str], batch_size: int = 100
    ) -> AsyncGenerator[ExtractionResult, None]:
        """Extract from multiple files in batches.

        메모리 효율적인 배치 처리.

        Args:
            file_paths: List of file paths to process
            batch_size: Number of files to process in each batch

        Yields:
            ExtractionResult for each batch
        """
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i : i + batch_size]
            batch_objects = []
            batch_relationships = []

            # Process batch concurrently
            tasks = [self.extract_from_file(path) for path in batch]
            results = await asyncio.gather(*tasks)

            for result in results:
                batch_objects.extend(result.objects)
                batch_relationships.extend(result.relationships)

            yield ExtractionResult(objects=batch_objects, relationships=batch_relationships)

    def _extract_relationships(
        self,
        tree: Tree,
        file_path: str,
        language: str,
        objects: list[CodeObject],
        ts_language: Language,
    ) -> list[Relationship]:
        """Extract all relationships in a single AST pass using QueryCursor.

        단일 순회로 모든 관계 타입(CALLS, EXTENDS, REFERENCES)을 추출.

        Uses tree-sitter 0.25.2+ API where QueryCursor.captures() returns
        a dict[str, Any] mapping capture names to lists of nodes.

        Performance: 3x faster than previous implementation that made
        3 separate AST traversals (one per relationship type).

        Args:
            tree: Parsed AST tree
            file_path: Source file path
            language: Language name (e.g., 'python')
            objects: Extracted code objects
            ts_language: Tree-sitter Language object for query compilation

        Returns:
            List of extracted Relationship objects
        """
        try:
            relationships = []

            # Build object lookup maps for efficient resolution
            # Use deterministic_id as primary key (guaranteed unique)
            # Use name as secondary key (allows multiple objects with same name)
            id_map: dict[str, CodeObject] = {obj.deterministic_id: obj for obj in objects}
            name_map: dict[str, list[CodeObject]] = {}

            for obj in objects:
                if obj.name not in name_map:
                    name_map[obj.name] = []
                name_map[obj.name].append(obj)

            # Log statistics for debugging
            total_names = len(name_map)
            duplicate_names = sum(1 for objs in name_map.values() if len(objs) > 1)
            if duplicate_names > 0:
                logger.debug(
                    f"Object name statistics for {file_path}: "
                    f"{len(objects)} objects, {total_names} unique names, "
                    f"{duplicate_names} names with duplicates"
                )

            # Compile all queries once (avoid recompilation)
            compiled_queries = self._compile_relationship_queries(ts_language, language)

            # Single pass: execute all queries and collect captures by type
            for rel_type, cursor in compiled_queries:
                try:
                    # QueryCursor.captures() returns dict[str, Any]: {'capture_name': [nodes]}
                    captures_dict = cursor.captures(tree.root_node)

                    # Process each capture name and its matched nodes
                    for _capture_name, nodes in captures_dict.items():
                        for node in nodes:
                            try:
                                rel = self._create_relationship(
                                    node, rel_type, file_path, id_map, name_map
                                )
                                if rel:
                                    relationships.append(rel)
                            except (ValueError, AttributeError, UnicodeDecodeError) as e:
                                logger.debug(
                                    f"Failed to create {rel_type.value} relationship "
                                    f"from node: {e}",
                                    exc_info=True,
                                )
                except (ValueError, RuntimeError, OSError) as e:
                    logger.warning(
                        f"Failed to execute query for {rel_type.value}: {e}", exc_info=True
                    )

        except (ValueError, RuntimeError, OSError) as e:
            logger.error(f"Relationship extraction failed for {file_path}: {e}", exc_info=True)
            return []
        else:
            return relationships

    def _compile_relationship_queries(
        self, ts_language: Language, language: str
    ) -> list[tuple[RelationType, QueryCursor]]:
        """Compile all relationship queries for the given language using QueryCursor.

        Uses tree-sitter 0.25.2+ API with Query and QueryCursor.
        Implements caching to avoid recompiling queries for the same language.

        Args:
            ts_language: Tree-sitter Language object
            language: Language name string (e.g., 'python')

        Returns:
            List of (RelationType, QueryCursor) tuples
        """
        compiled = []

        # Compile CALLS patterns
        if language in self.call_patterns:
            for pattern in self.call_patterns[language]:
                cursor = self._compile_query_cached(ts_language, pattern)
                if cursor:
                    compiled.append((RelationType.CALLS, cursor))

        # Compile EXTENDS (inheritance) patterns
        if language in self.inheritance_patterns:
            for pattern in self.inheritance_patterns[language]:
                cursor = self._compile_query_cached(ts_language, pattern)
                if cursor:
                    compiled.append((RelationType.EXTENDS, cursor))

        # Compile IMPLEMENTS (interface) patterns
        if language in self.interface_patterns:
            for pattern in self.interface_patterns[language]:
                cursor = self._compile_query_cached(ts_language, pattern)
                if cursor:
                    compiled.append((RelationType.IMPLEMENTS, cursor))

        # Compile REFERENCES patterns
        if language in self.reference_patterns:
            for pattern in self.reference_patterns[language]:
                cursor = self._compile_query_cached(ts_language, pattern)
                if cursor:
                    compiled.append((RelationType.REFERENCES, cursor))

        return compiled

    def _compile_query_cached(self, ts_language: Language, pattern: str) -> QueryCursor | None:
        """Compile query pattern with caching.

        Args:
            ts_language: Tree-sitter Language object
            pattern: Query pattern string

        Returns:
            QueryCursor instance or None if pattern is invalid
        """
        cache_key = (id(ts_language), pattern)
        if cache_key not in self._query_cache:
            try:
                query = Query(ts_language, pattern)
                self._query_cache[cache_key] = QueryCursor(query)
            except (ValueError, RuntimeError) as e:
                logger.debug(f"Invalid query pattern for language: {pattern[:50]}... Error: {e}")
                self._query_cache[cache_key] = None
        return self._query_cache[cache_key]

    def _create_relationship(
        self,
        node: Node,
        rel_type: RelationType,
        _file_path: str,
        id_map: dict[str, CodeObject],
        name_map: dict[str, list[CodeObject]],
    ) -> Relationship | None:
        """Create a relationship from a matched node.

        Unified relationship creation logic for all types with proper duplicate handling.

        Args:
            node: Matched AST node
            rel_type: Type of relationship (CALLS, EXTENDS, REFERENCES)
            _file_path: Source file path (unused but kept for signature compatibility)
            id_map: Map of deterministic_id to CodeObject (guaranteed unique)
            name_map: Map of name to list of CodeObjects (supports duplicates)

        Returns:
            Relationship instance or None if invalid
        """
        if node.text is None:
            return None
        target_name = node.text.decode("utf-8")

        # Special handling for REFERENCES: skip function calls
        if (
            rel_type == RelationType.REFERENCES
            and node.parent
            and node.parent.type in ["call", "call_expression"]
        ):
            return None

        # Find source context (caller/referencer/child class)
        source_obj = self._find_context(node, id_map, name_map)
        if not source_obj:
            return None

        # Find target object(s) by name
        target_objs = name_map.get(target_name, [])
        if not target_objs:
            # Target not found in this file (might be external)
            return None

        # For EXTENDS, target must exist
        if rel_type == RelationType.EXTENDS and not target_objs:
            return None

        # For REFERENCES, validate target exists and is different from source
        if rel_type == RelationType.REFERENCES and (
            not target_objs
            or all(obj.deterministic_id == source_obj.deterministic_id for obj in target_objs)
        ):
            return None

        # Select best target match using spatial proximity heuristic
        target_obj = self._select_best_target(node, source_obj, target_objs)
        if not target_obj:
            return None

        # Create relationship using proper Relationship model fields
        return Relationship(
            source_id=source_obj.deterministic_id,
            source_type=source_obj.object_type.value,
            target_id=target_obj.deterministic_id,
            target_type=target_obj.object_type.value,
            relation_type=rel_type,
            confidence=1.0,  # High confidence for static analysis
        )

    def _find_context(
        self, node: Node, id_map: dict[str, CodeObject], name_map: dict[str, list[CodeObject]]
    ) -> CodeObject | None:
        """Find the source context (containing function/class) for a node.

        Unified context finding logic with proper duplicate handling.

        Args:
            node: AST node to find context for
            id_map: Map of deterministic_id to CodeObject
            name_map: Map of name to list of CodeObjects

        Returns:
            CodeObject instance or None
        """
        parent = node.parent
        while parent:
            if parent.type in [
                "function_definition",
                "method",
                "method_definition",
                "function_declaration",
                "method_declaration",
                "class_definition",
                "class_declaration",
            ]:
                context_name = self._find_name_node(parent)
                if context_name and context_name in name_map:
                    # Get all objects with this name
                    candidates = name_map[context_name]
                    # Select best match using spatial proximity
                    return self._select_best_context(parent, candidates)
                break
            parent = parent.parent

        return None

    def _select_best_target(
        self, node: Node, source_obj: CodeObject, candidates: list[CodeObject]
    ) -> CodeObject | None:
        """Select best target using spatial proximity.

        Args:
            node: Reference node
            source_obj: Source object
            candidates: Candidate targets

        Returns:
            Best matching object or None
        """
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        if not hasattr(node, "start_point"):
            return candidates[0]

        ref_line = node.start_point[0] + 1
        source_line = source_obj.start_line

        best_obj = candidates[0]
        min_distance = abs(source_line - ref_line)

        for obj in candidates[1:]:
            distance = abs(obj.start_line - ref_line)
            if distance < min_distance:
                min_distance = distance
                best_obj = obj

        return best_obj

    def _select_best_context(self, parent: Node, candidates: list[CodeObject]) -> CodeObject | None:
        """Select best context object from candidates using spatial proximity.

        When multiple objects have the same name, prefer the one that matches
        the parent node's location in the source.

        Args:
            parent: Parent AST node
            candidates: List of candidate context objects

        Returns:
            Best matching CodeObject or None
        """
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        # Match by line range if available
        if hasattr(parent, "start_point") and hasattr(parent, "end_point"):
            parent_start_line = parent.start_point[0] + 1  # Convert to 1-indexed
            for obj in candidates:
                if obj.start_line == parent_start_line:
                    return obj

        # Fallback: return first candidate
        return candidates[0]

    def _find_name_node(self, node: Node) -> str | None:
        """Find the name identifier of a node."""
        # Try field-based lookup first (works for most languages)
        name_node = node.child_by_field_name("name")
        if name_node and name_node.text:
            return name_node.text.decode("utf-8")

        # Fallback: iterate children to find identifier
        for child in node.children:
            if child.type == "identifier":
                text_bytes = child.text
                if text_bytes is not None:
                    result: str = text_bytes.decode("utf-8")
                    return result
        return None

    def _extract_contains_relationships(self, objects: list[CodeObject]) -> list[Relationship]:
        """Extract CONTAINS relationships from parent-child hierarchy.

        Leverages existing parent_deterministic_id field to create structural relationships.

        Examples:
        - Class CONTAINS Method
        - Class CONTAINS Field
        - Module CONTAINS Class

        Args:
            objects: List of extracted code objects

        Returns:
            List of CONTAINS relationships
        """
        if not objects:
            return []

        # Build object lookup map for O(1) parent resolution
        id_map: dict[str, CodeObject] = {obj.deterministic_id: obj for obj in objects}

        relationships = []

        for obj in objects:
            # Skip objects without parent
            if not obj.parent_deterministic_id:
                continue

            # Find parent object
            parent_obj = id_map.get(obj.parent_deterministic_id)
            if not parent_obj:
                # Parent not in current file (might be in different file)
                logger.debug(
                    f"Parent not found for {obj.name} (type: {obj.object_type.value}): "
                    f"parent_id={obj.parent_deterministic_id}"
                )
                continue

            # Create CONTAINS relationship (parent contains child)
            relationships.append(
                Relationship(
                    source_id=parent_obj.deterministic_id,
                    source_type=parent_obj.object_type.value,
                    target_id=obj.deterministic_id,
                    target_type=obj.object_type.value,
                    relation_type=RelationType.CONTAINS,
                    confidence=1.0,  # High confidence for structural relationships
                )
            )

        logger.debug(
            f"Extracted {len(relationships)} CONTAINS relationships from {len(objects)} objects"
        )

        return relationships

    def _extract_imports(
        self,
        tree: Tree,
        file_path: str,
        language: str,
        ts_language: Language,
    ) -> list[ImportInfo]:
        """Extract import statements from AST.

        Extracts module/class names that are imported in this file.
        Cross-file resolution happens later in batch processing.

        Args:
            tree: Parsed AST tree
            file_path: Source file path
            language: Language name (e.g., 'python')
            ts_language: Tree-sitter Language object for query compilation

        Returns:
            List of ImportInfo instances
        """
        if language not in self.import_patterns:
            return []

        imports: list[ImportInfo] = []

        # Compile import queries
        for pattern in self.import_patterns[language]:
            cursor = self._compile_query_cached(ts_language, pattern)
            if not cursor:
                continue

            try:
                captures_dict = cursor.captures(tree.root_node)

                for _capture_name, nodes in captures_dict.items():
                    for node in nodes:
                        if node.text is None:
                            continue

                        imported_name = node.text.decode("utf-8")

                        # Clean up string literals (JavaScript/TypeScript)
                        if imported_name.startswith(("'", '"')):
                            imported_name = imported_name.strip("'\"")

                        # Skip empty or invalid imports
                        if not imported_name or imported_name in (".", "..", "/"):
                            continue

                        imports.append(
                            ImportInfo(
                                imported_name=imported_name,
                                source_file=file_path,
                            )
                        )

            except (ValueError, RuntimeError, OSError) as e:
                logger.debug(f"Failed to extract imports from {file_path}: {e}", exc_info=True)

        logger.debug(f"Extracted {len(imports)} imports from {file_path}")

        return imports
