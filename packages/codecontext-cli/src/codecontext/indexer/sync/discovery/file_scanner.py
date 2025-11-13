"""File discovery and filtering for indexing.

Clean Architecture: Separates code files from document files for proper handling.

This module provides file scanning functionality to discover source files
in a repository while respecting filters and size limits.

Design:
- Code files → ParserFactory → LanguageParser → CodeObject
- Document files → MarkdownParser/ConfigParser → DocumentNode
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codecontext.config.schema import CodeContextConfig

import logging

from codecontext.indexer.ast_parser import LanguageDetector
from codecontext.parsers.languages.config import ConfigFileParser
from codecontext.utils.path_filter import PathFilter

logger = logging.getLogger(__name__)


class FileScanner:
    """Discovers and filters files for indexing with clean separation.

    Clean Architecture Design:
    - Separates code files from document files
    - Code files: Python, Java, Kotlin, JavaScript, TypeScript
    - Document files: Markdown, YAML, JSON, Properties

    Applies filtering:
    - Gitignore patterns
    - File size limits
    - Path exclusions
    """

    def __init__(self, repository_path: Path, config: "CodeContextConfig") -> None:
        """Initialize file scanner.

        Args:
            repository_path: Path to repository root
            config: CodeContext configuration with indexing settings
        """
        self.repository_path = repository_path
        self.config = config
        self.path_filter = PathFilter(repository_path)
        self.max_file_size_bytes = config.indexing.max_file_size_mb * 1024 * 1024

    def scan_source_files(self) -> list[Path]:
        """Scan repository for ALL source files (code + documents).

        Returns:
            List of all file paths (code + markdown + config)
        """
        return self.scan_code_files() + self.scan_document_files()

    def scan_code_files(self) -> list[Path]:
        """Scan repository for CODE files ONLY.

        Returns:
            List of code file paths (.py, .kt, .java, .js, .ts, etc.)
        """
        code_files = self._scan_code_files()
        logger.debug(f"Discovered {len(code_files)} code files")
        return code_files

    def scan_document_files(self) -> list[Path]:
        """Scan repository for DOCUMENT files ONLY.

        Returns:
            List of document file paths (.md, .yaml, .json, .properties)
        """
        markdown_files = self._scan_markdown_files()
        config_files = self._scan_config_files()

        # Enhanced logging for debugging empty results
        logger.info(
            f"Document file discovery: {len(markdown_files)} markdown, {len(config_files)} config files"
        )

        if len(markdown_files) == 0:
            logger.warning("⚠️  No markdown files discovered - investigating...")
            # Test glob directly to see if files exist
            all_md = list(self.repository_path.glob("**/*.md"))
            logger.warning(f"   Raw glob found {len(all_md)} .md files in repository")

            if all_md:
                # Test first file against filter
                test_file = all_md[0]
                included = self._should_include_file(test_file, is_code=False)
                logger.warning(f"   Test file '{test_file.name}': filter_result={included}")
                logger.warning(f"   PathFilter has {len(self.path_filter.patterns)} patterns")

        document_files = markdown_files + config_files
        logger.debug(f"Discovered {len(document_files)} document files")
        return document_files

    def _scan_code_files(self) -> list[Path]:
        """Scan for code files based on supported language extensions.

        Returns:
            List of code file paths
        """
        code_files = []

        # Get all supported extensions from LanguageDetector
        # This ensures we discover all supported languages (.py, .kt, .kts, .jsx, .tsx, etc.)
        supported_extensions = set(LanguageDetector.EXTENSION_MAP.keys())

        # Exclude document/config extensions
        # (handled separately by _scan_markdown_files and _scan_config_files)
        document_extensions = {".md", ".markdown", ".yaml", ".yml", ".json", ".properties"}
        code_extensions = supported_extensions - document_extensions

        for ext in code_extensions:
            pattern = f"**/*{ext}"
            for file_path in self.repository_path.glob(pattern):
                if self._should_include_file(file_path, is_code=True):
                    code_files.append(file_path)

        return code_files

    def _scan_markdown_files(self) -> list[Path]:
        """Scan for markdown documentation files.

        Returns:
            List of markdown file paths
        """
        markdown_files = []

        for pattern in ["**/*.md", "**/*.markdown"]:
            for file_path in self.repository_path.glob(pattern):
                if self._should_include_file(file_path, is_code=False):
                    markdown_files.append(file_path)

        return markdown_files

    def _scan_config_files(self) -> list[Path]:
        """Scan for configuration files (YAML, JSON, Properties).

        Returns:
            List of config file paths
        """
        config_files = []

        # Get supported config extensions
        config_extensions = ConfigFileParser.get_supported_extensions()

        for ext in config_extensions:
            pattern = f"**/*{ext}"
            for file_path in self.repository_path.glob(pattern):
                if self._should_include_file(file_path, is_code=False, is_config=True):
                    config_files.append(file_path)

        return config_files

    def _should_include_file(
        self, file_path: Path, is_code: bool = False, is_config: bool = False
    ) -> bool:
        """Check if a file should be included based on filters.

        Args:
            file_path: Path to file
            is_code: Whether this is a code file (requires language detection)
            is_config: Whether this is a config file (requires format detection)

        Returns:
            True if file should be included, False otherwise
        """
        # Must be a file (not directory)
        if not file_path.is_file():
            return False

        # Check file size limit
        if file_path.stat().st_size > self.max_file_size_bytes:
            logger.debug(
                f"Skipping {file_path}: exceeds size limit "
                f"({file_path.stat().st_size / 1024 / 1024:.1f}MB)"
            )
            return False

        # Check path filter (gitignore, exclusions)
        if not self.path_filter.should_index(file_path):
            return False

        # Additional validation for code files
        if is_code and not LanguageDetector.is_supported(file_path):
            return False

        # Additional validation for config files
        if is_config:
            from codecontext.parsers.languages.config import ConfigFileParser

            config_parser = ConfigFileParser()
            if not config_parser.is_supported(file_path):
                return False

        return True

    def get_file_statistics(self) -> dict[str, int]:
        """Get statistics about discovered files.

        Returns:
            Dictionary with file counts by type
        """
        code_files = self._scan_code_files()
        markdown_files = self._scan_markdown_files()
        config_files = self._scan_config_files()

        return {
            "code_files": len(code_files),
            "markdown_files": len(markdown_files),
            "config_files": len(config_files),
            "total_files": len(code_files) + len(markdown_files) + len(config_files),
        }
