"""File discovery and filtering for indexing."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pathspec

if TYPE_CHECKING:
    from codecontext.config.schema import Config

from codecontext.indexer.ast_parser import LanguageDetector
from codecontext.parsers.languages.config import ConfigFileParser
from codecontext.utils.path_filter import PathFilter

logger = logging.getLogger(__name__)


class FileScanner:
    """Discovers and filters files for indexing."""

    def __init__(self, repository_path: Path, config: "Config") -> None:
        self.repository_path = repository_path
        self.config = config
        self.path_filter = PathFilter(repository_path)
        self.max_file_size_bytes = config.indexing.max_file_size_mb * 1024 * 1024

        self.include_spec = pathspec.PathSpec.from_lines("gitwildmatch", config.project.include)
        self.exclude_spec = pathspec.PathSpec.from_lines("gitwildmatch", config.project.exclude)

        logger.info(
            f"FileScanner: {len(config.project.include)} include, "
            f"{len(config.project.exclude)} exclude patterns"
        )

    def scan_source_files(self) -> list[Path]:
        return self.scan_code_files() + self.scan_document_files()

    def scan_code_files(self) -> list[Path]:
        code_files = self._scan_code_files()
        logger.debug(f"Discovered {len(code_files)} code files")
        return code_files

    def scan_document_files(self) -> list[Path]:
        markdown_files = self._scan_markdown_files()
        config_files = self._scan_config_files()

        logger.info(
            f"Document file discovery: {len(markdown_files)} markdown, "
            f"{len(config_files)} config files"
        )

        return markdown_files + config_files

    def _scan_code_files(self) -> list[Path]:
        code_files = []

        supported_extensions = set(LanguageDetector.EXTENSION_MAP.keys())
        document_extensions = {".md", ".markdown", ".yaml", ".yml", ".json", ".properties"}
        code_extensions = supported_extensions - document_extensions

        for ext in code_extensions:
            for file_path in self.repository_path.glob(f"**/*{ext}"):
                if self._should_include_file(file_path, is_code=True):
                    code_files.append(file_path)

        return code_files

    def _scan_markdown_files(self) -> list[Path]:
        markdown_files = []

        for pattern in ["**/*.md", "**/*.markdown"]:
            for file_path in self.repository_path.glob(pattern):
                if self._should_include_file(file_path, is_code=False):
                    markdown_files.append(file_path)

        return markdown_files

    def _scan_config_files(self) -> list[Path]:
        config_files = []

        for ext in ConfigFileParser.get_supported_extensions():
            for file_path in self.repository_path.glob(f"**/*{ext}"):
                if self._should_include_file(file_path, is_code=False, is_config=True):
                    config_files.append(file_path)

        return config_files

    def _should_include_file(
        self, file_path: Path, is_code: bool = False, is_config: bool = False
    ) -> bool:
        if not file_path.is_file():
            return False

        try:
            relative_path = file_path.relative_to(self.repository_path)
        except ValueError:
            return False

        path_str = str(relative_path).replace("\\", "/")

        if not self.include_spec.match_file(path_str):
            return False

        if self.exclude_spec.match_file(path_str):
            return False

        if file_path.stat().st_size > self.max_file_size_bytes:
            return False

        if not self.path_filter.should_index(file_path):
            return False

        if is_code and not LanguageDetector.is_supported(file_path):
            return False

        if is_config:
            config_parser = ConfigFileParser()
            if not config_parser.is_supported(file_path):
                return False

        return True

    def get_file_statistics(self) -> dict[str, int]:
        code_files = self._scan_code_files()
        markdown_files = self._scan_markdown_files()
        config_files = self._scan_config_files()

        return {
            "code_files": len(code_files),
            "markdown_files": len(markdown_files),
            "config_files": len(config_files),
            "total_files": len(code_files) + len(markdown_files) + len(config_files),
        }
