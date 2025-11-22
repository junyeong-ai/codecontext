"""Configuration management commands."""

import json
import os
import subprocess

import toml
import typer

from codecontext.config.settings import get_config_path, get_data_dir, get_settings


def init() -> None:
    """Initialize global configuration file."""
    path = get_config_path()
    template = """# CodeContext Configuration

[embeddings]
provider = "huggingface"

[embeddings.huggingface]
device = "cpu"  # Use "cpu" | "cuda" | "mps" - "auto" may cause MPS issues on macOS
model_name = "jinaai/jina-code-embeddings-0.5b"

[storage]
provider = "qdrant"

[storage.qdrant]
mode = "embedded"  # embedded | remote
path = "~/.codecontext/data"
fusion_method = "rrf"  # rrf | dbsf
upsert_batch_size = 100  # 10-1000

# For remote mode:
# [storage.qdrant]
# mode = "remote"
# url = "http://localhost:6333"
# api_key = "your-api-key"

[search]
enable_graph_expansion = true
graph_max_hops = 1
graph_ppr_threshold = 0.4
max_chunks_per_file = 2

[translation]
enabled = true

[indexing]
parallel_workers = 0  # 0 = auto
"""

    if path.exists():
        typer.echo(f"Config already exists: {path}", err=True)
        raise typer.Exit(1)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template)

    if os.name == "posix":
        os.chmod(path, 0o600)

    typer.echo(f"Created: {path}")


def show(
    json_format: bool = typer.Option(False, "--json", help="Output as JSON"),
    effective: bool = typer.Option(False, "--effective", help="Show merged config"),
) -> None:
    """Display configuration."""
    settings = get_settings()
    config = settings.load()

    if effective:
        output = config.model_dump()
    else:
        if get_config_path().exists():
            output = toml.load(get_config_path())
        else:
            typer.echo("No global config found", err=True)
            raise typer.Exit(1)

    if json_format:
        typer.echo(json.dumps(output, indent=2, default=str))
    else:
        typer.echo(toml.dumps(output))


def path(data: bool = typer.Option(False, "--data", help="Show data directory")) -> None:
    """Print configuration path."""
    if data:
        typer.echo(get_data_dir())
    else:
        typer.echo(get_config_path())


def edit() -> None:
    """Edit global configuration file."""
    config_path = get_config_path()

    if not config_path.exists():
        typer.echo(
            f"Config not found: {config_path}\\nRun: codecontext config init",
            err=True,
        )
        raise typer.Exit(1)

    editor = os.getenv("EDITOR", "vim")
    subprocess.run([editor, str(config_path)])


def validate(
    strict: bool = typer.Option(False, "--strict", help="Enable strict validation"),
) -> None:
    """Validate configuration."""
    try:
        settings = get_settings()
        config = settings.load()
        typer.echo("✓ Configuration is valid")

        if strict:
            warnings = []
            if (
                config.embeddings.huggingface.batch_size
                and config.embeddings.huggingface.batch_size > 256
            ):
                warnings.append("⚠ batch_size > 256 may cause OOM")

            if warnings:
                for w in warnings:
                    typer.echo(w, err=True)
    except Exception as e:
        typer.echo(f"✗ Invalid configuration: {e}", err=True)
        raise typer.Exit(1) from e
