"""Translation provider factory with plugin discovery."""

import asyncio
import logging
from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

from codecontext_core.exceptions import ConfigurationError
from codecontext_core.interfaces import TranslationProvider

logger = logging.getLogger(__name__)


def get_available_providers() -> dict[str, Callable[[Any], TranslationProvider]]:
    """Discover available translation providers via entry points.

    Returns:
        Dictionary mapping provider names to provider classes

    Note:
        Providers register via entry points in their pyproject.toml:
        [project.entry-points."codecontext.translation"]
        nllb = "codecontext_translation_nllb.provider:NLLBProvider"
    """
    providers = {}
    for ep in entry_points(group="codecontext.translation"):
        try:
            providers[ep.name] = ep.load()
        except (ImportError, AttributeError, ValueError) as e:
            logger.warning(f"Failed to load translation provider '{ep.name}': {e}")
    return providers


class TranslationFactory:
    """Factory for creating translation providers with plugin discovery."""

    @staticmethod
    def create_provider(config: Any) -> TranslationProvider:
        """Create a translation provider based on configuration.

        Args:
            config: Translation configuration

        Returns:
            Translation provider instance

        Raises:
            ConfigurationError: If provider type is not supported or not installed
        """
        provider_type = config.provider.lower()
        available_providers = get_available_providers()

        if provider_type not in available_providers:
            installed = ", ".join(available_providers.keys()) if available_providers else "none"
            msg = (
                f"Translation provider '{provider_type}' not found. "
                f"Installed providers: {installed}. "
                f"Install with: pip install codecontext-translation-{provider_type}"
            )
            raise ConfigurationError(msg)

        provider_class = available_providers[provider_type]

        # Get provider-specific config
        provider_config = getattr(config, provider_type, None)
        if provider_config is None:
            msg = f"Configuration for provider '{provider_type}' not found"
            raise ConfigurationError(msg)

        return provider_class(provider_config)


def create_translation_provider(config: Any) -> TranslationProvider | None:
    """Convenience function to create and initialize translation provider.

    Args:
        config: Translation configuration

    Returns:
        Fully initialized translation provider instance or None if disabled
    """
    if not getattr(config, "enabled", True):
        return None

    provider = TranslationFactory.create_provider(config)

    # Initialize provider
    if hasattr(provider, "initialize"):
        asyncio.run(provider.initialize())

    return provider
