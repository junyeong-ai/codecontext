"""Parser factory for creating CODE-specific language parsers.

This factory creates CodeParser implementations for code files ONLY.
Document files (markdown, YAML, JSON, properties) are handled separately
by MarkdownParser and ConfigFileParser in AsyncIndexStrategy.

Architecture:
- ParserFactory → CodeParser (CodeObject extraction)
- MarkdownParser → DocumentNode extraction
- ConfigFileParser → DocumentNode extraction
"""

from pathlib import Path

from codecontext_core.exceptions import UnsupportedLanguageError
from codecontext_core.models import Language

from codecontext.config.schema import ParsingConfig
from codecontext.indexer.ast_parser import LanguageDetector, ParserConfig
from codecontext.parsers.interfaces import CodeParser
from codecontext.parsers.languages.java import JavaParser
from codecontext.parsers.languages.javascript import JavaScriptParser
from codecontext.parsers.languages.kotlin import KotlinParser
from codecontext.parsers.languages.python import PythonParser
from codecontext.parsers.languages.typescript import TypeScriptParser


class ParserFactory:
    """Factory for creating CODE language parsers (CodeParser interface).

    Clean Architecture Design:
    - Creates CodeParser implementations ONLY (Python, Kotlin, Java, JS, TS)
    - Returns parsers that extract CodeObject instances
    - Document parsers (Markdown, Config) are handled separately

    Usage:
        factory = ParserFactory.from_parsing_config(config)
        parser = factory.get_parser("example.py")  # Returns PythonParser
        objects = parser.extract_code_objects(file_path, source)  # CodeObject list

    Note:
        - Raises UnsupportedLanguageError for document files (.md, .yaml, etc.)
        - Document files should be processed via MarkdownParser/ConfigFileParser
    """

    def __init__(self, parser_config: ParserConfig | None = None) -> None:
        """Initialize parser factory with configuration.

        Args:
            parser_config: Parser configuration (optional, uses defaults if None)
        """
        self._parser_config = parser_config
        self._cache: dict[Language, CodeParser] = {}

    @classmethod
    def from_parsing_config(cls, parsing_config: ParsingConfig) -> "ParserFactory":
        """Create factory from Pydantic parsing configuration.

        Args:
            parsing_config: Pydantic parsing configuration from settings

        Returns:
            ParserFactory instance
        """
        parser_config = ParserConfig(
            timeout_micros=parsing_config.timeout_micros,
            enable_error_recovery=parsing_config.enable_error_recovery,
            partial_parse_threshold=parsing_config.partial_parse_threshold,
            language_overrides=parsing_config.language_overrides,
        )
        return cls(parser_config)

    def get_parser(self, file_path: str) -> CodeParser:
        """Get CODE parser for file (CODE FILES ONLY).

        Args:
            file_path: Path to CODE source file (as string)

        Returns:
            Language-specific parser instance (PythonParser, KotlinParser, etc.)

        Raises:
            UnsupportedLanguageError: If file is not a supported CODE language
                or if file is a document (.md, .yaml, etc.) - use MarkdownParser instead
        """
        language = LanguageDetector.detect_language(Path(file_path))
        return self.get_parser_by_language(language)

    def get_parser_by_language(self, language: Language) -> CodeParser:
        """Get parser for a specific language.

        Args:
            language: Language enum

        Returns:
            Language-specific parser instance (cached)

        Raises:
            UnsupportedLanguageError: If language is not supported
        """
        if language not in self._cache:
            self._cache[language] = self._create_parser(language)
        return self._cache[language]

    def _create_parser(self, language: Language) -> CodeParser:
        """Create a new CODE parser instance for a language.

        Args:
            language: Language enum (CODE LANGUAGES ONLY)

        Returns:
            Language-specific parser instance (with ParserConfig applied)

        Raises:
            UnsupportedLanguageError: If language is not a supported CODE language.
                Document languages (MARKDOWN, YAML, JSON, PROPERTIES) should use
                MarkdownParser or ConfigFileParser instead.
        """
        # Code languages ONLY
        if language == Language.PYTHON:
            return PythonParser(parser_config=self._parser_config)
        elif language == Language.KOTLIN:
            return KotlinParser(parser_config=self._parser_config)
        elif language == Language.JAVA:
            return JavaParser(parser_config=self._parser_config)
        elif language == Language.JAVASCRIPT:
            return JavaScriptParser(parser_config=self._parser_config)
        elif language == Language.TYPESCRIPT:
            return TypeScriptParser(parser_config=self._parser_config)
        # Document languages → explicit error with guidance
        elif language in [Language.MARKDOWN, Language.YAML, Language.JSON, Language.PROPERTIES]:
            msg = (
                f"{language.value} files are not CODE files. "
                f"Use MarkdownParser or ConfigFileParser instead. "
                f"This factory creates CodeParser instances for CODE extraction only."
            )
            raise UnsupportedLanguageError(msg)
        else:
            raise UnsupportedLanguageError(language.value)

    def clear_cache(self) -> None:
        """Clear cached parser instances."""
        self._cache.clear()
