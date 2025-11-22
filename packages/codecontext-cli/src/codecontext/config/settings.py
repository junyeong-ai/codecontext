"""Configuration management for CodeContext."""

import os
from pathlib import Path
from typing import Any

import toml
from codecontext_core.exceptions import ConfigurationError
from pydantic import ValidationError

from codecontext.config.schema import Config


def get_config_dir() -> Path:
    return Path.home() / ".codecontext"


def get_config_path() -> Path:
    return get_config_dir() / "config.toml"


def get_data_dir() -> Path:
    return get_config_dir() / "data"


def get_project_config_path() -> Path | None:
    current = Path.cwd()
    for parent in [current, *current.parents]:
        candidate = parent / ".codecontext.toml"
        if candidate.exists():
            return candidate
    return None


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge override into base recursively."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_toml(path: Path) -> dict[str, Any]:
    """Load TOML file."""
    try:
        with path.open() as f:
            return toml.load(f)
    except Exception as e:
        raise ConfigurationError(f"Failed to load {path}: {e}") from e


def load_from_env() -> dict[str, Any]:
    """Load configuration from environment variables."""
    config: dict[str, Any] = {}

    if device := os.getenv("CODECONTEXT_DEVICE"):
        config.setdefault("embeddings", {}).setdefault("huggingface", {})["device"] = device

    if batch := os.getenv("CODECONTEXT_BATCH_SIZE"):
        config.setdefault("embeddings", {}).setdefault("huggingface", {})["batch_size"] = int(batch)

    if model := os.getenv("CODECONTEXT_MODEL"):
        config.setdefault("embeddings", {}).setdefault("huggingface", {})["model_name"] = model

    if port := os.getenv("CODECONTEXT_PORT"):
        config.setdefault("storage", {})["port"] = int(port)

    if level := os.getenv("CODECONTEXT_LOG_LEVEL"):
        config.setdefault("logging", {})["level"] = level.upper()

    return config


class Settings:
    """Configuration loader with priority: CLI > ENV > Project > Global > Defaults."""

    def __init__(self, cli_overrides: dict[str, Any] | None = None) -> None:
        self.cli_overrides = cli_overrides or {}
        self._config: Config | None = None

    def load(self) -> Config:
        """Load and merge configuration from all sources."""
        if self._config:
            return self._config

        config_dict: dict[str, Any] = {}

        # 1. Global config
        if get_config_path().exists():
            global_config = load_toml(get_config_path())
            config_dict = deep_merge(config_dict, global_config)

        # 2. Environment override: CODECONTEXT_CONFIG for test isolation
        if config_env_path := os.getenv("CODECONTEXT_CONFIG"):
            env_config_file = Path(config_env_path)
            if env_config_file.exists():
                env_file_config = load_toml(env_config_file)
                config_dict = deep_merge(config_dict, env_file_config)

        # 3. Project config (.codecontext.toml)
        if project_path := get_project_config_path():
            project_config = load_toml(project_path)
            config_dict = deep_merge(config_dict, project_config)

        # 4. Environment variables
        env_config = load_from_env()
        config_dict = deep_merge(config_dict, env_config)

        # 5. CLI overrides
        config_dict = deep_merge(config_dict, self.cli_overrides)

        try:
            self._config = Config(**config_dict)
        except ValidationError as e:
            raise ConfigurationError(f"Invalid configuration: {e}") from e

        return self._config

    @property
    def config(self) -> Config:
        if not self._config:
            return self.load()
        return self._config


_settings: Settings | None = None


def get_settings(cli_overrides: dict[str, Any] | None = None) -> Settings:
    global _settings
    if not _settings:
        _settings = Settings(cli_overrides)
    return _settings
