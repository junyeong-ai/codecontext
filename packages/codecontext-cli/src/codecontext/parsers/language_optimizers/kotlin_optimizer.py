"""Kotlin-specific optimizations for code analysis."""

from codecontext.parsers.language_optimizers.base import LanguageOptimizer, OptimizationMetadata
from codecontext_core.models.cast_chunk import CASTChunk
from tree_sitter import Node


class KotlinOptimizer(LanguageOptimizer):
    """Optimizer for Kotlin-specific constructs and patterns."""

    def optimize_chunk(self, chunk: CASTChunk, ast_node: Node) -> CASTChunk:
        """Apply Kotlin-specific optimizations."""
        # Extract Kotlin features
        metadata = self.extract_language_features(ast_node, chunk.raw_content.encode())

        # Enhance chunk metadata
        if chunk.language_metadata is None:
            chunk.language_metadata = {}

        chunk.language_metadata.update(
            {
                "special_constructs": metadata.special_constructs,
                "complexity_factors": metadata.complexity_factors,
                "semantic_tags": metadata.semantic_tags,
            }
        )

        # Add Kotlin-specific search terms
        additional_terms = self.enhance_search_terms(chunk)
        if chunk.search_keywords is None:
            chunk.search_keywords = []
        chunk.search_keywords.extend(additional_terms)

        return chunk

    def extract_language_features(
        self, ast_node: Node, source_bytes: bytes
    ) -> OptimizationMetadata:
        """Extract Kotlin-specific features."""
        special_constructs = []
        complexity_factors = {}
        optimization_hints = []
        semantic_tags = []

        # Check for data classes
        if self._is_data_class(ast_node, source_bytes):
            special_constructs.append("data_class")
            semantic_tags.append("data_class")
            optimization_hints.append("Data class with auto-generated methods")

        # Check for sealed classes
        if self._is_sealed_class(ast_node, source_bytes):
            special_constructs.append("sealed_class")
            semantic_tags.append("sealed")
            optimization_hints.append("Sealed class hierarchy")

        # Find coroutines and suspend functions
        if self._has_coroutines(ast_node, source_bytes):
            special_constructs.append("coroutines")
            semantic_tags.append("async")
            semantic_tags.append("coroutines")
            optimization_hints.append("Uses Kotlin coroutines")

        # Find extension functions
        if self._is_extension_function(ast_node, source_bytes):
            special_constructs.append("extension_function")
            semantic_tags.append("extension")
            optimization_hints.append("Extension function")

        # Find companion objects
        if self._has_companion_object(ast_node, source_bytes):
            special_constructs.append("companion_object")
            semantic_tags.append("companion")

        # Find inline functions
        if self._is_inline_function(ast_node, source_bytes):
            special_constructs.append("inline_function")
            semantic_tags.append("inline")
            optimization_hints.append("Inline function for performance")

        # Find lambda expressions
        lambdas = self._count_lambdas(ast_node)
        if lambdas > 0:
            special_constructs.append("lambdas")
            complexity_factors["lambdas"] = lambdas
            semantic_tags.append("functional")

        # Find null safety features
        null_safety = self._analyze_null_safety(ast_node, source_bytes)
        if null_safety["safe_calls"] > 0:
            special_constructs.append("null_safety")
            complexity_factors["null_safety"] = null_safety["safe_calls"]
            semantic_tags.append("null_safe")

        # Find when expressions
        when_count = self._count_when_expressions(ast_node)
        if when_count > 0:
            special_constructs.append("when_expression")
            complexity_factors["when_expressions"] = when_count
            semantic_tags.append("pattern_matching")

        # Find delegates
        if self._has_delegates(ast_node, source_bytes):
            special_constructs.append("delegates")
            semantic_tags.append("delegated")

        # Find annotations
        annotations = self._find_annotations(ast_node, source_bytes)
        if annotations:
            special_constructs.extend(annotations)
            complexity_factors["annotations"] = len(annotations)

            # Check for specific annotations
            for ann in annotations:
                if "@Test" in ann or "@ParameterizedTest" in ann:
                    semantic_tags.append("test")
                elif "@Composable" in ann:
                    semantic_tags.append("compose")
                    semantic_tags.append("ui")
                elif "@Entity" in ann:
                    semantic_tags.append("database")
                    semantic_tags.append("entity")

        # Check for object declarations (singletons)
        if self._is_object_declaration(ast_node):
            special_constructs.append("object_declaration")
            semantic_tags.append("singleton")

        # Calculate complexity
        complexity = self._calculate_kotlin_complexity(ast_node)
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
        """Generate Kotlin-specific search terms."""
        terms = []

        # Add Kotlin-specific keywords
        if chunk.node_type == "class_declaration":
            terms.extend(["kotlin class", "kt class"])
        elif chunk.node_type == "function_declaration":
            terms.extend(["kotlin function", "kt function", "fun"])

        # Add terms based on metadata
        metadata = chunk.language_metadata or {}

        if "data_class" in metadata.get("semantic_tags", []):
            terms.extend(["data class", "kotlin data", "auto equals hashcode"])

        if "coroutines" in metadata.get("semantic_tags", []):
            terms.extend(["coroutine", "suspend", "async", "await", "flow"])

        if "sealed" in metadata.get("semantic_tags", []):
            terms.extend(["sealed class", "sealed hierarchy", "algebraic data type"])

        if "extension" in metadata.get("semantic_tags", []):
            terms.extend(["extension function", "extend", "kotlin extension"])

        if "compose" in metadata.get("semantic_tags", []):
            terms.extend(["compose", "composable", "jetpack compose", "ui"])

        if "test" in metadata.get("semantic_tags", []):
            terms.extend(["test", "junit", "kotlin test"])

        if "singleton" in metadata.get("semantic_tags", []):
            terms.extend(["singleton", "object", "kotlin object"])

        # Add import-based terms
        if chunk.imports:
            for imp in chunk.imports:
                if "kotlinx.coroutines" in imp:
                    terms.extend(["coroutines", "async", "flow"])
                elif "androidx.compose" in imp:
                    terms.extend(["compose", "android", "ui"])
                elif "ktor" in imp:
                    terms.extend(["ktor", "server", "api"])
                elif "junit" in imp:
                    terms.extend(["junit", "test", "testing"])

        return list(set(terms))  # Remove duplicates

    def calculate_complexity_score(self, ast_node: Node, source_bytes: bytes) -> int:
        """Calculate Kotlin-specific complexity score."""
        score = 1

        # Base complexity
        complexity = self._calculate_kotlin_complexity(ast_node)
        if complexity > 20:
            score += 3
        elif complexity > 10:
            score += 2
        elif complexity > 5:
            score += 1

        # Add for coroutines
        if self._has_coroutines(ast_node, source_bytes):
            score += 2

        # Add for sealed classes
        if self._is_sealed_class(ast_node, source_bytes):
            score += 1

        # Add for when expressions
        when_count = self._count_when_expressions(ast_node)
        if when_count > 3:
            score += 2
        elif when_count > 0:
            score += 1

        # Add for lambdas
        lambda_count = self._count_lambdas(ast_node)
        if lambda_count > 5:
            score += 2
        elif lambda_count > 2:
            score += 1

        # Add for delegates
        if self._has_delegates(ast_node, source_bytes):
            score += 1

        return min(score, 10)

    # Helper methods for feature detection

    def _is_data_class(self, node: Node, source_bytes: bytes) -> bool:
        """Check if class is a data class."""
        if node.type == "class_declaration":
            for child in node.children:
                if child.type == "modifiers":
                    mods = source_bytes[child.start_byte : child.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                    if "data" in mods:
                        return True
        return False

    def _is_sealed_class(self, node: Node, source_bytes: bytes) -> bool:
        """Check if class is sealed."""
        if node.type == "class_declaration":
            for child in node.children:
                if child.type == "modifiers":
                    mods = source_bytes[child.start_byte : child.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                    if "sealed" in mods:
                        return True
        return False

    def _has_coroutines(self, node: Node, source_bytes: bytes) -> bool:
        """Check if code uses coroutines."""
        text = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        return "suspend" in text or "async" in text or "launch" in text or "flow" in text.lower()

    def _is_extension_function(self, node: Node, _source_bytes: bytes) -> bool:
        """Check if function is an extension function."""
        if node.type == "function_declaration":
            for child in node.children:
                # Kotlin tree-sitter uses "receiver_type" not "function_receiver"
                if child.type == "receiver_type":
                    return True
        return False

    def _has_companion_object(self, node: Node, source_bytes: bytes) -> bool:
        """Check if class has companion object."""
        if node.type != "class_declaration":
            return False

        for child in node.children:
            if child.type == "companion_object":
                return True
            if child.type in ["class_body", "body"] and self._has_companion_in_body(
                child, source_bytes
            ):
                return True
        return False

    def _has_companion_in_body(self, body_node: Node, source_bytes: bytes) -> bool:
        """Check if class body contains companion object."""
        for member in body_node.children:
            if member.type == "companion_object":
                return True
            if member.type == "object_declaration" and self._is_companion_object_decl(
                member, source_bytes
            ):
                return True
        return False

    def _is_companion_object_decl(self, obj_node: Node, source_bytes: bytes) -> bool:
        """Check if object declaration has companion modifier."""
        for child in obj_node.children:
            if child.type == "modifiers":
                mods = source_bytes[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
                if "companion" in mods:
                    return True
        return False

    def _is_inline_function(self, node: Node, source_bytes: bytes) -> bool:
        """Check if function is inline."""
        if node.type == "function_declaration":
            for child in node.children:
                if child.type == "modifiers":
                    mods = source_bytes[child.start_byte : child.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                    if "inline" in mods:
                        return True
        return False

    def _count_lambdas(self, node: Node) -> int:
        """Count lambda expressions."""
        count = 0

        def traverse(n: Node) -> None:
            nonlocal count
            if n.type == "lambda_literal":
                count += 1
            for child in n.children:
                if child.is_named:
                    traverse(child)

        traverse(node)
        return count

    def _analyze_null_safety(self, node: Node, source_bytes: bytes) -> dict[str, int]:
        """Analyze null safety features."""
        text = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")

        return {
            "safe_calls": text.count("?."),
            "elvis_operators": text.count("?:"),
            "not_null_assertions": text.count("!!"),
            "nullable_types": text.count("?") - text.count("?.") - text.count("?:"),
        }

    def _count_when_expressions(self, node: Node) -> int:
        """Count when expressions."""
        count = 0

        def traverse(n: Node) -> None:
            nonlocal count
            if n.type == "when_expression":
                count += 1
            for child in n.children:
                if child.is_named:
                    traverse(child)

        traverse(node)
        return count

    def _has_delegates(self, node: Node, source_bytes: bytes) -> bool:
        """Check if code uses delegates."""
        text = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        return " by " in text and ("lazy" in text or "observable" in text or "Delegates" in text)

    def _find_annotations(self, node: Node, source_bytes: bytes) -> list[str]:
        """Find all annotations."""
        annotations = []

        def traverse(n: Node) -> None:
            if n.type in ["annotation", "modifier"]:
                text = source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="ignore")
                if text.startswith("@"):
                    annotations.append(text)
            for child in n.children:
                if child.is_named:
                    traverse(child)

        traverse(node)
        return annotations

    def _is_object_declaration(self, node: Node) -> bool:
        """Check if node is an object declaration."""
        node_type: str = str(node.type) if hasattr(node, "type") else ""
        return node_type == "object_declaration"

    def _calculate_kotlin_complexity(self, node: Node) -> int:
        """Calculate Kotlin cyclomatic complexity."""
        complexity = 1

        decision_points = [
            "if_expression",
            "else",
            "when_expression",
            "when_entry",
            "for_statement",
            "while_statement",
            "do_while_statement",
            "try_expression",
            "catch_block",
            "elvis_expression",  # ?:
            "disjunction_expression",  # ||
            "conjunction_expression",  # &&
        ]

        def traverse(n: Node) -> None:
            nonlocal complexity
            if n.type in decision_points:
                complexity += 1
            for child in n.children:
                if child.is_named:
                    traverse(child)

        traverse(node)
        return complexity
