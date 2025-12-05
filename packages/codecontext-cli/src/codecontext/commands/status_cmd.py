"""Status command implementation."""

import logging

import typer
from codecontext_core.exceptions import CodeContextError, ProjectNotFoundError
from rich.console import Console
from rich.panel import Panel

from codecontext.utils.cli_context import initialize_command
from codecontext.utils.project_registry import get_project_registry

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
        # Initialize command context (no embedding provider needed, no logging)
        ctx = initialize_command(project=project, enable_logging=False)

        # Get index state
        state = ctx.storage.get_index_state()

        if state is None:
            # Check if collection exists but no state yet (indexing in progress)
            try:
                stats = ctx.storage.get_statistics()
            except Exception as e:
                if "doesn't exist" in str(e) or "Not found" in str(e):
                    console.print(
                        f"[yellow]No index found for project '{ctx.project_id}'.\n"
                        f"Run 'codecontext index' in the repository directory or\n"
                        f"'codecontext index --project <name>' to create one.[/yellow]"
                    )
                    raise typer.Exit(code=0)
                raise

            if stats.get("content_count", 0) > 0:
                registry = get_project_registry()
                project_info = registry.get_project(ctx.project_id)
                display_name = project_info.name if project_info else ctx.project_id
                console.print(
                    Panel.fit(
                        f"[bold yellow]Indexing in Progress[/bold yellow]\n"
                        f"Project: {display_name} ({ctx.project_id})\n"
                        f"Content objects: {stats.get('content_count', 0)}\n"
                        f"\nThe index is currently being built. "
                        f"Run this command again when indexing is complete.",
                        border_style="yellow",
                    )
                )
            else:
                console.print(
                    f"[yellow]No index found for project '{ctx.project_id}'.\n"
                    f"Run 'codecontext index' in the repository directory or\n"
                    f"'codecontext index --project <name>' to create one.[/yellow]"
                )
            raise typer.Exit(code=0)

        # Get statistics
        stats = ctx.storage.get_statistics()

        # Convert IndexState to dict if needed
        if hasattr(state, "to_metadata"):
            state_dict = state.to_metadata()
        elif isinstance(state, dict):
            state_dict = state
        else:
            console.print(
                f"[bold red]Error:[/bold red] Invalid state format. "
                f"Expected IndexState or dict, got {type(state).__name__}",
                style="red",
            )
            raise typer.Exit(code=1)

        # Extract state information
        project_id = state_dict.get("project_id", "Unknown")
        project_name = state_dict.get("project_name", "")
        repository_path = state_dict.get("repository_path", "Unknown")
        status_value = state_dict.get("status", "unknown")
        last_indexed = state_dict.get("last_indexed_at", "Never")
        last_commit = (
            state_dict.get("last_commit_hash", "")[:8]
            if state_dict.get("last_commit_hash")
            else "N/A"
        )
        total_files = state_dict.get("total_files", 0)

        # Parse languages (can be string or list)
        languages = state_dict.get("languages", "")
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
                pass

        # Display project with name if available
        project_display = f"{project_name} ({project_id})" if project_name else project_id

        # Display status
        console.print(
            Panel.fit(
                f"[bold blue]CodeContext Index Status[/bold blue]\n"
                f"Project: {project_display}\n"
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
            console.print(f"Index version: {state_dict.get('index_version', 'Unknown')}")
            console.print(f"Total objects: {state_dict.get('total_objects', 0)}")
            console.print(f"Meta collection size: {stats.get('meta_count', 0)}")

        ctx.storage.close()

    except ProjectNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None
    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None
