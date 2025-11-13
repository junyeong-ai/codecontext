"""Status command implementation."""

import typer
from rich.console import Console
from rich.panel import Panel

import logging

from codecontext_core.exceptions import CodeContextError
from codecontext.utils.cli_context import initialize_command

console = Console()
logger = logging.getLogger(__name__)


def status(
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Project name (auto-detected from current directory if not specified)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed statistics",
    ),
) -> None:
    """
    Show index status and statistics for a specific project.

    Displays information about the current index state including
    number of indexed files, code objects, and last sync time.
    """
    try:
        # Initialize command context (no embedding provider needed)
        ctx = initialize_command(project=project)

        # Get index state
        state = ctx.storage.get_index_state()

        if state is None:
            console.print(
                f"[yellow]No index found for project '{ctx.project_id}'. "
                f"Run 'codecontext index --project {ctx.project_id}' to create one.[/yellow]"
            )
            raise typer.Exit(code=0)

        # Get statistics
        stats = ctx.storage.get_statistics()

        # Storage always returns dict (clean design, no legacy support)
        if not isinstance(state, dict):
            console.print(
                f"[bold red]Error:[/bold red] Invalid state format. "
                f"Expected dict, got {type(state).__name__}",
                style="red",
            )
            raise typer.Exit(code=1)

        # Extract state information
        project_id = state.get("project_id", "Unknown")
        repository_path = state.get("repository_path", "Unknown")
        status_value = state.get("status", "unknown")
        last_indexed = state.get("last_indexed_at", "Never")
        last_commit = (
            state.get("last_commit_hash", "")[:8] if state.get("last_commit_hash") else "N/A"
        )
        total_files = state.get("total_files", 0)

        # Parse languages (can be string or list)
        languages = state.get("languages", "")
        if isinstance(languages, str):
            languages = languages.split(",") if languages else []
        elif not isinstance(languages, list):
            languages = []

        # Format last indexed time
        if isinstance(last_indexed, str) and last_indexed != "Never":
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(last_indexed.replace("Z", "+00:00"))
                last_indexed = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                pass  # Keep original if parsing fails

        # Display status
        console.print(
            Panel.fit(
                f"[bold blue]CodeContext Index Status[/bold blue]\n"
                f"Project: {project_id}\n"
                f"Repository: {repository_path}\n"
                f"Status: {status_value}\n"
                f"Last indexed: {last_indexed}\n"
                f"Commit: {last_commit}\n"
                f"\n[bold]Statistics:[/bold]\n"
                f"Files: {total_files}\n"
                f"Content items: {stats.get('content_count', 0)}\n"
                f"Metadata items: {stats.get('meta_count', 0)}\n"
                f"Languages: {', '.join(languages) if languages else 'None'}",
                border_style="blue",
            )
        )

        if verbose:
            console.print("\n[bold]Detailed Statistics:[/bold]")
            console.print(f"Index version: {state.get('index_version', 'Unknown')}")
            console.print(f"Total objects: {state.get('total_objects', 0)}")
            console.print(f"Meta collection size: {stats.get('meta_count', 0)}")

        ctx.storage.close()

    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None
