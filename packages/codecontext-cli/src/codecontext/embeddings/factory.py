"""Embedding provider factory with plugin discovery."""

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

from codecontext_core.exceptions import ConfigurationError
from codecontext_core.interfaces import EmbeddingProvider

from codecontext.config.schema import EmbeddingConfig


def get_available_providers() -> dict[str, Callable[[Any], EmbeddingProvider]]:
    """
    Discover available embedding providers via entry points.

    Returns:
        Dictionary mapping provider names to provider classes

    Note:
        Providers register via entry points in their pyproject.toml:
        [project.entry-points."codecontext.embeddings"]
        huggingface = "codecontext_embeddings_huggingface.provider:HuggingFaceEmbeddingProvider"
    """
    providers = {}
    for ep in entry_points(group="codecontext.embeddings"):
        try:
            providers[ep.name] = ep.load()
        except (ImportError, AttributeError, ValueError) as e:
            # Log warning but don't fail - allow other providers to load
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to load embedding provider '{ep.name}': {e}"
            )
    return providers


class EmbeddingFactory:
    """Factory for creating embedding providers with plugin discovery."""

    @staticmethod
    def create_provider(config: EmbeddingConfig) -> EmbeddingProvider:
        """
        Create an embedding provider based on configuration.

        Args:
            config: Embedding configuration

        Returns:
            Embedding provider instance

        Raises:
            ConfigurationError: If provider type is not supported or not installed
        """
        provider_type = config.provider.lower()
        available_providers = get_available_providers()

        if provider_type not in available_providers:
            installed = ", ".join(available_providers.keys()) if available_providers else "none"
            msg = (
                f"Embedding provider '{provider_type}' not found. "
                f"Installed providers: {installed}. "
                f"Install with: pip install codecontext-embeddings-{provider_type}"
            )
            raise ConfigurationError(msg)

        provider_class = available_providers[provider_type]

        # Get provider-specific config
        provider_config = getattr(config, provider_type, None)
        if provider_config is None:
            msg = f"Configuration for provider '{provider_type}' not found"
            raise ConfigurationError(msg)

        # MyPy doesn't know provider_class is a concrete implementation (loaded via entry points)
        return provider_class(provider_config)


def create_embedding_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    """
    Convenience function to create and initialize embedding provider.

    Args:
        config: Embedding configuration

    Returns:
        Fully initialized embedding provider instance
    """
    import asyncio

    provider = EmbeddingFactory.create_provider(config)

    # Initialize provider synchronously (required for CLI commands)
    if hasattr(provider, "initialize"):
        asyncio.run(provider.initialize())

    return provider
