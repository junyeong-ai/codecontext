"""Init command - Initialize CodeContext for a project."""

from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.prompt import Confirm

from codecontext.config.analyzer import ProjectAnalyzer

console = Console()


def init(
    path: Path = typer.Argument(
        Path.cwd(),
        help="Project directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    include_tests: bool = typer.Option(
        False,
        "--include-tests",
        help="Include test directories in indexing",
    ),
    local: bool = typer.Option(
        True,
        "--local/--remote",
        help="Use local ChromaDB (default: local)",
    ),
    remote: str | None = typer.Option(
        None,
        "--remote",
        help="Remote ChromaDB server (host:port)",
    ),
    yes: bool = typer.Option(
        False,
        "-y",
        "--yes",
        help="Skip confirmation",
    ),
) -> None:
    """
    Initialize CodeContext for a project.

    Analyzes project structure and creates .codecontext.yaml configuration.

    Examples:

        # Interactive setup (recommended)
        codecontext init

        # Include test directories
        codecontext init --include-tests

        # Use remote ChromaDB
        codecontext init --remote localhost:8100

        # Non-interactive
        codecontext init -y
    """
    try:
        path = path.resolve()

        # Check if already initialized
        config_file = path / ".codecontext.yaml"
        if config_file.exists() and not yes:
            if not Confirm.ask(
                "\n[yellow].codecontext.yaml already exists.[/yellow]\nOverwrite?",
                default=False,
            ):
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        # Analyze project structure
        console.print("\n[cyan]Analyzing project structure...[/cyan]")
        analyzer = ProjectAnalyzer(path)
        result = analyzer.analyze(include_tests=include_tests)

        # Show results
        console.print(f"\n[bold]Detected:[/bold] {result.type} project")

        if result.modules:
            console.print(f"\n[bold]Modules found:[/bold] {len(result.modules)}")
            for i, module in enumerate(result.modules[:10], 1):
                rel_path = module.path.relative_to(path)
                console.print(f"  {i}. {rel_path} ({module.type})")

            if len(result.modules) > 10:
                console.print(f"  ... and {len(result.modules) - 10} more")

        console.print("\n[bold]Recommended include patterns:[/bold]")
        for i, pattern in enumerate(result.recommended_includes[:15], 1):
            console.print(f"  {i}. {pattern}")

        if len(result.recommended_includes) > 15:
            console.print(f"  ... and {len(result.recommended_includes) - 15} more")

        # Confirm
        if not yes:
            if not Confirm.ask("\n[bold]Proceed with these patterns?[/bold]", default=True):
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        # Storage configuration
        storage_config = _build_storage_config(local, remote)

        # Generate config
        config = {
            "project": {
                "name": path.name,
                "type": result.type,
                "include": result.recommended_includes,
                "exclude": result.recommended_excludes,
            },
            "storage": storage_config,
        }

        # Write config file
        with open(config_file, "w") as f:
            yaml.dump(config, f, sort_keys=False, default_flow_style=False)

        # Setup local ChromaDB if needed
        if storage_config["mode"] == "local":
            _setup_local(path, storage_config["local"]["port"])

        # Update .gitignore
        _update_gitignore(path)

        # Success message
        console.print(f"\n[green]✓ Created:[/green] {config_file}")
        console.print("\n[dim]You can edit this file to customize patterns.[/dim]")

        console.print("\n[bold]Next steps:[/bold]")
        if storage_config["mode"] == "local":
            console.print("  1. [dim].codecontext/start-chroma.sh[/dim]")
            console.print("  2. [dim]codecontext index[/dim]")
            console.print('  3. [dim]codecontext search "your query"[/dim]')
        else:
            console.print("  1. [dim]codecontext index[/dim]")
            console.print('  2. [dim]codecontext search "your query"[/dim]')

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


def _build_storage_config(local: bool, remote: str | None) -> dict[str, Any]:
    """Build storage configuration."""
    if remote:
        # Parse remote spec
        if ":" in remote:
            host, port_str = remote.split(":", 1)
            port = int(port_str)
        else:
            host = remote
            port = 8000

        return {
            "mode": "remote",
            "remote": {
                "host": host,
                "port": port,
            },
        }
    else:
        return {
            "mode": "local",
            "local": {
                "path": ".codecontext/chroma",
                "port": 8000,
            },
        }


def _setup_local(path: Path, port: int) -> None:
    """Setup local ChromaDB."""
    codecontext_dir = path / ".codecontext"
    codecontext_dir.mkdir(exist_ok=True)

    chroma_dir = codecontext_dir / "chroma"
    chroma_dir.mkdir(exist_ok=True)

    # Create startup script
    script = codecontext_dir / "start-chroma.sh"
    script.write_text(
        f"""#!/usr/bin/env bash
# Auto-generated ChromaDB startup script

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
DATA_PATH="$SCRIPT_DIR/chroma"
PORT={port}

echo "Starting local ChromaDB server..."
echo "Data path: $DATA_PATH"
echo "Port: $PORT"
echo ""
echo "Press Ctrl+C to stop"

chroma run --path "$DATA_PATH" --port $PORT
"""
    )
    script.chmod(0o755)


def _update_gitignore(path: Path) -> None:
    """Update .gitignore with CodeContext patterns."""
    gitignore = path / ".gitignore"

    patterns = [
        "# CodeContext",
        ".codecontext/chroma/",
        ".codecontext/logs/",
        ".codecontext/*.pid",
    ]

    if gitignore.exists():
        content = gitignore.read_text()

        # Check if already has CodeContext patterns
        if ".codecontext" not in content:
            # Append patterns
            with open(gitignore, "a") as f:
                f.write("\n\n" + "\n".join(patterns) + "\n")
    else:
        # Create new .gitignore
        gitignore.write_text("\n".join(patterns) + "\n")
