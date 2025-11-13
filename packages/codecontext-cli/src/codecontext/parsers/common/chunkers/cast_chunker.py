"""cAST-style structure-preserving code chunker."""

from pathlib import Path
from typing import Any, cast

from codecontext_core.models.cast_chunk import CASTChunk
from tree_sitter import Node

from codecontext.parsers.common.chunkers.base import BaseChunker, ChunkingConfig


class CASTChunker(BaseChunker):
    """Structure-preserving AST chunking following cAST methodology.

    This chunker ensures each chunk is a semantically complete unit that
    can be understood independently while preserving relationships.
    """

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        """Initialize cAST chunker with configuration."""
        super().__init__(config)
        self.context_cache: dict[str, tuple[list[str], str | None]] = {}

    def chunk_file(self, file_path: Path, source_code: str, language: str) -> list[CASTChunk]:
        """Chunk an entire file into semantic units using cAST approach.

        Args:
            file_path: Path to the source file
            source_code: Complete source code content
            language: Programming language

        Returns:
            List of CASTChunk objects representing the file
        """
        try:
            # Parse file with tree-sitter
            import tree_sitter_language_pack as tslp

            parser = tslp.get_parser(cast(Any, language))
            tree = parser.parse(source_code.encode())
            root = tree.root_node

            # Extract file-level context (imports, module docstring)
            imports, module_doc = self._extract_file_context(root, source_code.encode())
            self.context_cache[str(file_path)] = (imports, module_doc)

            # Recursively chunk the AST
            chunks = self._chunk_node_recursive(
                node=root,
                source_bytes=source_code.encode(),
                file_path=file_path,
                language=language,
                parent_chunk_id=None,
                depth=0,
            )

        except (RuntimeError, UnicodeDecodeError, ValueError):
            # Fallback to line-based chunking if AST parsing fails
            from codecontext.parsers.common.chunkers.base import FallbackChunker

            fallback = FallbackChunker(self.config)
            return fallback.chunk_file(file_path, source_code, language)
        else:
            return chunks

    def chunk_ast_node(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        language: str,
        parent_chunk_id: str | None = None,
    ) -> list[CASTChunk]:
        """Chunk a specific AST node preserving semantic structure.

        Args:
            node: Tree-sitter AST node to chunk
            source_bytes: Original source code as bytes
            file_path: Path to the source file
            language: Programming language
            parent_chunk_id: ID of parent chunk if nested

        Returns:
            List of CASTChunk objects for this node
        """
        return self._chunk_node_recursive(
            node=node,
            source_bytes=source_bytes,
            file_path=file_path,
            language=language,
            parent_chunk_id=parent_chunk_id,
            depth=0,
        )

    def _chunk_node_recursive(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        language: str,
        parent_chunk_id: str | None,
        depth: int,
    ) -> list[CASTChunk]:
        """Recursively chunk AST nodes preserving structure."""
        chunks = []

        # Check if this node should be a chunk
        if self._should_create_chunk(node, language):
            chunk = self._create_chunk_from_node(
                node=node,
                source_bytes=source_bytes,
                file_path=file_path,
                language=language,
                parent_chunk_id=parent_chunk_id,
            )

            # Check if chunk needs to be split (with language-specific logic)
            if self.should_split_node(node, source_bytes, language):
                # Split large nodes at natural boundaries
                sub_chunks = self._split_large_node(
                    node=node,
                    source_bytes=source_bytes,
                    file_path=file_path,
                    language=language,
                    parent_chunk=chunk,
                )
                chunks.extend(sub_chunks)
            else:
                chunks.append(chunk)
                parent_chunk_id = chunk.deterministic_id

        # Process children
        for child in node.children:
            if child.is_named:
                child_chunks = self._chunk_node_recursive(
                    node=child,
                    source_bytes=source_bytes,
                    file_path=file_path,
                    language=language,
                    parent_chunk_id=parent_chunk_id,
                    depth=depth + 1,
                )
                chunks.extend(child_chunks)

        return chunks

    def _should_create_chunk(self, node: Node, language: str) -> bool:
        """Determine if a node should become a chunk."""
        # Language-agnostic chunk-worthy node types
        chunk_types = {
            "function_definition",
            "function_declaration",
            "method_definition",
            "method_declaration",
            "class_definition",
            "class_declaration",
            "interface_declaration",
            "interface_definition",
            "module",
            "namespace",
            "constructor_definition",
            "constructor_declaration",
        }

        # Language-specific additions
        if language == "python":
            chunk_types.update({"decorated_definition", "async_function_definition"})
        elif language in ["java", "kotlin"]:
            chunk_types.update({"annotation_type_declaration", "enum_declaration"})
        elif language in ["javascript", "typescript"]:
            chunk_types.update({"arrow_function", "function_expression", "class_expression"})

        return node.type in chunk_types

    def _create_chunk_from_node(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        language: str,
        parent_chunk_id: str | None,
    ) -> CASTChunk:
        """Create a CASTChunk from an AST node with context."""
        # Extract raw content
        raw_content = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")

        # Get context from cache or extract
        imports, parent_def = self._get_context_for_node(
            node=node, source_bytes=source_bytes, file_path=file_path
        )

        # Build content with context
        content_parts = []
        if imports:
            content_parts.extend(imports)
            content_parts.append("")  # Empty line separator

        if parent_def and not self._is_top_level(node):
            content_parts.append(parent_def)
            content_parts.append("    ...")  # Indicate parent body omitted
            content_parts.append("")

        content_parts.append(raw_content)
        content = "\n".join(content_parts)

        # Extract metadata
        name = self._extract_node_name(node, source_bytes)
        signature = self._extract_signature(node, source_bytes, language)
        docstring = self._extract_docstring(node, source_bytes, language)

        # Get line information
        start_line, end_line = self.extract_line_info(source_bytes, node.start_byte, node.end_byte)

        # Extract language metadata
        language_metadata = self._extract_language_metadata(node, source_bytes, language)

        # Create chunk
        chunk = CASTChunk(
            deterministic_id=self.generate_chunk_id(file_path, node.start_byte, node.end_byte),
            file_path=file_path,
            language=language,
            content=content,
            raw_content=raw_content,
            imports=imports,
            parent_definition=parent_def,
            start_line=start_line,
            end_line=end_line,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            token_count=self.estimate_tokens(content),
            node_type=node.type,
            name=name,
            signature=signature,
            docstring=docstring,
            parent_chunk_id=parent_chunk_id,
            language_metadata=language_metadata,
        )

        # Enhance search keywords using Language Optimizer
        search_keywords = self._enhance_search_keywords(chunk, language)
        if search_keywords:
            chunk.search_keywords = search_keywords

        return chunk

    def should_split_node(
        self, node: Node, source_bytes: bytes, language: str | None = None
    ) -> bool:
        """Determine if a node should be split using language-specific logic.

        Override of BaseChunker.should_split_node with optimizer integration.

        If language_specific optimization is enabled and an optimizer exists,
        uses the optimizer's language-aware split logic. Otherwise falls back
        to the base implementation (token count threshold).

        Args:
            node: Tree-sitter AST node
            source_bytes: Original source code as bytes
            language: Programming language (optional)

        Returns:
            True if the node should be split into smaller chunks
        """
        # Use language-specific optimizer if available and enabled
        if self.config.language_specific and language:
            from codecontext.parsers.language_optimizers.optimizer_factory import get_optimizer

            optimizer = get_optimizer(language)
            if optimizer:
                # Language-aware split decision
                return optimizer.should_split_chunk(node, source_bytes)

        # Fallback to token-based split logic
        return super().should_split_node(node, source_bytes)

    def _split_large_node(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        language: str,
        parent_chunk: CASTChunk,
    ) -> list[CASTChunk]:
        """Split a large node at natural boundaries."""
        chunks = [parent_chunk]  # Keep the parent as overview

        # Find natural split points (methods in a class, statements in a function)
        split_points = self._find_split_points(node, language)

        for child in node.children:
            if child.is_named and child.type in split_points:
                # Create a chunk for each split point
                child_chunk = self._create_chunk_from_node(
                    node=child,
                    source_bytes=source_bytes,
                    file_path=file_path,
                    language=language,
                    parent_chunk_id=parent_chunk.deterministic_id,
                )
                chunks.append(child_chunk)
                parent_chunk.child_chunk_ids.append(child_chunk.deterministic_id)

        return chunks

    def _find_split_points(self, node: Node, _language: str) -> set[str]:
        """Find natural split points for a node type."""
        if node.type in ["class_definition", "class_declaration"]:
            return {"method_definition", "method_declaration", "function_definition"}
        elif node.type in ["function_definition", "function_declaration"]:
            # Split at major statement blocks
            return {"if_statement", "for_statement", "while_statement", "try_statement"}
        else:
            return set()

    def _extract_file_context(
        self, root: Node, source_bytes: bytes
    ) -> tuple[list[str], str | None]:
        """Extract file-level context (imports and module docstring)."""
        imports = []
        module_doc = None

        for child in root.children:
            if child.type in [
                "import_statement",
                "import_from_statement",
                "import_declaration",
                "using_directive",
                "include",
            ]:
                import_text = source_bytes[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
                imports.append(import_text)
            elif child.type == "expression_statement" and not module_doc:
                # Check for module docstring (first expression statement)
                first_child = child.children[0] if child.children else None
                if first_child and first_child.type == "string":
                    module_doc = source_bytes[first_child.start_byte : first_child.end_byte].decode(
                        "utf-8", errors="ignore"
                    )

        return imports, module_doc

    def _get_context_for_node(
        self, node: Node, source_bytes: bytes, file_path: Path
    ) -> tuple[list[str], str | None]:
        """Get relevant context for a node."""
        # Get cached file context
        imports, _ = self.context_cache.get(str(file_path), ([], None))

        # Find parent definition if nested
        parent_def = None
        parent = node.parent
        while parent:
            if parent.type in ["class_definition", "class_declaration"]:
                # Extract class definition line
                for child in parent.children:
                    if child.type in ["identifier", "class_name"]:
                        class_name = source_bytes[child.start_byte : child.end_byte].decode(
                            "utf-8", errors="ignore"
                        )
                        parent_def = f"class {class_name}:"
                        break
                break
            parent = parent.parent

        # Filter imports to only relevant ones
        relevant_imports = self._filter_relevant_imports(
            imports, source_bytes[node.start_byte : node.end_byte]
        )

        return relevant_imports, parent_def

    def _filter_relevant_imports(self, imports: list[str], node_content: bytes) -> list[str]:
        """Filter imports to only those referenced in the node."""
        node_text = node_content.decode("utf-8", errors="ignore")
        relevant = []

        for imp in imports:
            # Simple heuristic: check if any imported name appears in node
            if "import" in imp:
                parts = imp.replace("import", "").replace("from", "").strip().split()
                for part in parts:
                    clean_part = part.strip("(),")
                    if clean_part and clean_part in node_text:
                        relevant.append(imp)
                        break

        return relevant[:10]  # Limit to prevent context explosion

    def _is_top_level(self, node: Node) -> bool:
        """Check if node is at top level of file."""
        parent = node.parent
        return parent is None or parent.type in ["module", "source_file", "program"]

    def _extract_node_name(self, node: Node, source_bytes: bytes) -> str:
        """Extract the name of a node (function name, class name, etc.)."""
        for child in node.children:
            if child.type in ["identifier", "name", "property_identifier"]:
                return source_bytes[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
        return ""

    def _extract_signature(self, node: Node, source_bytes: bytes, _language: str) -> str | None:
        """Extract function/method signature."""
        if node.type not in [
            "function_definition",
            "function_declaration",
            "method_definition",
            "method_declaration",
        ]:
            return None

        # Find parameters node
        for child in node.children:
            if child.type in ["parameters", "parameter_list", "formal_parameters"]:
                params = source_bytes[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
                name = self._extract_node_name(node, source_bytes)
                return f"{name}{params}"

        return None

    def _extract_docstring(self, node: Node, source_bytes: bytes, language: str) -> str | None:
        """Extract docstring from a node."""
        if language == "python":
            # Look for first expression statement with string
            for child in node.children:
                if child.type in ["block", "body"]:
                    for stmt in child.children:
                        if stmt.type == "expression_statement":
                            for expr in stmt.children:
                                if expr.type == "string":
                                    return source_bytes[expr.start_byte : expr.end_byte].decode(
                                        "utf-8", errors="ignore"
                                    )
                            break
        elif language in ["java", "kotlin", "javascript", "typescript"]:
            # Look for comment before node
            prev = node.prev_sibling
            if prev and prev.type == "comment":
                return source_bytes[prev.start_byte : prev.end_byte].decode(
                    "utf-8", errors="ignore"
                )

        return None

    def _extract_language_metadata(
        self, node: Node, source_bytes: bytes, language: str
    ) -> dict[str, Any]:
        """Extract language-specific metadata using Language Optimizer.

        Leverages language-specific optimizers for deep semantic analysis:
        - Python: async/await, decorators, type hints, comprehensions, frameworks
        - Kotlin: data classes, coroutines, null safety, sealed classes
        - Falls back to basic extraction for unsupported languages

        Returns:
            Dictionary with semantic tags, complexity, and language features
        """
        from codecontext.parsers.language_optimizers.optimizer_factory import get_optimizer

        # Try language-specific optimizer first
        optimizer = get_optimizer(language)
        if optimizer:
            optimization_result = optimizer.extract_language_features(node, source_bytes)

            # Convert OptimizationMetadata to dict for storage
            metadata: dict[str, Any] = {}

            if optimization_result.semantic_tags:
                metadata["semantic_tags"] = optimization_result.semantic_tags

            if optimization_result.special_constructs:
                metadata["special_constructs"] = optimization_result.special_constructs

            if optimization_result.complexity_factors:
                metadata["complexity_factors"] = optimization_result.complexity_factors
                # Extract cyclomatic complexity as primary score
                if "cyclomatic" in optimization_result.complexity_factors:
                    metadata["complexity_score"] = optimization_result.complexity_factors[
                        "cyclomatic"
                    ]

            if optimization_result.optimization_hints:
                metadata["optimization_hints"] = optimization_result.optimization_hints

            return metadata

        # Fallback to basic extraction for languages without optimizer
        return self._extract_basic_metadata(node, source_bytes, language)

    def _extract_basic_metadata(
        self, node: Node, source_bytes: bytes, language: str
    ) -> dict[str, Any]:
        """Basic metadata extraction for languages without optimizer.

        This is the fallback when no language-specific optimizer exists.
        Provides minimal but consistent metadata across all languages.
        """
        metadata = {}

        if language == "python":
            # Extract decorators
            decorators = []
            for child in node.children:
                if child.type == "decorator":
                    dec_text = source_bytes[child.start_byte : child.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                    decorators.append(dec_text)
            if decorators:
                metadata["decorators"] = decorators

        elif language in ["java", "kotlin"]:
            # Extract annotations
            annotations = []
            for child in node.children:
                if child.type in ["annotation", "modifier"]:
                    ann_text = source_bytes[child.start_byte : child.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                    annotations.append(ann_text)
            if annotations:
                metadata["annotations"] = annotations

        elif language == "typescript":
            # Extract type annotations
            type_annotations = []
            for child in node.children:
                if child.type == "type_annotation":
                    type_text = source_bytes[child.start_byte : child.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                    type_annotations.append(type_text)
            if type_annotations:
                metadata["type_annotations"] = type_annotations

        return metadata

    def _enhance_search_keywords(self, chunk: CASTChunk, language: str) -> list[str]:
        """Generate enhanced search keywords using Language Optimizer.

        Leverages language-specific optimizers to generate semantic search keywords:
        - Framework detection (numpy, pandas, django, asyncio, etc.)
        - Pattern keywords (async, coroutine, dataclass, sealed, etc.)
        - Architecture patterns (factory, singleton, repository, etc.)

        Args:
            chunk: The CASTChunk to enhance
            language: Programming language

        Returns:
            List of enhanced search keywords
        """
        from codecontext.parsers.language_optimizers.optimizer_factory import get_optimizer

        optimizer = get_optimizer(language)
        if optimizer:
            return optimizer.enhance_search_terms(chunk)

        # No enhancement for languages without optimizer
        return []
