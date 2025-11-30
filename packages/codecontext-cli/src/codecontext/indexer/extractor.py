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
    imported_name: str
    source_file: str


@dataclass
class ExtractionResult:
    objects: list[CodeObject]
    relationships: list[Relationship]
    imports: list[ImportInfo] = field(default_factory=list)


class Extractor:
    def __init__(self, parser_factory: "ParserFactory") -> None:
        self.parser_factory = parser_factory
        self._init_patterns()
        self._query_cache: dict[tuple[int, str], QueryCursor | None] = {}

    def _init_patterns(self) -> None:
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
        if content is None:
            content = Path(file_path).read_text(encoding="utf-8")

        parser = self.parser_factory.get_parser(file_path)
        if not parser:
            return ExtractionResult(objects=[], relationships=[])

        tree = parser.parser.parse_text(content)
        if not tree:
            return ExtractionResult(objects=[], relationships=[])

        source_bytes = content.encode("utf-8")
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

        relationships.extend(self._extract_contains_relationships(objects))

        return ExtractionResult(objects=objects, relationships=relationships, imports=imports)

    async def extract_batch(
        self, file_paths: list[str], batch_size: int = 100
    ) -> AsyncGenerator[ExtractionResult, None]:
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i : i + batch_size]
            batch_objects = []
            batch_relationships = []

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
        try:
            relationships = []
            id_map: dict[str, CodeObject] = {obj.deterministic_id: obj for obj in objects}
            name_map: dict[str, list[CodeObject]] = {}

            for obj in objects:
                if obj.name not in name_map:
                    name_map[obj.name] = []
                name_map[obj.name].append(obj)

            compiled_queries = self._compile_relationship_queries(ts_language, language)

            for rel_type, cursor in compiled_queries:
                try:
                    captures_dict = cursor.captures(tree.root_node)

                    for _capture_name, nodes in captures_dict.items():
                        for node in nodes:
                            try:
                                rel = self._create_relationship(node, rel_type, id_map, name_map)
                                if rel:
                                    relationships.append(rel)
                            except (ValueError, AttributeError, UnicodeDecodeError) as e:
                                logger.debug(
                                    f"Failed to create {rel_type.value} relationship: {e}",
                                    exc_info=True,
                                )
                except (ValueError, RuntimeError, OSError) as e:
                    logger.warning(f"Query execution failed for {rel_type.value}: {e}")

        except (ValueError, RuntimeError, OSError) as e:
            logger.error(f"Relationship extraction failed for {file_path}: {e}")
            return []
        else:
            return relationships

    def _compile_relationship_queries(
        self, ts_language: Language, language: str
    ) -> list[tuple[RelationType, QueryCursor]]:
        compiled = []

        pattern_map = [
            (self.call_patterns, RelationType.CALLS),
            (self.inheritance_patterns, RelationType.EXTENDS),
            (self.interface_patterns, RelationType.IMPLEMENTS),
            (self.reference_patterns, RelationType.REFERENCES),
        ]

        for patterns, rel_type in pattern_map:
            if language in patterns:
                for pattern in patterns[language]:
                    cursor = self._compile_query_cached(ts_language, pattern)
                    if cursor:
                        compiled.append((rel_type, cursor))

        return compiled

    def _compile_query_cached(self, ts_language: Language, pattern: str) -> QueryCursor | None:
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
        id_map: dict[str, CodeObject],
        name_map: dict[str, list[CodeObject]],
    ) -> Relationship | None:
        if node.text is None:
            return None
        target_name = node.text.decode("utf-8")

        if (
            rel_type == RelationType.REFERENCES
            and node.parent
            and node.parent.type in ["call", "call_expression"]
        ):
            return None

        source_obj = self._find_context(node, id_map, name_map)
        if not source_obj:
            return None

        target_objs = name_map.get(target_name, [])
        if not target_objs:
            return None

        if rel_type == RelationType.REFERENCES and all(
            obj.deterministic_id == source_obj.deterministic_id for obj in target_objs
        ):
            return None

        target_obj = self._select_best_target(node, source_obj, target_objs)
        if not target_obj:
            return None

        return Relationship(
            source_id=source_obj.deterministic_id,
            source_name=source_obj.name,
            source_type=source_obj.object_type.value,
            source_file=source_obj.relative_path,
            source_line=source_obj.start_line,
            target_id=target_obj.deterministic_id,
            target_name=target_obj.name,
            target_type=target_obj.object_type.value,
            target_file=target_obj.relative_path,
            target_line=target_obj.start_line,
            relation_type=rel_type,
        )

    def _find_context(
        self, node: Node, id_map: dict[str, CodeObject], name_map: dict[str, list[CodeObject]]
    ) -> CodeObject | None:
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
                    return self._select_best_context(parent, name_map[context_name])
                break
            parent = parent.parent

        return None

    def _select_best_target(
        self, node: Node, source_obj: CodeObject, candidates: list[CodeObject]
    ) -> CodeObject | None:
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        if not hasattr(node, "start_point"):
            return candidates[0]

        ref_line = node.start_point[0] + 1

        best_obj = candidates[0]
        min_distance = abs(source_obj.start_line - ref_line)

        for obj in candidates[1:]:
            distance = abs(obj.start_line - ref_line)
            if distance < min_distance:
                min_distance = distance
                best_obj = obj

        return best_obj

    def _select_best_context(self, parent: Node, candidates: list[CodeObject]) -> CodeObject | None:
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        if hasattr(parent, "start_point"):
            parent_start_line = parent.start_point[0] + 1
            for obj in candidates:
                if obj.start_line == parent_start_line:
                    return obj

        return candidates[0]

    def _find_name_node(self, node: Node) -> str | None:
        name_node = node.child_by_field_name("name")
        if name_node and name_node.text:
            return name_node.text.decode("utf-8")

        for child in node.children:
            if child.type == "identifier" and child.text is not None:
                return child.text.decode("utf-8")
        return None

    def _extract_contains_relationships(self, objects: list[CodeObject]) -> list[Relationship]:
        if not objects:
            return []

        id_map: dict[str, CodeObject] = {obj.deterministic_id: obj for obj in objects}
        relationships = []

        for obj in objects:
            if not obj.parent_deterministic_id:
                continue

            parent_obj = id_map.get(obj.parent_deterministic_id)
            if not parent_obj:
                continue

            relationships.append(
                Relationship(
                    source_id=parent_obj.deterministic_id,
                    source_name=parent_obj.name,
                    source_type=parent_obj.object_type.value,
                    source_file=parent_obj.relative_path,
                    source_line=parent_obj.start_line,
                    target_id=obj.deterministic_id,
                    target_name=obj.name,
                    target_type=obj.object_type.value,
                    target_file=obj.relative_path,
                    target_line=obj.start_line,
                    relation_type=RelationType.CONTAINS,
                )
            )

        return relationships

    def _extract_imports(
        self,
        tree: Tree,
        file_path: str,
        language: str,
        ts_language: Language,
    ) -> list[ImportInfo]:
        if language not in self.import_patterns:
            return []

        imports: list[ImportInfo] = []

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

                        if imported_name.startswith(("'", '"')):
                            imported_name = imported_name.strip("'\"")

                        if not imported_name or imported_name in (".", "..", "/"):
                            continue

                        imports.append(
                            ImportInfo(imported_name=imported_name, source_file=file_path)
                        )

            except (ValueError, RuntimeError, OSError) as e:
                logger.debug(f"Failed to extract imports from {file_path}: {e}")

        return imports
