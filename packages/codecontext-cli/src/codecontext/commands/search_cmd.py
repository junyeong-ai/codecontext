"""Search command implementation."""

import contextlib
from enum import Enum

import typer
from rich.console import Console

from codecontext_core.exceptions import CodeContextError
from codecontext_core.models import SearchQuery
import logging

from codecontext.search.formatter import format_results
from codecontext.search.retriever import SearchRetriever
from codecontext.utils.cli_context import initialize_command
from codecontext.utils.logging import SuppressLoggingContext

console = Console()
logger = logging.getLogger(__name__)


class OutputFormat(str, Enum):
    """Output format options."""

    JSON = "json"
    TEXT = "text"


def search(
    query: str = typer.Argument(..., help="Natural language search query"),
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Project name (auto-detected from current directory if not specified)",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of results to return",
        min=1,
        max=100,
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        "--format",
        "-f",
        help="Output format",
    ),
    language: str | None = typer.Option(
        None,
        "--language",
        "-l",
        help="Filter by programming language",
    ),
    file_pattern: str | None = typer.Option(
        None,
        "--file-pattern",
        help="Filter by file pattern",
    ),
    expand: bool = typer.Option(
        False,
        "--expand",
        "-e",
        help="Include detailed scoring breakdown (BM25, Vector, etc.)",
    ),
) -> None:
    """
    Search the indexed codebase with natural language queries.

    Returns code objects ranked by semantic similarity to the query.
    Use --format json for machine-readable output suitable for AI agents.
    Use --expand to include detailed scoring information for analysis.
    """
    try:
        # Initialize command context with embedding provider
        # Suppress logging for JSON output to keep stdout clean
        enable_logging = output_format != OutputFormat.JSON

        # Use context manager to suppress only CodeContext logging (not third-party)
        suppress_ctx = SuppressLoggingContext() if not enable_logging else None

        with suppress_ctx if suppress_ctx else contextlib.nullcontext():
            ctx = initialize_command(
                project=project,
                need_embedding=True,
                enable_logging=enable_logging,
            )

            # Embedding provider must be available for search

            assert ctx.embedding_provider is not None, "Embedding provider required for search"
            embedding_provider = ctx.embedding_provider

            # Create search query
            search_query = SearchQuery(
                query_text=query,
                limit=limit,
                language_filter=language,
                file_filter=file_pattern,
            )

            # Execute search
            retriever = SearchRetriever(
                ctx.config, embedding_provider, ctx.storage, ctx.translation_provider
            )
            results = retriever.search(search_query)

            # Format and display results (with storage for relationships & impact_stats)
            formatted_output = format_results(
                results, output_format.value, query, ctx.storage, include_scoring=expand
            )

            if output_format == OutputFormat.JSON:
                # Use plain print for JSON to avoid rich formatting
                print(formatted_output)
            else:
                console.print(formatted_output)

            # Close storage
            ctx.storage.close()

    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        logger.exception("Search failed")
        raise typer.Exit(code=1) from None
