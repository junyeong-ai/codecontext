"""TypeScript-specific optimizations for AST parsing and search."""

import re

from codecontext.parsers.language_optimizers.base import LanguageOptimizer, OptimizationMetadata
from codecontext_core.models.cast_chunk import CASTChunk
from tree_sitter import Node


class TypeScriptOptimizer(LanguageOptimizer):
    """Optimizer for TypeScript-specific constructs and patterns."""

    def optimize_chunk(self, chunk: CASTChunk, ast_node: Node) -> CASTChunk:
        """Apply TypeScript-specific optimizations to a chunk.

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
        """Extract TypeScript-specific features from AST.

        Detects:
        - Decorators (@Component, @Injectable, @Input, @Output)
        - Type annotations (interfaces, type aliases)
        - Generics
        - Async/await patterns
        - Optional chaining (?.)
        - Nullish coalescing (??)
        - Framework patterns (Angular, NestJS, React)

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

        # Find decorators
        decorators = self._find_decorators(ast_node, source_bytes)
        if decorators:
            special_constructs.extend(decorators)
            complexity_factors["decorators"] = len(decorators)
            semantic_tags.append("decorated")

            # Check for specific decorators
            for dec in decorators:
                if any(
                    angular in dec for angular in ["@Component", "@NgModule", "@Directive", "@Pipe"]
                ):
                    semantic_tags.append("angular")
                    semantic_tags.append("component")
                elif any(nest in dec for nest in ["@Injectable", "@Controller", "@Module"]):
                    semantic_tags.append("nestjs")
                    semantic_tags.append("dependency_injection")
                elif any(io in dec for io in ["@Input", "@Output"]):
                    semantic_tags.append("angular_io")
                    semantic_tags.append("component_communication")

        # Find type annotations
        type_annotations = self._find_type_annotations(ast_node, source_bytes)
        if type_annotations:
            special_constructs.append("type_annotations")
            complexity_factors["type_annotations"] = len(type_annotations)
            semantic_tags.append("typed")
            optimization_hints.append("Fully typed with TypeScript")

        # Find interfaces
        if self._has_interfaces(ast_node):
            special_constructs.append("interfaces")
            semantic_tags.append("interface")
            semantic_tags.append("contract")

        # Find generics
        if self._has_generics(ast_node, source_bytes):
            special_constructs.append("generics")
            semantic_tags.append("generic")
            complexity_factors["generics"] = 1

        # Find async/await
        if self._has_async_await(ast_node):
            special_constructs.append("async_await")
            semantic_tags.append("async")
            optimization_hints.append("Asynchronous code")

        # Find optional chaining
        if self._has_optional_chaining(ast_node, source_bytes):
            special_constructs.append("optional_chaining")
            semantic_tags.append("modern_ts")
            optimization_hints.append("Uses optional chaining (?.) for null safety")

        # Find nullish coalescing
        if self._has_nullish_coalescing(ast_node, source_bytes):
            special_constructs.append("nullish_coalescing")
            semantic_tags.append("modern_ts")

        # Find arrow functions
        if self._has_arrow_functions(ast_node):
            special_constructs.append("arrow_functions")
            semantic_tags.append("modern_js")

        # Find promises
        if self._has_promises(ast_node, source_bytes):
            special_constructs.append("promises")
            semantic_tags.append("async")

        # Find template literals
        if self._has_template_literals(ast_node):
            special_constructs.append("template_literals")
            semantic_tags.append("modern_js")

        # Find exception handling
        if self._has_exception_handling(ast_node):
            special_constructs.append("exception_handling")
            semantic_tags.append("error_handling")

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
        """Generate TypeScript-specific search terms.

        Args:
            chunk: The chunk to analyze

        Returns:
            List of additional search terms
        """
        terms = []

        # Add basic TypeScript terms
        if chunk.node_type in ["class_declaration", "interface_declaration"]:
            terms.extend(["typescript class", "ts class", "typescript interface"])
        elif chunk.node_type in ["function_declaration", "method_definition"]:
            terms.extend(["typescript function", "ts function", "typescript method"])

        # Add semantic tags as search terms
        metadata = chunk.language_metadata
        if not metadata:
            return terms

        semantic_tags = metadata.get("semantic_tags", [])

        # Framework-specific terms
        if "angular" in semantic_tags:
            terms.extend(["angular", "component", "angular component"])
        if "nestjs" in semantic_tags:
            terms.extend(["nestjs", "nest framework", "backend"])
        if "component_communication" in semantic_tags:
            terms.extend(["input output", "component props", "data binding"])

        # Pattern-specific terms
        if "async" in semantic_tags:
            terms.extend(["async", "await", "promise", "asynchronous"])
        if "modern_ts" in semantic_tags:
            terms.extend(["modern typescript", "ts4", "ts5"])
        if "typed" in semantic_tags:
            terms.extend(["type safe", "strongly typed", "type checking"])
        if "interface" in semantic_tags:
            terms.extend(["interface", "contract", "type definition"])

        return terms

    def _find_decorators(self, node: Node, source_bytes: bytes) -> list[str]:
        """Find TypeScript decorators in node."""
        decorators = []

        def traverse(n: Node) -> None:
            if n.type == "decorator":
                dec_text = source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="ignore")
                decorators.append(dec_text)
            for child in n.children:
                traverse(child)

        traverse(node)
        return decorators

    def _find_type_annotations(self, node: Node, source_bytes: bytes) -> list[str]:
        """Find type annotations."""
        annotations = []

        def traverse(n: Node) -> None:
            if n.type == "type_annotation":
                ann_text = source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="ignore")
                annotations.append(ann_text)
            for child in n.children:
                traverse(child)

        traverse(node)
        return annotations

    def _has_interfaces(self, node: Node) -> bool:
        """Check if node contains interfaces."""

        def traverse(n: Node) -> bool:
            if n.type == "interface_declaration":
                return True
            return any(traverse(child) for child in n.children)

        return traverse(node)

    def _has_generics(self, node: Node, source_bytes: bytes) -> bool:
        """Check if node uses generics."""
        content = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        # Look for <T>, <T, U>, etc. patterns
        return bool(re.search(r"<\s*[A-Z][a-zA-Z0-9_]*(?:\s*,\s*[A-Z][a-zA-Z0-9_]*)*\s*>", content))

    def _has_async_await(self, node: Node) -> bool:
        """Check if node uses async/await."""

        def traverse(n: Node) -> bool:
            if n.type in ["async", "await_expression"]:
                return True
            return any(traverse(child) for child in n.children)

        return traverse(node)

    def _has_optional_chaining(self, node: Node, source_bytes: bytes) -> bool:
        """Check if node uses optional chaining (?.)."""
        content = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        return "?." in content

    def _has_nullish_coalescing(self, node: Node, source_bytes: bytes) -> bool:
        """Check if node uses nullish coalescing (??)."""
        content = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        return "??" in content

    def _has_arrow_functions(self, node: Node) -> bool:
        """Check if node contains arrow functions."""

        def traverse(n: Node) -> bool:
            if n.type == "arrow_function":
                return True
            return any(traverse(child) for child in n.children)

        return traverse(node)

    def _has_promises(self, node: Node, source_bytes: bytes) -> bool:
        """Check if node uses Promises."""
        content = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        return "Promise<" in content or ".then(" in content or ".catch(" in content

    def _has_template_literals(self, node: Node) -> bool:
        """Check if node uses template literals."""

        def traverse(n: Node) -> bool:
            if n.type == "template_string":
                return True
            return any(traverse(child) for child in n.children)

        return traverse(node)

    def _has_exception_handling(self, node: Node) -> bool:
        """Check if node has exception handling."""

        def traverse(n: Node) -> bool:
            if n.type in ["try_statement", "catch_clause", "throw_statement"]:
                return True
            return any(traverse(child) for child in n.children)

        return traverse(node)

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
                "switch_statement",
                "catch_clause",
                "ternary_expression",
            ]:
                complexity += 1
            # Logical operators
            elif n.type == "binary_expression":
                for child in n.children:
                    if child.type in ["&&", "||"]:
                        complexity += 1

            for child in n.children:
                traverse(child)

        traverse(node)
        return complexity
