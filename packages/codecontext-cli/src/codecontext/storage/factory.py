"""Storage provider factory with plugin discovery."""

from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any

from codecontext_core import VectorStore
from codecontext_core.exceptions import (
    ProviderNotFoundError,
)

from codecontext.config.schema import Config

if TYPE_CHECKING:
    from codecontext_core.interfaces import EmbeddingProvider


def get_available_providers() -> dict[str, Any]:
    """
    Discover available storage providers via entry points.

    Returns:
        Dictionary mapping provider names to provider classes

    Note:
        Providers register via entry points in their pyproject.toml:
        [project.entry-points."codecontext.storage"]
        qdrant = "codecontext_storage_qdrant.provider:QdrantProvider"
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
    def create_provider(
        config: Config, project_id: str, embedding_provider: "EmbeddingProvider | None" = None
    ) -> VectorStore:
        provider_type = config.storage.provider
        available_providers = get_available_providers()

        if provider_type not in available_providers:
            raise ProviderNotFoundError(provider_type, list(available_providers.keys()))

        provider_class = available_providers[provider_type]

        if provider_type == "qdrant":
            result: VectorStore = provider_class(
                config.storage.qdrant, project_id, config.indexing.field_weights, embedding_provider
            )
            return result
        else:
            raise ValueError(f"Unknown provider: {provider_type}")


def create_storage_provider(
    config: Config, project_id: str, embedding_provider: "EmbeddingProvider | None" = None
) -> VectorStore:
    """
    Convenience function to create storage provider.

    Args:
        config: Full configuration including storage and indexing settings
        project_id: Unique project identifier for collection isolation
        embedding_provider: Optional embedding provider for vector dimension detection

    Returns:
        Storage provider instance
    """
    return StorageFactory.create_provider(config, project_id, embedding_provider)
