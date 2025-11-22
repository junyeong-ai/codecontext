"""Logging configuration for CodeContext."""

import logging
import sys
from typing import Any

from codecontext.config.schema import LoggingConfig


def setup_logging(config: LoggingConfig) -> None:
    """
    Configure logging based on configuration.

    Configures all CodeContext package loggers to ensure consistent
    formatting across main package and provider packages.

    Args:
        config: Logging configuration
    """
    # Configure all package logger roots
    packages = [
        "codecontext",
        "codecontext_core",
        "codecontext_embeddings_huggingface",
        "codecontext_embeddings_openai",
        "codecontext_storage_qdrant",
        "codecontext_translation_nllb",
    ]

    # Create handler (shared across all loggers)
    handler: logging.FileHandler | logging.StreamHandler[Any]
    handler = (
        logging.FileHandler(config.file) if config.file else logging.StreamHandler[Any](sys.stderr)
    )

    # Set format
    if config.format == "json":
        # Simple JSON-like format
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s"}'
        )
    else:
        # Text format
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler.setFormatter(formatter)

    # Configure each package logger
    for package in packages:
        logger = logging.getLogger(package)
        logger.setLevel(config.level)

        # Close and remove existing handlers
        for old_handler in logger.handlers[:]:
            old_handler.close()
            logger.removeHandler(old_handler)

        # Add configured handler
        logger.addHandler(handler)

        # Prevent propagation to root logger (avoid duplicate logs)
        logger.propagate = False


class SuppressLoggingContext:
    """Complete logging suppression for clean programmatic output.

    Suppresses ALL logging output (CodeContext + third-party libraries)
    and redirects stderr temporarily. This ensures JSON/programmatic
    output is not polluted with logs or progress bars.

    Design:
    - Disables root logger (affects all loggers)
    - Redirects stderr to /dev/null (suppresses progress bars)
    - Restores everything on exit

    Example:
        >>> with SuppressLoggingContext():
        ...     # All logs and progress bars suppressed
        ...     search_results = search(query)
    """

    def __init__(self) -> None:
        """Initialize suppression context."""
        self.original_stderr = sys.stderr
        self.original_disable_level = logging.root.manager.disable

    def __enter__(self) -> "SuppressLoggingContext":
        """Enter context - suppress all logging and stderr."""
        # Disable ALL logging (root logger level)
        logging.disable(logging.CRITICAL)

        # Redirect stderr to /dev/null (suppresses progress bars, warnings)
        sys.stderr = open("/dev/null", "w")

        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: object,
    ) -> None:
        """Exit context - restore logging and stderr."""
        # Restore stderr
        sys.stderr.close()
        sys.stderr = self.original_stderr

        # Restore logging
        logging.disable(self.original_disable_level)
