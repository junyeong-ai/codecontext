"""CLI command initialization helpers.

Centralizes common initialization logic across all CLI commands to reduce
code duplication and improve maintainability.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from codecontext.config.schema import Config
from codecontext.config.settings import get_settings
from codecontext.embeddings.factory import create_embedding_provider
from codecontext.storage.factory import create_storage_provider
from codecontext.translation import create_translation_provider
from codecontext.utils.logging import setup_logging
from codecontext.utils.project import get_project_id, normalize_project_id

if TYPE_CHECKING:
    from codecontext_core import VectorStore
    from codecontext_core.interfaces import EmbeddingProvider, TranslationProvider


@dataclass
class CommandContext:
    """Container for initialized CLI command components.

    This class holds all the components needed by CLI commands:
    - Configuration
    - Project ID
    - Storage provider
    - Optional embedding provider
    - Optional translation provider

    Example:
        >>> ctx = initialize_command(project="my-project", need_embedding=True)
        >>> ctx.storage.get_statistics()
        >>> ctx.embedding_provider.embed(["text"])
    """

    config: Config
    """Loaded configuration from settings."""

    project_id: str
    """Normalized project identifier."""

    storage: "VectorStore"
    """Initialized vector storage provider."""

    embedding_provider: "EmbeddingProvider | None" = None
    """Optional embedding provider (only if need_embedding=True)."""

    translation_provider: "TranslationProvider | None" = None
    """Optional translation provider (only if translation.enabled=True)."""


def initialize_command(
    project: str | None = None,
    path: Path | None = None,
    need_embedding: bool = False,
    enable_logging: bool = True,
) -> CommandContext:
    """Initialize common CLI command components.

    This function centralizes the initialization logic that is repeated across
    all CLI commands. It loads configuration, detects/normalizes project ID,
    creates storage provider, and optionally creates embedding provider.

    Args:
        project: Optional project ID override (uses detection if None)
        path: Optional path for project detection (uses cwd if None)
        need_embedding: Whether to create embedding provider
        enable_logging: Whether to enable logging (False for JSON output)

    Returns:
        CommandContext with initialized components

    Raises:
        ConfigurationError: If configuration is invalid
        StorageError: If storage initialization fails
        CodeContextError: For other initialization errors

    Example:
        >>> # Minimal initialization (status command)
        >>> ctx = initialize_command()

        >>> # With embedding provider (index, search commands)
        >>> ctx = initialize_command(need_embedding=True)

        >>> # With custom project and path
        >>> ctx = initialize_command(
        ...     project="my-project",
        ...     path=Path("/path/to/repo"),
        ...     need_embedding=True
        ... )
    """
    # Load configuration with project path for .codecontext.toml discovery
    from codecontext.config.settings import reset_settings

    reset_settings()  # Ensure fresh settings for each command
    settings = get_settings(project_path=path)
    config = settings.load()

    # Setup logging (can be disabled for JSON output)
    if enable_logging:
        setup_logging(config.logging)

    # Detect or use provided project ID
    if project:
        project_id = project
    else:
        detect_path = path if path is not None else Path.cwd()
        project_id = get_project_id(detect_path)

    # Normalize project ID
    project_id = normalize_project_id(project_id)

    # Create embedding provider if needed
    embedding_provider = None
    if need_embedding:
        embedding_provider = create_embedding_provider(config.embeddings)

    # Create translation provider if enabled
    translation_provider = None
    if config.translation.enabled:
        translation_provider = create_translation_provider(config.translation)

    # Create and initialize storage
    storage = create_storage_provider(config, project_id, embedding_provider)
    try:
        storage.initialize()
    except Exception as e:
        error_msg = str(e)
        if not need_embedding and "Embedding provider required" in error_msg:
            pass
        elif "doesn't exist" in error_msg or "Not found" in error_msg:
            pass
        else:
            raise

    return CommandContext(
        config=config,
        project_id=project_id,
        storage=storage,
        embedding_provider=embedding_provider,
        translation_provider=translation_provider,
    )
