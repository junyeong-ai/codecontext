"""Custom exceptions for CodeContext."""

from typing import Any


class CodeContextError(Exception):
    """Base exception for all CodeContext errors."""


class ConfigurationError(CodeContextError):
    """Raised when there is a configuration error."""


class EmbeddingError(CodeContextError):
    """Raised when embedding generation fails."""


class StorageError(CodeContextError):
    """Raised when storage operations fail."""


class IndexingError(CodeContextError):
    """Raised when indexing operations fail."""


class SearchError(CodeContextError):
    """Raised when search operations fail."""


class ParserError(CodeContextError):
    """Raised when AST parsing fails."""


class ValidationError(CodeContextError):
    """Raised when data validation fails."""


class InvalidParameterError(CodeContextError):
    """Raised when invalid parameters are provided."""

    def __init__(self, param_name: str, value: Any, constraint: str) -> None:
        super().__init__(f"Invalid parameter '{param_name}' = {value}: {constraint}")
        self.param_name = param_name
        self.value = value
        self.constraint = constraint


class ProviderConfigurationNotFoundError(ConfigurationError):
    """Raised when provider configuration is not found."""

    def __init__(self, provider_type: str) -> None:
        super().__init__(
            f"Configuration for provider '{provider_type}' not found in config. "
            f"Add '{provider_type}:' section to your config file."
        )
        self.provider_type = provider_type


class ProviderNotFoundError(ConfigurationError):
    """Raised when provider is not found."""

    def __init__(self, provider_type: str, available: list[str]) -> None:
        available_str = ", ".join(available) if available else "none"
        super().__init__(
            f"Provider '{provider_type}' not found. "
            f"Available providers: {available_str}. "
            f"Install with: pip install codecontext-{provider_type}"
        )
        self.provider_type = provider_type
        self.available = available


class GitError(CodeContextError):
    """Raised when git operations fail."""


class UnsupportedLanguageError(CodeContextError):
    """Raised when an unsupported language is encountered."""

    def __init__(self, language: str) -> None:
        super().__init__(f"Unsupported language: {language}")
        self.language = language


class FileNotInRepositoryError(IndexingError):
    """Raised when a file is not in the repository."""

    def __init__(self, file_path: str) -> None:
        super().__init__(f"File not in repository: {file_path}")
        self.file_path = file_path


class InvalidChecksumError(IndexingError):
    """Raised when file checksum doesn't match."""

    def __init__(self, file_path: str, expected: str, actual: str) -> None:
        super().__init__(f"Checksum mismatch for {file_path}: expected {expected}, got {actual}")
        self.file_path = file_path
        self.expected = expected
        self.actual = actual


class ProjectNotFoundError(CodeContextError):
    """Raised when a project is not found."""

    def __init__(self, project: str, suggestions: list[tuple[str, str]] | None = None) -> None:
        """Initialize ProjectNotFoundError.

        Args:
            project: The project name or ID that was not found
            suggestions: List of (collection_id, name) tuples for similar projects
        """
        self.project = project
        self.suggestions = suggestions or []

        if self.suggestions:
            suggestion_lines = [f"  - {name} ({cid})" for cid, name in self.suggestions[:3]]
            suggestion_text = "\n".join(suggestion_lines)
            message = (
                f"Project '{project}' not found.\n\n"
                f"Did you mean:\n{suggestion_text}\n\n"
                f"Use 'codecontext list-projects' to see all available projects."
            )
        else:
            message = (
                f"Project '{project}' not found.\n\n"
                f"Use 'codecontext list-projects' to see all available projects."
            )

        super().__init__(message)


class EmptyQueryError(SearchError):
    """Raised when search query is empty."""

    def __init__(self) -> None:
        super().__init__(
            "Search query cannot be empty.\n\n"
            'Usage: codecontext search "your query"\n'
            'Example: codecontext search "user authentication"'
        )
