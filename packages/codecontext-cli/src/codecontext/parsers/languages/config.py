"""Configuration file parser for CodeContext.

This parser handles configuration files (.properties, .json, .yaml, .yml),
chunking them into semantic sections using hierarchical adaptive chunking.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, ClassVar, NoReturn

import yaml
from codecontext_core.models import DocumentNode, Language

from codecontext.parsers.common.chunkers.properties import PropertiesConfigChunker
from codecontext.parsers.common.chunkers.yaml_json import JSONConfigChunker, YAMLConfigChunker
from codecontext.parsers.interfaces import ConfigParser

logger = logging.getLogger(__name__)


class ConfigFileParser(ConfigParser):
    """Parser for configuration files with format detection.

    This parser supports multiple configuration formats:
    - YAML (.yaml, .yml)
    - JSON (.json)
    - Properties (.properties)

    Features:
    - Format-agnostic parsing with automatic detection
    - Hierarchical adaptive chunking for optimal search
    - Rich metadata extraction (keys, values, env refs)
    - Section-based splitting with size optimization
    """

    SUPPORTED_EXTENSIONS: ClassVar[dict[str, str]] = {
        ".properties": "properties",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
    }

    # Error message constants
    _FILE_NOT_FOUND_MSG = "File not found"
    _UNSUPPORTED_FORMAT_MSG = "Unsupported config file format"
    _UNKNOWN_FORMAT_MSG = "Unknown format"

    def _raise_file_not_found(self, file_path: Path) -> NoReturn:
        """Raise FileNotFoundError for missing file."""
        msg = f"{self._FILE_NOT_FOUND_MSG}: {file_path}"
        raise FileNotFoundError(msg)

    def _raise_unsupported_format(self, suffix: str) -> NoReturn:
        """Raise ValueError for unsupported format."""
        msg = f"{self._UNSUPPORTED_FORMAT_MSG}: {suffix}"
        raise ValueError(msg)

    def _raise_unknown_format(self, format_name: str) -> NoReturn:
        """Raise ValueError for unknown format."""
        msg = f"{self._UNKNOWN_FORMAT_MSG}: {format_name}"
        raise ValueError(msg)

    def __init__(
        self, chunk_size: int = 512, min_chunk_size: int = 100, max_depth: int = 4
    ) -> None:
        """Initialize config file parser.

        Args:
            chunk_size: Target chunk size in tokens (default: 512)
            min_chunk_size: Minimum chunk size to prevent tiny chunks (default: 100)
            max_depth: Maximum nesting depth for splitting (default: 4)
        """
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_depth = max_depth
        self._last_format: str | None = None  # Track format of last parsed file
        # Create specific chunkers directly
        self.yaml_chunker = YAMLConfigChunker(chunk_size, min_chunk_size, max_depth)
        self.json_chunker = JSONConfigChunker(chunk_size, min_chunk_size, max_depth)
        self.properties_chunker = PropertiesConfigChunker(chunk_size, min_chunk_size, max_depth)
        logger.debug(
            f"Initialized ConfigFileParser with chunk_size={chunk_size}, "
            f"min_chunk_size={min_chunk_size}, max_depth={max_depth}"
        )

    def parse_file(self, file_path: Path) -> list[DocumentNode]:
        """Parse a config file into DocumentNode instances.

        Args:
            file_path: Path to configuration file

        Returns:
            List of DocumentNode instances representing chunks

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        logger.info(f"Parsing config file: {file_path}")

        # Validate file
        if not file_path.exists():
            self._raise_file_not_found(file_path)

        # Detect format
        config_format = self._detect_format(file_path)
        if config_format is None:
            self._raise_unsupported_format(file_path.suffix)

        # Track format for interface methods
        self._last_format = config_format

        try:
            if config_format == "yaml":
                document_nodes = self._parse_yaml(file_path)
            elif config_format == "json":
                document_nodes = self._parse_json(file_path)
            elif config_format == "properties":
                document_nodes = self._parse_properties(file_path)
            else:
                self._raise_unknown_format(config_format)

            logger.info(f"Successfully parsed {file_path}: {len(document_nodes)} chunks")
            return document_nodes

        except Exception as e:
            logger.error(
                f"Failed to parse {file_path}: {e}. Skipping file.",
                exc_info=True,
            )
            return []

    def _detect_format(self, file_path: Path) -> str | None:
        """Detect configuration file format from extension.

        Args:
            file_path: Path to file

        Returns:
            Format string ("yaml", "json", "properties") or None if unsupported
        """
        suffix = file_path.suffix.lower()
        return self.SUPPORTED_EXTENSIONS.get(suffix)

    def _parse_yaml(self, file_path: Path) -> list[DocumentNode]:
        """Parse single or multi-document YAML file."""
        import yaml

        logger.debug(f"Parsing YAML file: {file_path}")
        content = file_path.read_text(encoding="utf-8")

        try:
            return self._parse_multidoc_yaml(content, file_path)
        except yaml.YAMLError:
            logger.debug(f"Trying single-document parse for {file_path}")
            return self._parse_singledoc_yaml(content, file_path)

    def _parse_multidoc_yaml(self, content: str, file_path: Path) -> list[DocumentNode]:
        """Parse multi-document YAML (e.g., Spring Boot profiles)."""
        import yaml

        documents = list(yaml.safe_load_all(content))
        if not documents:
            return []

        all_chunks = []
        for idx, doc in enumerate(documents):
            if doc is None:
                continue

            try:
                chunks = self.yaml_chunker.chunk_yaml(doc, file_path)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Failed to chunk document {idx} in {file_path}: {e}")

        if len(documents) > 1:
            logger.debug(f"{file_path}: {len(documents)} documents, {len(all_chunks)} chunks")

        return all_chunks

    def _parse_singledoc_yaml(self, content: str, file_path: Path) -> list[DocumentNode]:
        """Parse single-document YAML."""
        import yaml

        data = yaml.safe_load(content)
        if data is None:
            return []

        return self.yaml_chunker.chunk_yaml(data, file_path)

    def _parse_json(self, file_path: Path) -> list[DocumentNode]:
        """Parse JSON file with hierarchical chunking.

        Args:
            file_path: Path to JSON file

        Returns:
            List of DocumentNode chunks
        """
        import json

        logger.debug(f"Parsing JSON file: {file_path}")
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)

        if data is None:
            logger.warning(f"Empty JSON file: {file_path}")
            return []

        return self.json_chunker.chunk_json(data, file_path)

    def _parse_properties(self, file_path: Path) -> list[DocumentNode]:
        """Parse properties file with prefix-based grouping.

        Args:
            file_path: Path to properties file

        Returns:
            List of DocumentNode chunks
        """
        logger.debug(f"Parsing properties file: {file_path}")
        return self.properties_chunker.chunk_properties(file_path)

    # Parser interface methods

    def get_language(self) -> Language:
        """Get the language this parser handles.

        Returns the language based on the last parsed file format.
        Falls back to YAML if no file has been parsed yet.
        """
        format_to_language = {
            "yaml": Language.YAML,
            "json": Language.JSON,
            "properties": Language.PROPERTIES,
        }
        return format_to_language.get(self._last_format or "yaml", Language.YAML)

    def supports_file(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to check

        Returns:
            True if file is a supported config format, False otherwise
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def get_file_extensions(self) -> list[str]:
        """Get list[Any] of supported file extensions.

        Returns:
            List of supported extensions (e.g., [".yaml", ".yml", ".json", ".properties"])
        """
        return list[Any](self.SUPPORTED_EXTENSIONS.keys())

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """Get list[Any] of supported file extensions (class method for static access).

        Returns:
            List of supported extensions (e.g., ['.yaml', '.yml', '.json', '.properties'])
        """
        return list[Any](cls.SUPPORTED_EXTENSIONS.keys())

    def is_supported(self, file_path: Path) -> bool:
        """Check if the file format is supported.

        Args:
            file_path: Path to file to check

        Returns:
            True if file extension is supported, False otherwise
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    # DocumentParser interface methods

    def extract_code_references(self, content: str) -> list[dict[str, Any]]:
        """Extract references to code from configuration content.

        Extracts:
        - Class references (e.g., com.example.ClassName)
        - File paths (e.g., /path/to/script.py)
        - URLs with code file extensions

        Args:
            content: Configuration file content

        Returns:
            List of code references with context
        """
        references = []

        # Extract Java-style class references (com.example.ClassName)
        class_pattern = r"([a-z][a-z0-9_]*\.)+[A-Z][a-zA-Z0-9_]*"
        for match in re.finditer(class_pattern, content):
            class_ref = match.group(0)
            references.append(
                {
                    "type": "class_reference",
                    "ref": class_ref,
                    "context": content[max(0, match.start() - 50) : match.end() + 50],
                }
            )

        # Extract file paths to code files
        file_pattern = r"['\"]([^'\"]*\.(?:py|js|ts|java|kt|go|rs|cpp|c|h|sh))['\"]"
        for match in re.finditer(file_pattern, content):
            file_path = match.group(1)
            references.append(
                {
                    "type": "file_reference",
                    "file": file_path,
                }
            )

        # Extract URLs pointing to code repositories
        url_pattern = r"https?://[^\s\"']+(?:\.git|/blob/|/tree/)"
        for match in re.finditer(url_pattern, content):
            url = match.group(0)
            references.append(
                {
                    "type": "repository_url",
                    "url": url,
                }
            )

        return references

    def chunk_document(
        self, content: str, max_chunk_size: int = 1500
    ) -> list[tuple[str, int, int]]:
        """Split large configuration documents into chunks for embedding.

        Delegates to format-specific chunkers for structural parsing,
        eliminating code duplication across formats.

        Args:
            content: Configuration file content
            max_chunk_size: Maximum characters per chunk

        Returns:
            List of (chunk_content, start_index, end_index) tuples
        """
        # Simple line-based chunking for interface compatibility
        # (DocumentNodes are created by parse_file() using proper chunkers)
        if len(content) <= max_chunk_size:
            return [(content, 0, len(content))]

        # Split by lines to maintain readability
        chunks = []
        lines = content.split("\n")
        current_chunk: list[str] = []
        current_start = 0
        current_pos = 0

        for line in lines:
            line_with_newline = line + "\n"
            if (
                len("\n".join(current_chunk)) + len(line_with_newline) > max_chunk_size
                and current_chunk
            ):
                chunk_content = "\n".join(current_chunk)
                chunks.append((chunk_content, current_start, current_pos))
                current_chunk = [line]
                current_start = current_pos
            else:
                current_chunk.append(line)
            current_pos += len(line) + 1

        # Add final chunk
        if current_chunk:
            chunk_content = "\n".join(current_chunk)
            chunks.append((chunk_content, current_start, len(content)))

        return chunks if chunks else [(content, 0, len(content))]

    # ConfigParser interface methods

    def extract_config_keys(self, content: str) -> list[str]:
        """Extract all configuration keys from the content.

        Args:
            content: Configuration file content

        Returns:
            List of configuration key paths (e.g., ["server.port", "database.url"])
        """
        keys = []
        detected_format = self._detect_format_from_content(content)

        if detected_format == "json":
            try:
                data = json.loads(content)
                keys = self._extract_json_keys(data)
            except json.JSONDecodeError:
                pass

        elif detected_format == "yaml":
            try:
                data = yaml.safe_load(content)
                keys = self._extract_yaml_keys(data)
            except yaml.YAMLError:
                pass

        elif detected_format == "properties":
            for line in content.split("\n"):
                if "=" in line and not line.strip().startswith("#"):
                    key = line.split("=")[0].strip()
                    if key:
                        keys.append(key)

        return keys

    def extract_env_references(self, content: str) -> list[str]:
        """Extract environment variable references from the content.

        Extracts patterns like ${VAR}, $VAR, %VAR%, etc.

        Args:
            content: Configuration file content

        Returns:
            List of environment variable names
        """
        env_vars = set[Any]()

        # ${VAR} style (common in Spring Boot, etc.)
        pattern1 = r"\$\{([A-Z_][A-Z0-9_]*)\}"
        env_vars.update(re.findall(pattern1, content))

        # $VAR style (shell-style)
        pattern2 = r"\$([A-Z_][A-Z0-9_]*)"
        env_vars.update(re.findall(pattern2, content))

        # %VAR% style (Windows-style)
        pattern3 = r"%([A-Z_][A-Z0-9_]*)%"
        env_vars.update(re.findall(pattern3, content))

        return sorted(list[Any](env_vars))

    def get_config_format(self) -> str:
        """Get the configuration file format.

        Returns:
            Format string ("yaml", "json", "properties")
        """
        return self._last_format or "yaml"

    def extract_dependencies(self, content: str) -> list[dict[str, Any]]:
        """Extract dependency information from configuration files.

        Extracts dependency declarations from common formats like:
        - Maven dependencies (pom.xml converted to properties)
        - Gradle dependencies (build.gradle.kts)
        - Package.json dependencies
        - Requirements.txt style

        Args:
            content: Configuration file content

        Returns:
            List of dependency dictionaries with name, version, scope
        """
        detected_format = self._detect_format_from_content(content)

        if detected_format == "json":
            return self._extract_json_dependencies(content)
        if detected_format == "yaml":
            return self._extract_yaml_dependencies(content)

        return []

    def _extract_json_dependencies(self, content: str) -> list[dict[str, Any]]:
        """Extract npm-style dependencies from JSON content."""
        dependencies = []
        try:
            data = json.loads(content)
            for dep_type in ["dependencies", "devDependencies", "peerDependencies"]:
                if dep_type in data and isinstance(data[dep_type], dict):
                    for name, version in data[dep_type].items():
                        dependencies.append({"name": name, "version": version, "scope": dep_type})
        except json.JSONDecodeError:
            pass
        return dependencies

    def _extract_yaml_dependencies(self, content: str) -> list[dict[str, Any]]:
        """Extract dependencies from YAML content."""
        dependencies = []
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                for key in ["dependencies", "requires", "packages"]:
                    if key in data:
                        deps = data[key]
                        if isinstance(deps, list):
                            dependencies.extend(self._extract_yaml_dep_items(deps, key))
        except yaml.YAMLError:
            pass
        return dependencies

    def _extract_yaml_dep_items(
        self, deps: list[dict[str, Any]], scope: str
    ) -> list[dict[str, Any]]:
        """Extract individual dependency items from YAML list[Any]."""
        dependencies = []
        for dep in deps:
            if isinstance(dep, str):
                dependencies.append({"name": dep, "version": "unspecified", "scope": scope})
            elif isinstance(dep, dict):
                dependencies.append(
                    {
                        "name": dep.get("name", "unknown"),
                        "version": dep.get("version", "unspecified"),
                        "scope": scope,
                    }
                )
        return dependencies

    # Helper methods

    def _detect_format_from_content(self, content: str) -> str:
        """Detect configuration format from content structure.

        Args:
            content: Configuration file content

        Returns:
            Format string ("yaml", "json", "properties", or "unknown")
        """
        content_stripped = content.strip()

        # JSON: starts with { or [
        if content_stripped.startswith("{") or content_stripped.startswith("["):
            try:
                json.loads(content)
            except json.JSONDecodeError:
                pass
            else:
                return "json"

        # Properties: contains key=value lines
        if any("=" in line and not line.strip().startswith("#") for line in content.split("\n")):
            return "properties"

        # YAML: contains key: value lines or YAML-specific markers
        if any(":" in line for line in content.split("\n")[:10]):
            return "yaml"

        return "unknown"

    def _extract_json_keys(
        self, data: dict[str, list[Any]] | list[Any], prefix: str = ""
    ) -> list[str]:
        """Recursively extract keys from JSON data.

        Args:
            data: JSON data structure
            prefix: Current key prefix for nested keys

        Returns:
            List of dot-separated key paths
        """
        keys = []

        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                keys.append(full_key)
                if isinstance(value, (dict, list)):
                    keys.extend(self._extract_json_keys(value, full_key))

        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    keys.extend(self._extract_json_keys(item, f"{prefix}[{i}]"))

        return keys

    def _extract_yaml_keys(
        self, data: dict[str, list[Any]] | list[Any], prefix: str = ""
    ) -> list[str]:
        """Recursively extract keys from YAML data.

        YAML and JSON share identical hierarchical structure when parsed,
        so key extraction logic is unified to avoid duplication.

        Args:
            data: YAML data structure
            prefix: Current key prefix for nested keys

        Returns:
            List of dot-separated key paths
        """
        # YAML uses same structure as JSON, delegate to avoid duplication
        return self._extract_json_keys(data, prefix)


def parse_config_file(file_path: Path, chunk_size: int = 512) -> list[DocumentNode]:
    """Convenience function to parse a configuration file.

    Args:
        file_path: Path to configuration file
        chunk_size: Target chunk size in tokens (default: 512)

    Returns:
        List of DocumentNode instances
    """
    parser = ConfigFileParser(chunk_size=chunk_size)
    return parser.parse_file(file_path)
