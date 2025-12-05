"""Project management commands implementation."""

import typer
from codecontext_core.exceptions import CodeContextError, ProjectNotFoundError
from rich.console import Console
from rich.panel import Panel

from codecontext.config.settings import get_settings
from codecontext.utils.project_registry import get_project_registry

console = Console()


def list_projects() -> None:
    """
    List all indexed projects with their statistics.

    Shows all projects that have been indexed with their
    current status and basic information.
    """
    try:
        registry = get_project_registry()
        projects = registry.list_projects()

        if not projects:
            console.print("[yellow]No indexed projects found.[/yellow]")
            console.print("Run 'codecontext index' to index a project.")
            raise typer.Exit(code=0)

        console.print(f"\n[bold]Found {len(projects)} project(s):[/bold]\n")

        for project in projects:
            if project.total_objects > 0 or project.repository_path:
                # Fully indexed project
                info_lines = [
                    f"[bold cyan]{project.name}[/bold cyan] [dim]({project.collection_id})[/dim]"
                ]
                if project.repository_path:
                    info_lines.append(f"Path: {project.repository_path}")
                if project.last_indexed:
                    info_lines.append(f"Last indexed: {project.last_indexed}")
                if project.total_files > 0 or project.total_objects > 0:
                    info_lines.append(
                        f"Files: {project.total_files} | Content objects: {project.total_objects}"
                    )

                console.print(Panel.fit("\n".join(info_lines), border_style="cyan"))
            else:
                # Partially indexed or empty project
                info_text = (
                    f"[bold cyan]{project.name}[/bold cyan] [dim]({project.collection_id})[/dim]\n"
                    f"Status: Indexing in progress\n"
                    f"Content objects: {project.total_objects}"
                )
                console.print(Panel.fit(info_text, border_style="yellow"))

    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None


def delete_project(
    project: str = typer.Argument(..., help="Project name or collection ID to delete"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Delete all indexes for a specific project.

    You can specify either the project name or collection ID.

    WARNING: This operation cannot be undone. All indexed data for the
    specified project will be permanently deleted.
    """
    try:
        settings = get_settings()
        config = settings.load()

        if config.storage.provider != "qdrant":
            console.print(
                "[bold red]Error:[/bold red] Only Qdrant storage is supported", style="red"
            )
            raise typer.Exit(code=1)

        # Resolve project name to collection ID
        registry = get_project_registry()
        collection_id = registry.resolve_project_id(project)

        if not collection_id:
            similar = registry.find_similar_projects(project)
            if similar:
                suggestions = [(p.collection_id, p.name) for p in similar[:3]]
                raise ProjectNotFoundError(project, suggestions)
            else:
                raise ProjectNotFoundError(project)

        project_info = registry.get_project(collection_id)
        display_name = f"{project_info.name} ({collection_id})" if project_info else collection_id

        # Confirm deletion
        if not yes:
            confirm = typer.confirm(
                f"Are you sure you want to delete all indexes for project '{display_name}'?"
            )
            if not confirm:
                console.print("[yellow]Deletion cancelled.[/yellow]")
                raise typer.Exit(code=0)

        # Delete based on storage mode
        if config.storage.qdrant.mode == "embedded":
            import shutil
            from pathlib import Path

            storage_path = Path(config.storage.qdrant.path).expanduser()
            project_path = storage_path / collection_id

            if project_path.exists():
                shutil.rmtree(project_path)

            # Also remove metadata
            from codecontext.config.settings import get_data_dir

            metadata_path = get_data_dir() / collection_id
            if metadata_path.exists():
                shutil.rmtree(metadata_path)

            console.print(f"[bold green]Success![/bold green] Deleted project '{display_name}'.")
        else:
            # Remote mode: delete collection from Qdrant server
            from qdrant_client import QdrantClient

            client = QdrantClient(
                url=config.storage.qdrant.url, api_key=config.storage.qdrant.api_key
            )

            try:
                client.delete_collection(collection_id)

                # Also remove metadata
                import shutil

                from codecontext.config.settings import get_data_dir

                metadata_path = get_data_dir() / collection_id
                if metadata_path.exists():
                    shutil.rmtree(metadata_path)

                console.print(
                    f"[bold green]Success![/bold green] Deleted project '{display_name}'."
                )
            except Exception as e:
                console.print(
                    f"[bold red]Error:[/bold red] Failed to delete project: {e}", style="red"
                )
                raise typer.Exit(code=1)
            finally:
                client.close()

        # Invalidate registry cache
        registry.invalidate_cache()

    except ProjectNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None
    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None
