"""Base class and interface for language-specific optimizations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from codecontext_core.models.cast_chunk import CASTChunk
from tree_sitter import Node


@dataclass
class OptimizationMetadata:
    """Metadata from language-specific optimizations."""

    special_constructs: list[str]
    """Special language constructs found."""

    complexity_factors: dict[str, int]
    """Factors contributing to complexity."""

    optimization_hints: list[str]
    """Hints for better indexing/search."""

    semantic_tags: list[str]
    """Semantic tags for improved search."""


class LanguageOptimizer(ABC):
    """Abstract base class for language-specific optimizations."""

    @abstractmethod
    def optimize_chunk(self, chunk: CASTChunk, ast_node: Node) -> CASTChunk:
        """
        Apply language-specific optimizations to a chunk.

        Args:
            chunk: The chunk to optimize
            ast_node: The AST node for the chunk

        Returns:
            Optimized chunk with enhanced metadata
        """
        pass

    @abstractmethod
    def extract_language_features(
        self, ast_node: Node, source_bytes: bytes
    ) -> OptimizationMetadata:
        """
        Extract language-specific features from AST.

        Args:
            ast_node: The AST node to analyze
            source_bytes: Source code as bytes

        Returns:
            Optimization metadata
        """
        pass

    @abstractmethod
    def enhance_search_terms(self, chunk: CASTChunk) -> list[str]:
        """
        Generate additional search terms based on language patterns.

        Args:
            chunk: The chunk to analyze

        Returns:
            List of additional search terms
        """
        pass

    def should_split_chunk(self, ast_node: Node, source_bytes: bytes) -> bool:
        """
        Determine if a chunk should be split based on language-specific rules.

        Args:
            ast_node: The AST node
            source_bytes: Source code as bytes

        Returns:
            True if the chunk should be split
        """
        # Default implementation - can be overridden
        text = source_bytes[ast_node.start_byte : ast_node.end_byte].decode(
            "utf-8", errors="ignore"
        )
        line_count = text.count("\n")
        return line_count > 50  # Split if more than 50 lines

    def calculate_complexity_score(self, _ast_node: Node, _source_bytes: bytes) -> int:
        """
        Calculate complexity score based on language-specific metrics.

        Args:
            ast_node: The AST node
            source_bytes: Source code as bytes

        Returns:
            Complexity score (1-10)
        """
        # Default implementation - can be overridden
        return 1
