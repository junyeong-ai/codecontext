"""Java-specific optimizations for AST parsing and search."""

import re

from codecontext.parsers.language_optimizers.base import LanguageOptimizer, OptimizationMetadata
from codecontext_core.models.cast_chunk import CASTChunk
from tree_sitter import Node


class JavaOptimizer(LanguageOptimizer):
    """Optimizer for Java-specific constructs and patterns."""

    def optimize_chunk(self, chunk: CASTChunk, ast_node: Node) -> CASTChunk:
        """Apply Java-specific optimizations to a chunk.

        Args:
            chunk: The chunk to optimize
            ast_node: The AST node for the chunk

        Returns:
            Optimized chunk with enhanced metadata
        """
        # Extract language features
        metadata = self.extract_language_features(ast_node, chunk.raw_content.encode())

        # Update chunk metadata
        chunk.language_metadata.update(
            {
                "semantic_tags": metadata.semantic_tags,
                "special_constructs": metadata.special_constructs,
                "complexity_factors": metadata.complexity_factors,
            }
        )

        # Add search keywords
        search_keywords = self.enhance_search_terms(chunk)
        if search_keywords:
            if chunk.search_keywords is None:
                chunk.search_keywords = []
            chunk.search_keywords.extend(search_keywords)

        return chunk

    def extract_language_features(
        self, ast_node: Node, source_bytes: bytes
    ) -> OptimizationMetadata:
        """Extract Java-specific features from AST.

        Detects:
        - Annotations (@Override, @Test, @Entity, @Autowired, etc.)
        - Streams and lambda expressions
        - Try-with-resources
        - Generics usage
        - Static imports
        - Framework patterns (Spring, JUnit, JPA)

        Args:
            ast_node: The AST node to analyze
            source_bytes: Source code as bytes

        Returns:
            Optimization metadata
        """
        special_constructs = []
        complexity_factors = {}
        optimization_hints = []
        semantic_tags = []

        # Find annotations
        annotations = self._find_annotations(ast_node, source_bytes)
        if annotations:
            special_constructs.extend(annotations)
            complexity_factors["annotations"] = len(annotations)
            semantic_tags.append("annotated")

            # Check for specific annotation types
            for ann in annotations:
                if "@Override" in ann:
                    semantic_tags.append("override")
                elif any(test in ann for test in ["@Test", "@ParameterizedTest", "@RepeatedTest"]):
                    semantic_tags.append("test")
                    semantic_tags.append("junit")
                elif any(jpa in ann for jpa in ["@Entity", "@Table", "@Column", "@ManyToOne"]):
                    semantic_tags.append("jpa")
                    semantic_tags.append("persistence")
                elif any(
                    spring in ann
                    for spring in ["@Autowired", "@Service", "@Controller", "@Component"]
                ):
                    semantic_tags.append("spring")
                    semantic_tags.append("dependency_injection")
                elif "@Deprecated" in ann:
                    semantic_tags.append("deprecated")

        # Find lambda expressions
        if self._has_lambda_expressions(ast_node):
            special_constructs.append("lambda_expression")
            semantic_tags.append("functional")
            optimization_hints.append("Uses functional programming patterns")

        # Find stream API usage
        if self._has_stream_api(ast_node, source_bytes):
            special_constructs.append("stream_api")
            semantic_tags.append("streams")
            semantic_tags.append("functional")
            optimization_hints.append("Uses Java Stream API")

        # Find try-with-resources
        if self._has_try_with_resources(ast_node):
            special_constructs.append("try_with_resources")
            semantic_tags.append("resource_management")
            optimization_hints.append("Uses automatic resource management")

        # Find generics
        if self._has_generics(ast_node, source_bytes):
            special_constructs.append("generics")
            semantic_tags.append("generic")
            complexity_factors["generics"] = 1

        # Find static imports
        static_imports = self._find_static_imports(ast_node, source_bytes)
        if static_imports:
            special_constructs.append("static_imports")
            complexity_factors["static_imports"] = len(static_imports)

        # Find exception handling
        if self._has_exception_handling(ast_node):
            special_constructs.append("exception_handling")
            semantic_tags.append("error_handling")

        # Find synchronized blocks/methods
        if self._has_synchronization(ast_node, source_bytes):
            special_constructs.append("synchronization")
            semantic_tags.append("concurrent")
            semantic_tags.append("thread_safe")

        # Calculate cyclomatic complexity
        complexity = self._calculate_cyclomatic_complexity(ast_node)
        if complexity > 10:
            complexity_factors["cyclomatic"] = complexity
            optimization_hints.append(f"High complexity ({complexity})")

        return OptimizationMetadata(
            special_constructs=special_constructs,
            complexity_factors=complexity_factors,
            optimization_hints=optimization_hints,
            semantic_tags=semantic_tags,
        )

    def enhance_search_terms(self, chunk: CASTChunk) -> list[str]:
        """Generate Java-specific search terms.

        Args:
            chunk: The chunk to analyze

        Returns:
            List of additional search terms
        """
        terms = []

        # Add basic Java terms
        if chunk.node_type in ["class_declaration", "interface_declaration"]:
            terms.extend(["java class", "java interface"])
        elif chunk.node_type in ["method_declaration", "constructor_declaration"]:
            terms.extend(["java method", "java function"])

        # Add semantic tags as search terms
        metadata = chunk.language_metadata
        if not metadata:
            return terms

        semantic_tags = metadata.get("semantic_tags", [])

        # Framework-specific terms
        if "spring" in semantic_tags:
            terms.extend(["spring framework", "spring boot", "dependency injection"])
        if "junit" in semantic_tags:
            terms.extend(["unit test", "junit test", "testing"])
        if "jpa" in semantic_tags:
            terms.extend(["jpa", "hibernate", "database", "orm"])

        # Pattern-specific terms
        if "functional" in semantic_tags:
            terms.extend(["functional programming", "lambda", "stream"])
        if "concurrent" in semantic_tags:
            terms.extend(["multithreading", "concurrency", "synchronized"])
        if "generic" in semantic_tags:
            terms.extend(["generics", "type parameter", "parameterized"])

        return terms

    def _find_annotations(self, node: Node, source_bytes: bytes) -> list[str]:
        """Find Java annotations in node."""
        annotations = []

        def traverse(n: Node) -> None:
            if n.type == "marker_annotation" or n.type == "annotation":
                ann_text = source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="ignore")
                annotations.append(ann_text)
            for child in n.children:
                traverse(child)

        traverse(node)
        return annotations

    def _has_lambda_expressions(self, node: Node) -> bool:
        """Check if node contains lambda expressions."""

        def traverse(n: Node) -> bool:
            if n.type == "lambda_expression":
                return True
            return any(traverse(child) for child in n.children)

        return traverse(node)

    def _has_stream_api(self, node: Node, source_bytes: bytes) -> bool:
        """Check if node uses Java Stream API."""
        content = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        stream_methods = [".stream()", ".filter(", ".map(", ".collect(", ".forEach(", ".reduce("]
        return any(method in content for method in stream_methods)

    def _has_try_with_resources(self, node: Node) -> bool:
        """Check if node contains try-with-resources statement."""

        def traverse(n: Node) -> bool:
            if n.type == "try_with_resources_statement":
                return True
            return any(traverse(child) for child in n.children)

        return traverse(node)

    def _has_generics(self, node: Node, source_bytes: bytes) -> bool:
        """Check if node uses generics."""
        content = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        # Simple heuristic: look for <...> patterns
        return bool(re.search(r"<\s*[A-Z][a-zA-Z0-9_]*(?:\s*,\s*[A-Z][a-zA-Z0-9_]*)*\s*>", content))

    def _find_static_imports(self, node: Node, source_bytes: bytes) -> list[str]:
        """Find static import statements."""
        static_imports = []

        def traverse(n: Node) -> None:
            if n.type == "import_declaration":
                import_text = source_bytes[n.start_byte : n.end_byte].decode(
                    "utf-8", errors="ignore"
                )
                if "static" in import_text:
                    static_imports.append(import_text)
            for child in n.children:
                traverse(child)

        traverse(node)
        return static_imports

    def _has_exception_handling(self, node: Node) -> bool:
        """Check if node has exception handling."""

        def traverse(n: Node) -> bool:
            if n.type in ["try_statement", "catch_clause", "throw_statement"]:
                return True
            return any(traverse(child) for child in n.children)

        return traverse(node)

    def _has_synchronization(self, node: Node, source_bytes: bytes) -> bool:
        """Check if node has synchronized blocks/methods."""
        content = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        return "synchronized" in content

    def _calculate_cyclomatic_complexity(self, node: Node) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity

        def traverse(n: Node) -> None:
            nonlocal complexity
            # Control flow constructs
            if n.type in [
                "if_statement",
                "while_statement",
                "for_statement",
                "switch_expression",
                "catch_clause",
                "ternary_expression",
            ]:
                complexity += 1
            # Logical operators (each adds a branch)
            elif n.type in ["binary_expression"]:
                # Check for && or ||
                for child in n.children:
                    if child.type in ["&&", "||"]:
                        complexity += 1

            for child in n.children:
                traverse(child)

        traverse(node)
        return complexity
