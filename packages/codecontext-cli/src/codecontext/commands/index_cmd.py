"""Index command implementation."""

import asyncio
import logging
from pathlib import Path

import typer
from codecontext_core.exceptions import (
    CodeContextError,
    ConfigurationError,
    StorageError,
)
from codecontext_core.models import IndexState
from rich.console import Console
from rich.panel import Panel

from codecontext.indexer.sync.full import FullIndexStrategy
from codecontext.indexer.sync.incremental import IncrementalIndexStrategy
from codecontext.utils.cli_context import initialize_command
from codecontext.utils.metadata import update_project_metadata
from codecontext.utils.project import get_project_id

console = Console()
logger = logging.getLogger(__name__)


def index(
    path: Path = typer.Argument(
        Path.cwd(),
        help="Path to repository to index",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Project name (auto-detected from git remote if not specified)",
    ),
    incremental: bool = typer.Option(
        False,
        "--incremental",
        "-i",
        help="Perform incremental update based on git changes",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force full reindex even if incremental is specified",
    ),
) -> None:
    """
    Index a codebase into the searchable knowledge base.

    This command extracts code objects from source files, generates embeddings,
    and stores them in vector storage for fast semantic search.
    """
    try:
        # Initialize command context with embedding provider
        ctx = initialize_command(
            project=project,
            path=path,
            need_embedding=True,
        )

        # Embedding provider must be available for indexing

        assert ctx.embedding_provider is not None, "Embedding provider required for indexing"
        embedding_provider = ctx.embedding_provider

        console.print(
            Panel.fit(
                f"[bold blue]CodeContext Indexer[/bold blue]\n"
                f"Project: {ctx.project_id}\n"
                f"Repository: {path}\n"
                f"Mode: {'Incremental' if incremental and not force else 'Full'}",
                border_style="blue",
            )
        )

        # Run async indexing
        async def _run_indexing() -> IndexState:
            # Determine sync strategy
            if incremental and not force:
                # Get last commit from index state
                state = ctx.storage.get_index_state()
                last_commit = state.last_commit_hash if state else None

                if last_commit:
                    console.print(
                        f"[green]Starting incremental sync from commit {last_commit[:8]}...[/green]"
                    )
                    incr_strategy = IncrementalIndexStrategy(
                        ctx.config,
                        embedding_provider,
                        ctx.storage,
                        translation_provider=ctx.translation_provider,
                    )
                    return await incr_strategy.index(path, show_progress=True)
                else:
                    console.print(
                        "[yellow]No previous index found, performing full sync...[/yellow]"
                    )
                    full_strategy = FullIndexStrategy(
                        ctx.config, embedding_provider, ctx.storage, ctx.translation_provider
                    )
                    return await full_strategy.index(path, show_progress=True)
            else:
                console.print("[green]Starting full sync...[/green]")
                full_strategy = FullIndexStrategy(
                    ctx.config, embedding_provider, ctx.storage, ctx.translation_provider
                )
                return await full_strategy.index(path, show_progress=True)

        result_state = asyncio.run(_run_indexing())

        # Update project metadata
        project_id = get_project_id(path)
        update_project_metadata(project_id, path)

        # Display results
        commit_hash = result_state.last_commit_hash[:8] if result_state.last_commit_hash else "N/A"
        console.print(
            Panel.fit(
                f"[bold green]Indexing Complete[/bold green]\n"
                f"Files processed: {result_state.total_files}\n"
                f"Code objects indexed: {result_state.total_objects}\n"
                f"Languages: {', '.join(result_state.languages)}\n"
                f"Commit: {commit_hash}",
                border_style="green",
            )
        )

        # Close storage
        ctx.storage.close()

    except StorageError as e:
        console.print(f"[bold red]Storage Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None
    except ConfigurationError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1) from None
    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        logger.exception("Indexing failed")
        raise typer.Exit(code=1) from None
