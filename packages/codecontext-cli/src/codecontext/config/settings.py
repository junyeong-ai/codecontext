"""Configuration management for CodeContext CLI."""

import os
from pathlib import Path
from typing import Any, ClassVar

import yaml
from pydantic import ValidationError

from codecontext.config.schema import CodeContextConfig
from codecontext_core.exceptions import ConfigurationError


class Settings:
    """Manages CodeContext configuration from files and environment variables."""

    DEFAULT_CONFIG_LOCATIONS: ClassVar[list[Path]] = [
        Path.cwd() / ".codecontext.yaml",
        Path.cwd() / ".codecontext.yml",
        Path.home() / ".codecontext" / "config.yaml",
        Path.home() / ".codecontext" / "config.yml",
    ]

    ENV_PREFIX: ClassVar[str] = "CODECONTEXT_"

    def __init__(self, config_path: Path | None = None) -> None:
        """
        Initialize settings.

        Args:
            config_path: Optional path to config file. If None, searches default locations.

        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        self.config_path = config_path
        self._config: CodeContextConfig | None = None

    def load(self) -> CodeContextConfig:
        """
        Load configuration from file and environment variables.

        Returns:
            Loaded and validated configuration

        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        if self._config is not None:
            return self._config

        # Load from file
        config_dict = self._load_from_file()

        # Override with environment variables
        config_dict = self._apply_env_overrides(config_dict)

        # Validate and create config object
        try:
            self._config = CodeContextConfig(**config_dict)
        except ValidationError as e:
            msg = f"Configuration validation failed: {e}"
            raise ConfigurationError(msg) from e

        return self._config

    def _load_from_file(self) -> dict[str, Any]:
        """Load configuration from YAML file."""
        config_file = self._find_config_file()

        if config_file is None:
            # No config file found, use defaults
            return {}

        try:
            with config_file.open() as f:
                data = yaml.safe_load(f)
                return data if data is not None else {}
        except yaml.YAMLError as e:
            msg = f"Failed to parse config file {config_file}: {e}"
            raise ConfigurationError(msg) from e
        except OSError as e:
            msg = f"Failed to read config file {config_file}: {e}"
            raise ConfigurationError(msg) from e

    def _find_config_file(self) -> Path | None:
        """Find configuration file."""
        if self.config_path is not None:
            if not self.config_path.exists():
                msg = f"Config file not found: {self.config_path}"
                raise ConfigurationError(msg)
            return self.config_path

        # Check environment variable
        env_config = os.getenv("CODECONTEXT_CONFIG")
        if env_config is not None:
            env_path = Path(env_config)
            if not env_path.exists():
                msg = f"Config file from CODECONTEXT_CONFIG not found: {env_path}"
                raise ConfigurationError(msg)
            return env_path

        # Search default locations
        for location in self.DEFAULT_CONFIG_LOCATIONS:
            if location.exists():
                return location

        return None

    def _apply_env_overrides(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Apply environment variable overrides.

        Environment variables follow the pattern:
        CODECONTEXT_<section>_<key>=value

        Examples:
            CODECONTEXT_CHROMADB_HOST=localhost
            CODECONTEXT_CHROMADB_PORT=8000
            CODECONTEXT_LOG_LEVEL=DEBUG
        """
        self._apply_storage_overrides(config)
        self._apply_logging_overrides(config)
        self._apply_embedding_overrides(config)
        self._apply_indexing_overrides(config)
        return config

    def _apply_storage_overrides(self, config: dict[str, Any]) -> None:
        """Apply storage-related environment variable overrides."""
        host = os.getenv("CODECONTEXT_CHROMADB_HOST")
        if host is not None:
            config.setdefault("storage", {}).setdefault("chromadb", {})["host"] = host

        port_str = os.getenv("CODECONTEXT_CHROMADB_PORT")
        if port_str is not None:
            try:
                port = int(port_str)
                config.setdefault("storage", {}).setdefault("chromadb", {})["port"] = port
            except ValueError as e:
                msg = "CODECONTEXT_CHROMADB_PORT must be an integer"
                raise ConfigurationError(msg) from e

    def _apply_logging_overrides(self, config: dict[str, Any]) -> None:
        """Apply logging-related environment variable overrides."""
        log_level = os.getenv("CODECONTEXT_LOG_LEVEL")
        if log_level is not None:
            config.setdefault("logging", {})["level"] = log_level.upper()

    def _apply_embedding_overrides(self, config: dict[str, Any]) -> None:
        """Apply embedding-related environment variable overrides."""
        model_name = os.getenv("CODECONTEXT_EMBEDDING_MODEL")
        if model_name is not None:
            config.setdefault("embeddings", {}).setdefault("huggingface", {})[
                "model_name"
            ] = model_name

        device = os.getenv("CODECONTEXT_EMBEDDING_DEVICE")
        if device is not None:
            config.setdefault("embeddings", {}).setdefault("huggingface", {})["device"] = device

        num_workers_str = os.getenv("CODECONTEXT_EMBEDDING_NUM_WORKERS")
        if num_workers_str is not None:
            try:
                num_workers = int(num_workers_str)
                config.setdefault("embeddings", {}).setdefault("huggingface", {})[
                    "num_workers"
                ] = num_workers
            except ValueError as e:
                msg = "CODECONTEXT_EMBEDDING_NUM_WORKERS must be an integer"
                raise ConfigurationError(msg) from e

    def _apply_indexing_overrides(self, config: dict[str, Any]) -> None:
        """Apply indexing-related environment variable overrides."""
        batch_size_str = os.getenv("CODECONTEXT_BATCH_SIZE")
        if batch_size_str is not None:
            try:
                batch_size = int(batch_size_str)
                config.setdefault("indexing", {})["batch_size"] = batch_size
            except ValueError as e:
                msg = "CODECONTEXT_BATCH_SIZE must be an integer"
                raise ConfigurationError(msg) from e

    @property
    def config(self) -> CodeContextConfig:
        """
        Get current configuration.

        Returns:
            Current configuration (loads if not already loaded)
        """
        if self._config is None:
            return self.load()
        return self._config


# Global settings instance
_settings: Settings | None = None


def get_settings(config_path: Path | None = None) -> Settings:
    """
    Get global settings instance.

    Args:
        config_path: Optional path to config file

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings(config_path=config_path)
    return _settings
