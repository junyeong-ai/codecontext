"""Tree-sitter based AST parser with comprehensive optimization support.

This module provides an optimized Tree-sitter parser with:
- Configurable timeout to prevent infinite loops
- Graceful error recovery for partial parsing
- Performance monitoring and metrics
- Incremental parsing support
- Language-specific timeout overrides
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, NoReturn

from codecontext_core.exceptions import ParserError, UnsupportedLanguageError
from codecontext_core.models import Language as LanguageEnum
from tree_sitter import Language, Node, Parser, Tree

logger = logging.getLogger(__name__)


@dataclass
class ParsingMetrics:
    """Metrics for a single parsing operation."""

    file_path: str
    language: str
    file_size_bytes: int
    parse_time_ms: float
    success: bool
    has_errors: bool = False
    error_node_count: int = 0
    total_node_count: int = 0
    timeout_occurred: bool = False
    error_message: str | None = None

    @property
    def valid_node_ratio(self) -> float:
        """Calculate ratio of valid (non-ERROR) nodes."""
        if self.total_node_count == 0:
            return 0.0
        return 1.0 - (self.error_node_count / self.total_node_count)


@dataclass
class ParserConfig:
    """Configuration for Tree-sitter parser optimization.

    This is a lightweight data class for passing configuration to the parser.
    The full configuration is managed by Pydantic models in config/schema.py.
    """

    timeout_micros: int = 5_000_000  # 5 seconds
    enable_error_recovery: bool = True
    partial_parse_threshold: float = 0.5
    enable_incremental_parsing: bool = False
    enable_performance_monitoring: bool = False
    language_overrides: dict[str, dict[str, int]] = field(default_factory=dict)

    def get_timeout_for_language(self, language: str) -> int:
        """Get timeout for specific language, with override support."""
        # Safely handle empty or None language_overrides (e.g., from tests with Mocks)
        if self.language_overrides and language.lower() in self.language_overrides:
            return self.language_overrides[language.lower()].get(
                "timeout_micros", self.timeout_micros
            )
        return self.timeout_micros


class TreeSitterParser:
    """Optimized Tree-sitter AST parser with comprehensive error handling.

    Features:
    - Configurable timeout to prevent infinite loops on complex files
    - Graceful error recovery (returns partial AST instead of failing)
    - Performance monitoring (optional)
    - Incremental parsing support (reuse previous trees)
    - Language-specific timeout overrides
    """

    # Error message constants
    _TIMEOUT_MSG = "Parsing timed out"
    _SYNTAX_ERROR_MSG = "Source code contains syntax errors"
    _QUALITY_MSG = "Partial parse quality below threshold"

    def __init__(
        self,
        language: LanguageEnum,
        ts_language: Language,
        config: ParserConfig | None = None,
    ) -> None:
        """
        Initialize parser for a specific language.

        Args:
            language: Language enum
            ts_language: Tree-sitter language object
            config: Optional parser configuration (uses defaults if None)

        Raises:
            ParserError: If parser initialization fails
        """
        self.language = language
        self.ts_language = ts_language
        self.config = config or ParserConfig()

        # Initialize parser with timeout (if supported by tree-sitter version)
        self.parser = Parser(ts_language)
        timeout = self.config.get_timeout_for_language(language.value)

        # Try to set timeout - gracefully handle if method doesn't exist
        if hasattr(self.parser, "set_timeout_micros"):
            self.parser.set_timeout_micros(timeout)
        else:
            logger.debug(
                "tree-sitter Parser.set_timeout_micros() not available. "
                "Timeout configuration will not be applied. "
                "This is expected with older tree-sitter versions and does not affect functionality."
            )

        # Incremental parsing state
        self.previous_tree: Tree | None = None
        self._parse_count = 0

        logger.debug(
            f"Initialized {language.value} parser "
            f"(timeout={timeout / 1_000_000:.1f}s, "
            f"error_recovery={self.config.enable_error_recovery})"
        )

    def _raise_timeout_error(self, context: str = "") -> NoReturn:
        """Raise timeout error with context."""
        timeout_sec = self.config.timeout_micros / 1_000_000
        msg = f"{self._TIMEOUT_MSG} (>{timeout_sec:.1f}s)"
        if context:
            msg = f"{msg} for {context}"
        raise ParserError(msg)

    def _raise_syntax_error(self, recovery_hint: bool = True) -> NoReturn:
        """Raise syntax error with optional recovery hint."""
        msg = self._SYNTAX_ERROR_MSG
        if recovery_hint:
            msg = f"{msg}. Enable error_recovery to extract partial results."
        raise ParserError(msg)

    def _raise_quality_error(self, ratio: float, threshold: float, context: str = "") -> NoReturn:
        """Raise quality error with metrics."""
        msg = f"{self._QUALITY_MSG}: {ratio:.1%} < {threshold:.1%}"
        if context:
            msg = f"{msg} for {context}"
        raise ParserError(msg)

    def _validate_tree(
        self, tree: Tree | None, file_path: Path, file_size: int, start_time: float | None
    ) -> ParsingMetrics:
        """Validate parsed tree and return metrics."""
        # Check for timeout
        if tree is None:
            if self.config.enable_error_recovery:
                logger.warning(
                    f"Parsing {file_path} timed out "
                    f"(>{self.config.timeout_micros / 1_000_000:.1f}s). "
                    "Error recovery enabled but no partial tree available."
                )
            self._raise_timeout_error(str(file_path))

        # Analyze tree
        metrics = self._analyze_tree(tree, file_path, file_size, start_time)

        # Check for syntax errors
        if metrics.has_errors and not self.config.enable_error_recovery:
            self._raise_syntax_error()

        # Check partial parse quality
        if metrics.has_errors and metrics.valid_node_ratio < self.config.partial_parse_threshold:
            logger.warning(
                f"Partial parse quality too low for {file_path}: "
                f"{metrics.valid_node_ratio:.1%} valid nodes "
                f"(threshold: {self.config.partial_parse_threshold:.1%})"
            )
            self._raise_quality_error(
                metrics.valid_node_ratio, self.config.partial_parse_threshold, str(file_path)
            )

        return metrics

    def _log_parse_result(self, file_path: Path, metrics: ParsingMetrics) -> None:
        """Log parse results with appropriate level."""
        if metrics.has_errors:
            logger.warning(
                f"Parsed {file_path} with errors: "
                f"{metrics.error_node_count}/{metrics.total_node_count} ERROR nodes "
                f"({metrics.valid_node_ratio:.1%} valid). "
                "Partial AST will be used."
            )
        else:
            logger.debug(f"Successfully parsed {file_path}")

        # Log metrics if monitoring enabled
        if self.config.enable_performance_monitoring:
            logger.info(
                f"Parse metrics for {file_path}: "
                f"{metrics.parse_time_ms:.1f}ms, "
                f"{metrics.total_node_count} nodes, "
                f"{metrics.valid_node_ratio:.1%} valid"
            )

    def parse_file(self, file_path: Path) -> Tree:
        """
        Parse a source file into an AST with comprehensive error handling.

        This method implements the full parsing optimization strategy:
        1. Set timeout to prevent infinite loops
        2. Attempt parsing with optional incremental support
        3. Check for errors and validate partial parse quality
        4. Collect performance metrics if enabled
        5. Return tree (possibly with ERROR nodes if recovery enabled)

        Args:
            file_path: Path to the source file

        Returns:
            Parsed AST tree (may contain ERROR nodes if partial parse)

        Raises:
            ParserError: If parsing fails or partial parse quality too low
        """
        start_time = time.time() if self.config.enable_performance_monitoring else None

        try:
            # Read file
            with Path(file_path).open("rb") as f:
                source_code = f.read()

            file_size = len(source_code)

            # Parse with optional incremental support
            if self.config.enable_incremental_parsing and self.previous_tree:
                logger.debug(f"Using incremental parsing for {file_path}")
                tree = self.parser.parse(source_code, old_tree=self.previous_tree)
            else:
                tree = self.parser.parse(source_code)

            # Validate tree and get metrics
            metrics = self._validate_tree(tree, file_path, file_size, start_time)

            # Log results
            self._log_parse_result(file_path, metrics)

            # Store for incremental parsing
            if self.config.enable_incremental_parsing:
                self.previous_tree = tree
                self._parse_count += 1

        except OSError as e:
            msg = f"Failed to read file {file_path}: {e}"
            raise ParserError(msg) from e
        except ParserError:
            raise
        except (UnicodeDecodeError, RuntimeError) as e:
            msg = f"Failed to parse {file_path}: {e}"
            raise ParserError(msg) from e
        else:
            return tree

    def parse_text(self, source_code: str) -> Tree:
        """
        Parse source code text into an AST with error handling.

        Similar to parse_file but for in-memory source code.

        Args:
            source_code: Source code as string

        Returns:
            Parsed AST tree (may contain ERROR nodes if partial parse)

        Raises:
            ParserError: If parsing fails or partial parse quality too low
        """
        start_time = time.time() if self.config.enable_performance_monitoring else None

        try:
            source_bytes = bytes(source_code, "utf8")

            # Parse with optional incremental support
            if self.config.enable_incremental_parsing and self.previous_tree:
                tree = self.parser.parse(source_bytes, old_tree=self.previous_tree)
            else:
                tree = self.parser.parse(source_bytes)

            # Check for timeout
            if tree is None:
                self._raise_timeout_error()

            # Validate parse quality
            metrics = self._analyze_tree(tree, "<memory>", len(source_bytes), start_time)

            if metrics.has_errors and not self.config.enable_error_recovery:
                self._raise_syntax_error()

            # Check partial parse quality
            if (
                metrics.has_errors
                and metrics.valid_node_ratio < self.config.partial_parse_threshold
            ):
                self._raise_quality_error(
                    metrics.valid_node_ratio, self.config.partial_parse_threshold
                )

            # Log warnings if needed
            if metrics.has_errors:
                logger.warning(
                    f"Parsed source with {metrics.error_node_count} ERROR nodes "
                    f"({metrics.valid_node_ratio:.1%} valid)"
                )

            # Store for incremental parsing
            if self.config.enable_incremental_parsing:
                self.previous_tree = tree
                self._parse_count += 1

        except ParserError:
            raise
        except (UnicodeDecodeError, RuntimeError) as e:
            msg = f"Failed to parse source code: {e}"
            raise ParserError(msg) from e
        else:
            return tree

    def reset(self) -> None:
        """Reset parser state (clear cached trees for incremental parsing)."""
        self.previous_tree = None
        self._parse_count = 0
        logger.debug(f"Reset {self.language.value} parser state")

    def _analyze_tree(
        self,
        tree: Tree,
        file_path: str | Path,
        file_size: int,
        start_time: float | None,
    ) -> ParsingMetrics:
        """Analyze parse tree for errors and collect metrics."""
        has_errors = tree.root_node.has_error
        error_count = 0
        total_count = 0

        # Count ERROR nodes if tree has errors
        if has_errors:
            error_count, total_count = self._count_error_nodes(tree.root_node)
        else:
            # For valid trees, just count total nodes
            total_count = self._count_total_nodes(tree.root_node)

        # Calculate parse time if monitoring enabled
        parse_time_ms = 0.0
        if start_time is not None:
            parse_time_ms = (time.time() - start_time) * 1000

        return ParsingMetrics(
            file_path=str(file_path),
            language=self.language.value,
            file_size_bytes=file_size,
            parse_time_ms=parse_time_ms,
            success=True,
            has_errors=has_errors,
            error_node_count=error_count,
            total_node_count=total_count,
        )

    def _count_error_nodes(self, node: Node) -> tuple[int, int]:
        """Count ERROR nodes and total nodes in tree.

        Returns:
            Tuple of (error_count, total_count)
        """
        error_count = 1 if node.type == "ERROR" or node.is_missing else 0
        total_count = 1

        for child in node.children:
            child_errors, child_total = self._count_error_nodes(child)
            error_count += child_errors
            total_count += child_total

        return error_count, total_count

    def _count_total_nodes(self, node: Node) -> int:
        """Count total nodes in tree (for valid trees without errors)."""
        count = 1
        for child in node.children:
            count += self._count_total_nodes(child)
        return count

    # Existing helper methods (unchanged)

    def get_node_text(self, node: Node, source_code: bytes) -> str:
        """
        Extract text for a tree-sitter node.

        Args:
            node: Tree-sitter node
            source_code: Original source code as bytes

        Returns:
            Text content of the node
        """
        return source_code[node.start_byte : node.end_byte].decode("utf8")

    def traverse_tree(self, tree: Tree, node_types: list[str] | None = None) -> list[Node]:
        """
        Traverse AST and collect nodes of specific types.

        Args:
            tree: Parsed AST tree
            node_types: Optional list of node types to collect (e.g., ['class_definition'])
                       If None, collects all nodes

        Returns:
            List of matching nodes
        """
        results: list[Node] = []

        def visit(node: Node) -> None:
            if node_types is None or node.type in node_types:
                results.append(node)
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return results

    def find_child_by_type(self, node: Node, child_type: str) -> Node | None:
        """
        Find first direct child of a specific type.

        Args:
            node: Parent node
            child_type: Type of child to find

        Returns:
            First matching child node or None
        """
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    def find_child_by_field(self, node: Node, field_name: str) -> Node | None:
        """
        Find child by field name.

        Args:
            node: Parent node
            field_name: Field name to search for

        Returns:
            Child node with matching field name or None
        """
        return node.child_by_field_name(field_name)

    def get_node_position(self, node: Node) -> tuple[int, int]:
        """
        Get line numbers for a node.

        Args:
            node: Tree-sitter node

        Returns:
            Tuple of (start_line, end_line) with 1-based indexing
        """
        start_line = node.start_point[0] + 1  # Convert to 1-based
        end_line = node.end_point[0] + 1
        return start_line, end_line

    def extract_docstring(self, _node: Node, _source_code: bytes) -> str | None:
        """
        Extract docstring/comment for a node if available.

        Args:
            node: Tree-sitter node
            source_code: Original source code

        Returns:
            Docstring text or None
        """
        # This is language-specific and should be overridden by subclasses
        return None


class LanguageDetector:
    """Detect programming language from file extension."""

    EXTENSION_MAP: ClassVar[dict[str, LanguageEnum]] = {
        ".py": LanguageEnum.PYTHON,
        ".pyw": LanguageEnum.PYTHON,
        ".kt": LanguageEnum.KOTLIN,
        ".kts": LanguageEnum.KOTLIN,
        ".java": LanguageEnum.JAVA,
        ".js": LanguageEnum.JAVASCRIPT,
        ".jsx": LanguageEnum.JAVASCRIPT,
        ".mjs": LanguageEnum.JAVASCRIPT,
        ".cjs": LanguageEnum.JAVASCRIPT,
        ".ts": LanguageEnum.TYPESCRIPT,
        ".tsx": LanguageEnum.TYPESCRIPT,
        ".mts": LanguageEnum.TYPESCRIPT,
        ".cts": LanguageEnum.TYPESCRIPT,
        ".md": LanguageEnum.MARKDOWN,
        ".yaml": LanguageEnum.YAML,
        ".yml": LanguageEnum.YAML,
        ".json": LanguageEnum.JSON,
        ".properties": LanguageEnum.PROPERTIES,
    }

    @classmethod
    def detect_language(cls, file_path: Path) -> LanguageEnum:
        """
        Detect language from file extension.

        Args:
            file_path: Path to source file

        Returns:
            Detected language

        Raises:
            UnsupportedLanguageError: If language is not supported
        """
        suffix = file_path.suffix.lower()
        language = cls.EXTENSION_MAP.get(suffix)
        if language is None:
            raise UnsupportedLanguageError(suffix)
        return language

    @classmethod
    def is_supported(cls, file_path: Path) -> bool:
        """
        Check if file extension is supported.

        Args:
            file_path: Path to source file

        Returns:
            True if supported, False otherwise
        """
        return file_path.suffix.lower() in cls.EXTENSION_MAP
