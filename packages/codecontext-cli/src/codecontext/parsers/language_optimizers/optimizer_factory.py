"""Factory for creating language-specific optimizers."""

from codecontext.parsers.language_optimizers.base import LanguageOptimizer
from codecontext.parsers.language_optimizers.java_optimizer import JavaOptimizer
from codecontext.parsers.language_optimizers.kotlin_optimizer import KotlinOptimizer
from codecontext.parsers.language_optimizers.python_optimizer import PythonOptimizer
from codecontext.parsers.language_optimizers.typescript_optimizer import TypeScriptOptimizer


class LanguageOptimizerFactory:
    """Factory for creating and managing language-specific optimizers."""

    def __init__(self) -> None:
        """Initialize with available optimizers."""
        self._optimizers: dict[str, LanguageOptimizer] = {
            "python": PythonOptimizer(),
            "java": JavaOptimizer(),
            "kotlin": KotlinOptimizer(),
            "typescript": TypeScriptOptimizer(),
            # JavaScript shares TypeScript optimizer for now
            "javascript": TypeScriptOptimizer(),
        }

    def get_optimizer(self, language: str) -> LanguageOptimizer | None:
        """
        Get optimizer for a specific language.

        Args:
            language: Programming language name

        Returns:
            Language optimizer or None if not available
        """
        return self._optimizers.get(language.lower(), None)

    def has_optimizer(self, language: str) -> bool:
        """
        Check if an optimizer exists for a language.

        Args:
            language: Programming language name

        Returns:
            True if optimizer exists
        """
        return language.lower() in self._optimizers

    def register_optimizer(self, language: str, optimizer: LanguageOptimizer) -> None:
        """
        Register a custom optimizer for a language.

        Args:
            language: Programming language name
            optimizer: The optimizer instance
        """
        self._optimizers[language.lower()] = optimizer

    def get_supported_languages(self) -> list[str]:
        """
        Get list of languages with optimizers.

        Returns:
            List of supported language names
        """
        return list(self._optimizers.keys())


# Global factory instance
_factory = LanguageOptimizerFactory()


def get_optimizer(language: str) -> LanguageOptimizer | None:
    """
    Get optimizer for a language using the global factory.

    Args:
        language: Programming language name

    Returns:
        Language optimizer or None if not available
    """
    return _factory.get_optimizer(language)


def register_optimizer(language: str, optimizer: LanguageOptimizer) -> None:
    """
    Register a custom optimizer with the global factory.

    Args:
        language: Programming language name
        optimizer: The optimizer instance
    """
    _factory.register_optimizer(language, optimizer)
