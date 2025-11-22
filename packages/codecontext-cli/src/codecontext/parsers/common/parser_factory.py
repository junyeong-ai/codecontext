"""Factory for creating language-specific TreeSitter parsers.

Eliminates duplication across Python, Java, Kotlin, JavaScript, and TypeScript parsers
by centralizing parser initialization logic.
"""

from typing import Any, ClassVar, cast

from codecontext_core.models import Language
from tree_sitter_language_pack import get_language

from codecontext.indexer.ast_parser import ParserConfig, TreeSitterParser


class TreeSitterParserFactory:
    """Factory for creating language-specific TreeSitter parsers with defaults.

    Centralizes parser initialization logic that was previously duplicated
    across 5 language parsers (Python, Java, Kotlin, JavaScript, TypeScript).
    """

    # Language-specific timeout defaults (in microseconds)
    LANGUAGE_TIMEOUTS: ClassVar[dict[Language, int]] = {
        Language.PYTHON: 5_000_000,  # 5s - simple syntax
        Language.JAVA: 5_000_000,  # 5s - simple syntax
        Language.JAVASCRIPT: 5_000_000,  # 5s - simple syntax
        Language.TYPESCRIPT: 7_000_000,  # 7s - complex type resolution
        Language.KOTLIN: 10_000_000,  # 10s - DSL patterns (Gradle, etc.)
    }

    # Special grammar name mappings
    # Some languages use different grammar names than their Language enum value
    GRAMMAR_OVERRIDES: ClassVar[dict[Language, str]] = {
        Language.TYPESCRIPT: "tsx",  # TSX supports both .ts and .tsx files
    }

    @classmethod
    def create_parser(
        cls,
        language: Language,
        parser_config: ParserConfig | None = None,
    ) -> TreeSitterParser:
        """Create a TreeSitter parser for the given language.

        Args:
            language: Target programming language
            parser_config: Optional configuration override. If None, uses sensible defaults.

        Returns:
            Configured TreeSitterParser instance ready for AST parsing

        Example:
            >>> parser = TreeSitterParserFactory.create_parser(Language.PYTHON)
            >>> # Parser is ready to use with 5s timeout and error recovery enabled
        """
        # Get the grammar name (with special overrides for languages like TSX)
        grammar_name = cls.GRAMMAR_OVERRIDES.get(language, language.value.lower())
        ts_language = get_language(cast(Any, grammar_name))

        # Use provided config or create default with language-specific timeout
        if parser_config is None:
            timeout = cls.LANGUAGE_TIMEOUTS.get(language, 5_000_000)
            parser_config = ParserConfig(
                timeout_micros=timeout,
                enable_error_recovery=True,
                partial_parse_threshold=0.5,
            )

        return TreeSitterParser(language, ts_language, parser_config)
