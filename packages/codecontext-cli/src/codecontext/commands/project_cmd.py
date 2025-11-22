"""Project management commands implementation."""

import typer
from codecontext_core.exceptions import CodeContextError
from rich.console import Console

from codecontext.config.settings import get_settings

console = Console()


def list_projects() -> None:
    """
    List all indexed projects with their statistics.

    Shows all projects that have been indexed with their
    current status and basic information.
    """
    try:
        settings = get_settings()
        config = settings.load()

        if config.storage.provider != "qdrant":
            console.print(
                "[bold red]Error:[/bold red] Only Qdrant storage is supported", style="red"
            )
            raise typer.Exit(code=1)

        # Get storage path based on mode
        if config.storage.qdrant.mode == "embedded":
            from pathlib import Path

            storage_path = Path(config.storage.qdrant.path).expanduser()

            if not storage_path.exists():
                console.print("[yellow]No indexed projects found.[/yellow]")
                console.print("Run 'codecontext index' to index a project.")
                raise typer.Exit(code=0)

            # List all directories in storage path (each directory is a project)
            project_ids = [d.name for d in storage_path.iterdir() if d.is_dir()]

            if not project_ids:
                console.print("[yellow]No indexed projects found.[/yellow]")
                console.print("Run 'codecontext index' to index a project.")
                raise typer.Exit(code=0)

            console.print(f"\n[bold]Found {len(project_ids)} project(s):[/bold]\n")

            # Display each project
            for project_id in sorted(project_ids):
                try:
                    from codecontext.storage.factory import create_storage_provider

                    storage = create_storage_provider(config, project_id)
                    storage.initialize()

                    state = storage.get_index_state()
                    stats = storage.get_statistics()

                    # Display project info
                    if state:
                        from rich.panel import Panel

                        info_text = (
                            f"[bold cyan]{state.project_name or project_id}[/bold cyan] [dim]({project_id})[/dim]\n"
                            f"Path: {state.repository_path}\n"
                            f"Last indexed: {state.last_indexed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"Files: {state.total_files} | "
                            f"Content objects: {stats.get('content_count', 0)}"
                        )
                        console.print(Panel.fit(info_text, border_style="cyan"))
                    else:
                        from rich.panel import Panel

                        info_text = (
                            f"[bold cyan]{project_id}[/bold cyan]\n"
                            f"Status: Partially indexed\n"
                            f"Content objects: {stats.get('content_count', 0)}"
                        )
                        console.print(Panel.fit(info_text, border_style="yellow"))

                    storage.close()
                except Exception as e:
                    console.print(
                        f"[yellow]Warning: Could not load project '{project_id}': {e}[/yellow]"
                    )
        else:
            # Remote mode: list collections from Qdrant server
            from qdrant_client import QdrantClient

            client = QdrantClient(
                url=config.storage.qdrant.url, api_key=config.storage.qdrant.api_key
            )

            try:
                # Get all collections
                collections = client.get_collections().collections

                if not collections:
                    console.print("[yellow]No indexed projects found.[/yellow]")
                    console.print("Run 'codecontext index' to index a project.")
                    raise typer.Exit(code=0)

                console.print(f"\n[bold]Found {len(collections)} project(s):[/bold]\n")

                from rich.panel import Panel

                for collection in sorted(collections, key=lambda c: c.name):
                    collection_name = collection.name

                    try:
                        # Get collection info
                        collection_info = client.get_collection(collection_name)
                        points_count = collection_info.points_count

                        # Derive human-readable name from collection hash
                        from codecontext.utils.project import derive_project_name

                        display_name = derive_project_name(collection_name)

                        # Try to get index state
                        try:
                            from codecontext.storage.factory import create_storage_provider

                            storage = create_storage_provider(config, collection_name)
                            if hasattr(storage, "set_client"):
                                storage.set_client(client)
                            state = storage.get_index_state()

                            if state:
                                state_dict = (
                                    state.to_metadata() if hasattr(state, "to_metadata") else state
                                )
                                project_name = state_dict.get("project_id", "") or display_name
                                repo_path = state_dict.get("repository_path", "Unknown")
                                last_indexed = state_dict.get("last_indexed_at", "Unknown")
                                total_files = state_dict.get("total_files", 0)

                                info_text = (
                                    f"[bold cyan]{project_name}[/bold cyan] [dim]({collection_name})[/dim]\n"
                                    f"Path: {repo_path}\n"
                                    f"Last indexed: {last_indexed}\n"
                                    f"Files: {total_files} | Content objects: {points_count}"
                                )
                                console.print(Panel.fit(info_text, border_style="cyan"))
                            else:
                                info_text = (
                                    f"[bold cyan]{display_name}[/bold cyan] [dim]({collection_name})[/dim]\n"
                                    f"Status: Indexing in progress\n"
                                    f"Content objects: {points_count}"
                                )
                                console.print(Panel.fit(info_text, border_style="yellow"))
                        except Exception:
                            info_text = (
                                f"[bold cyan]{display_name}[/bold cyan] [dim]({collection_name})[/dim]\n"
                                f"Status: Indexed\n"
                                f"Content objects: {points_count}"
                            )
                            console.print(Panel.fit(info_text, border_style="green"))

                    except Exception as e:
                        console.print(
                            f"[yellow]Warning: Could not load collection '{collection_name}': {e}[/yellow]"
                        )

            except Exception as e:
                console.print(
                    f"[bold red]Error:[/bold red] Failed to list collections: {e}", style="red"
                )
                raise typer.Exit(code=1)

    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None


def delete_project(
    project: str = typer.Argument(..., help="Project ID to delete"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Delete all indexes for a specific project.

    You can specify the project ID (directory name in storage path).

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

        if config.storage.qdrant.mode == "embedded":
            import shutil
            from pathlib import Path

            storage_path = Path(config.storage.qdrant.path).expanduser()
            project_path = storage_path / project

            if not project_path.exists():
                console.print(
                    f"[bold red]Error:[/bold red] Project '{project}' not found", style="red"
                )
                console.print("\nRun 'codecontext list-projects' to see available projects.")
                raise typer.Exit(code=1)

            # Try to get project name from state
            try:
                from codecontext.storage.factory import create_storage_provider

                storage = create_storage_provider(config, project)
                storage.initialize()
                state = storage.get_index_state()
                storage.close()
                display_name = (
                    f"{state.project_name} ({project})" if state and state.project_name else project
                )
            except Exception:
                display_name = project

            # Confirm deletion
            if not yes:
                confirm = typer.confirm(
                    f"Are you sure you want to delete all indexes for project '{display_name}'?"
                )
                if not confirm:
                    console.print("[yellow]Deletion cancelled.[/yellow]")
                    raise typer.Exit(code=0)

            # Delete project directory
            try:
                shutil.rmtree(project_path)
                console.print(
                    f"[bold green]Success![/bold green] Deleted project '{display_name}'."
                )
            except Exception as e:
                console.print(
                    f"[bold red]Error:[/bold red] Failed to delete project: {e}", style="red"
                )
                raise typer.Exit(code=1)

        else:
            # Remote mode: delete collection from Qdrant server
            from qdrant_client import QdrantClient

            client = QdrantClient(
                url=config.storage.qdrant.url, api_key=config.storage.qdrant.api_key
            )

            try:
                # Check if collection exists
                collections = client.get_collections().collections
                collection_names = [c.name for c in collections]

                if project not in collection_names:
                    console.print(
                        f"[bold red]Error:[/bold red] Project '{project}' not found", style="red"
                    )
                    console.print("\nRun 'codecontext list-projects' to see available projects.")
                    raise typer.Exit(code=1)

                # Try to get project name from state
                display_name = project
                try:
                    from codecontext.storage.factory import create_storage_provider

                    storage = create_storage_provider(config, project)
                    if hasattr(storage, "set_client"):
                        storage.set_client(client)
                    state = storage.get_index_state()
                    if state and state.get("project_id"):
                        display_name = f"{state.get('project_id')} ({project})"
                except Exception:
                    pass

                # Confirm deletion
                if not yes:
                    confirm = typer.confirm(
                        f"Are you sure you want to delete all indexes for project '{display_name}'?"
                    )
                    if not confirm:
                        console.print("[yellow]Deletion cancelled.[/yellow]")
                        raise typer.Exit(code=0)

                # Delete collection
                try:
                    client.delete_collection(project)
                    console.print(
                        f"[bold green]Success![/bold green] Deleted project '{display_name}'."
                    )
                except Exception as e:
                    console.print(
                        f"[bold red]Error:[/bold red] Failed to delete project: {e}", style="red"
                    )
                    raise typer.Exit(code=1)

            except typer.Exit:
                raise
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}", style="red")
                raise typer.Exit(code=1)

    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None
