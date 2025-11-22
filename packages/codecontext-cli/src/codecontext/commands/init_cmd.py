"""Init command - Initialize CodeContext for a project."""

from pathlib import Path

import toml
import typer
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
    yes: bool = typer.Option(
        False,
        "-y",
        "--yes",
        help="Skip confirmation",
    ),
) -> None:
    """
    Initialize CodeContext for a project.

    Analyzes project structure and creates .codecontext.toml configuration.

    Examples:

        # Interactive setup (recommended)
        codecontext init

        # Include test directories
        codecontext init --include-tests

        # Non-interactive
        codecontext init -y
    """
    try:
        path = path.resolve()

        # Check if already initialized
        config_file = path / ".codecontext.toml"
        if config_file.exists() and not yes:
            if not Confirm.ask(
                "\n[yellow].codecontext.toml already exists.[/yellow]\nOverwrite?",
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

        # Generate config
        config = {
            "project": {
                "name": path.name,
                "include": result.recommended_includes,
                "exclude": result.recommended_excludes,
            },
        }

        # Add indexing config based on detected modules
        if result.modules:
            # Detect languages from module types
            languages = set()
            for module in result.modules:
                if module.type == "gradle":
                    languages.update(["kotlin", "java"])
                elif module.type == "maven":
                    languages.add("java")
                elif module.type == "npm":
                    languages.update(["javascript", "typescript"])
                elif module.type == "python":
                    languages.add("python")

            if languages:
                config["indexing"] = {"languages": sorted(languages)}

        # Write config file
        with open(config_file, "w") as f:
            toml.dump(config, f)

        # Success message
        console.print(f"\n[green]✓ Created:[/green] {config_file}")
        console.print("\n[dim]You can edit this file to customize patterns.[/dim]")

        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. [dim]codecontext index[/dim]")
        console.print('  2. [dim]codecontext search "your query"[/dim]')

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
