"""Python-specific optimizations for code analysis."""

from codecontext.parsers.language_optimizers.base import LanguageOptimizer, OptimizationMetadata
from codecontext_core.models.cast_chunk import CASTChunk
from tree_sitter import Node


class PythonOptimizer(LanguageOptimizer):
    """Optimizer for Python-specific constructs and patterns."""

    def optimize_chunk(self, chunk: CASTChunk, ast_node: Node) -> CASTChunk:
        """Apply Python-specific optimizations."""
        # Extract Python features
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

        # Add Python-specific search terms
        additional_terms = self.enhance_search_terms(chunk)
        if chunk.search_keywords is None:
            chunk.search_keywords = []
        chunk.search_keywords.extend(additional_terms)

        return chunk

    def extract_language_features(
        self, ast_node: Node, source_bytes: bytes
    ) -> OptimizationMetadata:
        """Extract Python-specific features."""
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
                if "@property" in dec:
                    semantic_tags.append("property")
                elif "@staticmethod" in dec:
                    semantic_tags.append("static_method")
                elif "@classmethod" in dec:
                    semantic_tags.append("class_method")
                elif "@dataclass" in dec:
                    semantic_tags.append("dataclass")
                elif "@pytest" in dec or "@test" in dec:
                    semantic_tags.append("test")
                elif "@async" in dec or "async" in dec:
                    semantic_tags.append("async")

        # Find comprehensions
        comprehensions = self._find_comprehensions(ast_node)
        if comprehensions:
            special_constructs.extend(comprehensions)
            complexity_factors["comprehensions"] = len(comprehensions)
            semantic_tags.append("functional")

        # Find generators
        if self._has_generators(ast_node):
            special_constructs.append("generator")
            semantic_tags.append("generator")
            optimization_hints.append("Uses generators for memory efficiency")

        # Find context managers
        if self._has_context_managers(ast_node):
            special_constructs.append("context_manager")
            semantic_tags.append("resource_management")

        # Find type hints
        type_hints = self._find_type_hints(ast_node, source_bytes)
        if type_hints:
            special_constructs.append("type_hints")
            complexity_factors["type_hints"] = len(type_hints)
            semantic_tags.append("typed")
            optimization_hints.append("Fully typed with type hints")

        # Find async/await
        if self._has_async_await(ast_node):
            special_constructs.append("async_await")
            semantic_tags.append("async")
            optimization_hints.append("Asynchronous code")

        # Find magic methods
        magic_methods = self._find_magic_methods(ast_node, source_bytes)
        if magic_methods:
            special_constructs.extend(magic_methods)
            semantic_tags.append("magic_methods")

            # Categorize magic methods
            if "__init__" in magic_methods:
                semantic_tags.append("constructor")
            if "__str__" in magic_methods or "__repr__" in magic_methods:
                semantic_tags.append("representation")
            if "__enter__" in magic_methods and "__exit__" in magic_methods:
                semantic_tags.append("context_manager")
            if "__iter__" in magic_methods or "__next__" in magic_methods:
                semantic_tags.append("iterator")

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
        """Generate Python-specific search terms."""
        terms = []

        # Add Python-specific keywords
        if chunk.node_type == "class_definition":
            terms.extend(["python class", "py class"])
        elif chunk.node_type == "function_definition":
            terms.extend(["python function", "py function", "def"])

        # Add terms based on metadata
        metadata = chunk.language_metadata or {}

        if "dataclass" in metadata.get("semantic_tags", []):
            terms.extend(["dataclass", "data class", "@dataclass"])

        if "async" in metadata.get("semantic_tags", []):
            terms.extend(["async", "await", "coroutine", "asyncio"])

        if "test" in metadata.get("semantic_tags", []):
            terms.extend(["test", "unit test", "pytest", "unittest"])

        if "generator" in metadata.get("semantic_tags", []):
            terms.extend(["generator", "yield", "iterator"])

        if "property" in metadata.get("semantic_tags", []):
            terms.extend(["property", "getter", "setter", "@property"])

        # Add import-based terms
        if chunk.imports:
            for imp in chunk.imports:
                if "numpy" in imp:
                    terms.extend(["numpy", "array", "numerical"])
                elif "pandas" in imp:
                    terms.extend(["pandas", "dataframe", "data analysis"])
                elif "django" in imp:
                    terms.extend(["django", "web", "orm"])
                elif "flask" in imp:
                    terms.extend(["flask", "web", "api"])
                elif "pytest" in imp:
                    terms.extend(["pytest", "test", "testing"])
                elif "asyncio" in imp:
                    terms.extend(["async", "asyncio", "concurrent"])

        return list(set(terms))  # Remove duplicates

    def calculate_complexity_score(self, ast_node: Node, source_bytes: bytes) -> int:
        """Calculate Python-specific complexity score."""
        score = 1

        # Base complexity from cyclomatic complexity
        cyclomatic = self._calculate_cyclomatic_complexity(ast_node)
        if cyclomatic > 20:
            score += 3
        elif cyclomatic > 10:
            score += 2
        elif cyclomatic > 5:
            score += 1

        # Add for decorators
        decorators = self._find_decorators(ast_node, source_bytes)
        if len(decorators) > 3:
            score += 2
        elif len(decorators) > 0:
            score += 1

        # Add for comprehensions
        if self._find_comprehensions(ast_node):
            score += 1

        # Add for async
        if self._has_async_await(ast_node):
            score += 1

        # Add for generators
        if self._has_generators(ast_node):
            score += 1

        # Add for metaclasses
        if self._has_metaclass(ast_node, source_bytes):
            score += 2

        return min(score, 10)

    # Helper methods for feature detection

    def _find_decorators(self, node: Node, source_bytes: bytes) -> list[str]:
        """Find all decorators in the node."""
        decorators = []
        for child in node.children:
            if child.type == "decorator":
                dec_text = source_bytes[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
                decorators.append(dec_text)
        return decorators

    def _find_comprehensions(self, node: Node) -> list[str]:
        """Find all comprehensions in the node."""
        comprehensions = []
        comp_types = [
            "list_comprehension",
            "dictionary_comprehension",
            "set_comprehension",
            "generator_expression",
        ]

        def traverse(n: Node) -> None:
            if n.type in comp_types:
                comprehensions.append(n.type.replace("_", " "))
            for child in n.children:
                if child.is_named:
                    traverse(child)

        traverse(node)
        return comprehensions

    def _has_generators(self, node: Node) -> bool:
        """Check if node contains generators."""

        def traverse(n: Node) -> bool:
            if n.type == "yield_expression" or n.type == "yield":
                return True
            return any(child.is_named and traverse(child) for child in n.children)

        return traverse(node)

    def _has_context_managers(self, node: Node) -> bool:
        """Check if node contains context managers."""

        def traverse(n: Node) -> bool:
            if n.type == "with_statement":
                return True
            return any(child.is_named and traverse(child) for child in n.children)

        return traverse(node)

    def _find_type_hints(self, node: Node, source_bytes: bytes) -> list[str]:
        """Find all type hints in the node."""
        type_hints = []

        def traverse(n: Node) -> None:
            if n.type in ["type", "type_annotation"]:
                hint_text = source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="ignore")
                type_hints.append(hint_text)
            for child in n.children:
                if child.is_named:
                    traverse(child)

        traverse(node)
        return type_hints

    def _has_async_await(self, node: Node) -> bool:
        """Check if node contains async/await."""
        if node.type in [
            "async_function_definition",
            "async_for_statement",
            "async_with_statement",
        ]:
            return True

        def traverse(n: Node) -> bool:
            if n.type in ["await_expression", "await"]:
                return True
            return any(child.is_named and traverse(child) for child in n.children)

        return traverse(node)

    def _find_magic_methods(self, node: Node, source_bytes: bytes) -> list[str]:
        """Find all magic methods in a class."""
        magic_methods = []

        if node.type == "class_definition":
            for child in node.children:
                if child.type in ["body", "block"]:
                    for member in child.children:
                        if member.type == "function_definition":
                            for name_child in member.children:
                                if name_child.type == "identifier":
                                    name = source_bytes[
                                        name_child.start_byte : name_child.end_byte
                                    ].decode("utf-8", errors="ignore")
                                    if name.startswith("__") and name.endswith("__"):
                                        magic_methods.append(name)
                                    break

        return magic_methods

    def _has_exception_handling(self, node: Node) -> bool:
        """Check if node contains exception handling."""

        def traverse(n: Node) -> bool:
            if n.type in ["try_statement", "except_clause", "raise_statement"]:
                return True
            return any(child.is_named and traverse(child) for child in n.children)

        return traverse(node)

    def _has_metaclass(self, node: Node, source_bytes: bytes) -> bool:
        """Check if class uses metaclass."""
        if node.type == "class_definition":
            for child in node.children:
                if child.type == "argument_list":
                    args_text = source_bytes[child.start_byte : child.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                    if "metaclass=" in args_text:
                        return True
        return False

    def _calculate_cyclomatic_complexity(self, node: Node) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity

        decision_points = [
            "if_statement",
            "elif_clause",
            "else_clause",
            "for_statement",
            "while_statement",
            "except_clause",
            "case_clause",  # match/case in Python 3.10+
            "conditional_expression",  # ternary operator
            "boolean_operator",  # and/or
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
