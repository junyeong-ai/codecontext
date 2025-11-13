"""Storage provider factory with plugin discovery."""

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

from codecontext.config.schema import StorageConfig
from codecontext_core.exceptions import (
    ProviderConfigurationNotFoundError,
    ProviderNotFoundError,
)
from codecontext_core import VectorStore


def get_available_providers() -> dict[str, Callable[[Any, str], VectorStore]]:
    """
    Discover available storage providers via entry points.

    Returns:
        Dictionary mapping provider names to provider classes

    Note:
        Providers register via entry points in their pyproject.toml:
        [project.entry-points."codecontext.storage"]
        chromadb = "codecontext_storage_chromadb.provider:ChromaDBVectorStore"
    """
    providers = {}
    for ep in entry_points(group="codecontext.storage"):
        try:
            providers[ep.name] = ep.load()
        except (ImportError, AttributeError, ValueError) as e:
            # Log warning but don't fail - allow other providers to load
            import logging

            logging.getLogger(__name__).warning(f"Failed to load storage provider '{ep.name}': {e}")
    return providers


class StorageFactory:
    """Factory for creating storage providers with plugin discovery."""

    @staticmethod
    def create_provider(config: StorageConfig, project_id: str) -> VectorStore:
        """
        Create a storage provider based on configuration.

        Args:
            config: Storage configuration
            project_id: Unique project identifier for collection isolation

        Returns:
            Storage provider instance

        Raises:
            ConfigurationError: If provider type is not supported or not installed
        """
        provider_type = config.provider.lower()
        available_providers = get_available_providers()

        if provider_type not in available_providers:
            raise ProviderNotFoundError(provider_type, list(available_providers.keys()))

        provider_class = available_providers[provider_type]

        # Get provider-specific config
        provider_config = getattr(config, provider_type, None)
        if provider_config is None:
            raise ProviderConfigurationNotFoundError(provider_type)

        # Create provider with project_id
        return provider_class(provider_config, project_id)


def create_storage_provider(config: StorageConfig, project_id: str) -> VectorStore:
    """
    Convenience function to create storage provider.

    Args:
        config: Storage configuration
        project_id: Unique project identifier for collection isolation

    Returns:
        Storage provider instance
    """
    return StorageFactory.create_provider(config, project_id)
