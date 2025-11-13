"""Project management commands implementation."""

import typer
from rich.console import Console
from rich.panel import Panel

from codecontext.config.settings import get_settings
import logging

from codecontext_core.exceptions import CodeContextError
from codecontext.storage.factory import create_storage_provider
from codecontext.utils.logging import setup_logging
from codecontext.utils.project_identifier import ProjectIdentifier

console = Console()
logger = logging.getLogger(__name__)


def list_projects() -> None:
    """
    List all indexed projects with their statistics.

    Shows all projects that have been indexed in ChromaDB with their
    current status and basic information.
    """
    try:
        # Load configuration
        settings = get_settings()
        config = settings.load()
        setup_logging(config.logging)

        # Connect to ChromaDB to list all collections
        from codecontext.storage.admin import ChromaDBAdminClient

        client = ChromaDBAdminClient(
            host=config.storage.chromadb.host, port=config.storage.chromadb.port
        )

        try:
            client.heartbeat()
        except (ConnectionError, OSError, RuntimeError) as e:
            console.print(
                f"[bold red]Error:[/bold red] Cannot connect to ChromaDB: {e}", style="red"
            )
            console.print("\n[yellow]Make sure ChromaDB server is running:[/yellow]")
            console.print("  ./scripts/chroma-cli.sh start")
            raise typer.Exit(code=1) from None

        # Get all collections and extract project IDs
        collections = client.list_collections()
        base_name = config.storage.chromadb.collection_name

        # Extract unique project IDs from collection names
        # Format: codecontext_index_{project_id}_state
        project_ids = set()
        for coll in collections:
            coll_name = coll.get("name", "") if isinstance(coll, dict) else str(coll)
            if coll_name.startswith(f"{base_name}_") and coll_name.endswith("_state"):
                # Extract project_id from collection name
                parts = coll_name[len(base_name) + 1 :].rsplit("_state", 1)
                if parts and parts[0]:
                    project_ids.add(parts[0])

        if not project_ids:
            console.print("[yellow]No indexed projects found.[/yellow]")
            console.print("Run 'codecontext index' to index a project.")
            raise typer.Exit(code=0)

        console.print(f"\n[bold]Found {len(project_ids)} project(s):[/bold]\n")

        # Display each project
        for project_id in sorted(project_ids):
            try:
                storage = create_storage_provider(config.storage, project_id)
                storage.initialize()
                state = storage.get_index_state()
                stats = storage.get_statistics()

                if state:
                    console.print(
                        Panel.fit(
                            f"[bold cyan]{project_id}[/bold cyan]\n"
                            f"Path: {state.repository_path}\n"
                            f"Last indexed: {state.last_indexed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"Files: {state.total_files} | "
                            f"Content: {stats.get('content_count', 0)} | "
                            f"Meta: {stats.get('meta_count', 0)}",
                            border_style="cyan",
                        )
                    )
                storage.close()
            except (ConnectionError, OSError, RuntimeError, ValueError) as e:
                console.print(
                    f"[yellow]Warning: Could not load project '{project_id}': {e}[/yellow]"
                )

    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None


def delete_project(
    project: str = typer.Argument(..., help="Project name to delete"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Delete all indexes for a specific project.

    WARNING: This operation cannot be undone. All indexed data for the
    specified project will be permanently deleted from ChromaDB.
    """
    try:
        # Load configuration
        settings = get_settings()
        config = settings.load()
        setup_logging(config.logging)

        # Normalize project ID
        project_id = ProjectIdentifier.normalize(project)

        # Confirm deletion
        if not yes:
            confirm = typer.confirm(
                f"Are you sure you want to delete all indexes for project '{project_id}'?"
            )
            if not confirm:
                console.print("[yellow]Deletion cancelled.[/yellow]")
                raise typer.Exit(code=0)

        # Connect to ChromaDB
        from codecontext.storage.admin import ChromaDBAdminClient

        client = ChromaDBAdminClient(
            host=config.storage.chromadb.host, port=config.storage.chromadb.port
        )

        try:
            client.heartbeat()
        except (ConnectionError, OSError, RuntimeError) as e:
            console.print(
                f"[bold red]Error:[/bold red] Cannot connect to ChromaDB: {e}", style="red"
            )
            console.print("\n[yellow]Make sure ChromaDB server is running:[/yellow]")
            console.print("  ./scripts/chroma-cli.sh start")
            raise typer.Exit(code=1) from None

        # Delete all project-specific collections
        base_name = config.storage.chromadb.collection_name
        collection_suffixes = ["code_objects", "documents", "relationships", "state"]
        deleted_count = 0

        for suffix in collection_suffixes:
            collection_name = f"{base_name}_{project_id}_{suffix}"
            try:
                client.delete_collection(collection_name)
                deleted_count += 1
                console.print(f"[green]✓[/green] Deleted collection: {collection_name}")
            except (ValueError, KeyError, RuntimeError) as e:
                logger.debug(f"Collection {collection_name} not found or already deleted: {e}")

        if deleted_count == 0:
            console.print(f"[yellow]No collections found for project '{project_id}'.[/yellow]")
        else:
            console.print(
                f"\n[bold green]Success![/bold green] Deleted {deleted_count} "
                f"collection(s) for project '{project_id}'."
            )

    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None
