"""Search command implementation."""

import contextlib
import logging
from enum import Enum

import typer
from codecontext_core.exceptions import CodeContextError
from codecontext_core.models import SearchQuery
from rich.console import Console

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
        help="Output format (text or json)",
    ),
    language: str | None = typer.Option(
        None,
        "--language",
        "-l",
        help="Filter by programming language",
    ),
    file_path: str | None = typer.Option(
        None,
        "--file",
        help="Filter by exact file path",
    ),
    result_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by result type: code, document",
    ),
    expand: str | None = typer.Option(
        None,
        "--expand",
        "-e",
        help="Expand fields: signature, snippet, content, relationships, complexity, impact, all (comma-separated)",
    ),
    instruction: str | None = typer.Option(
        None,
        "--instruction",
        "-i",
        help="Instruction type: nl2code (default), qa, code2code",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed logging output",
    ),
) -> None:
    """
    Search the indexed codebase.

    Examples:
        codecontext search "OrderService"                             # All results
        codecontext search "auth" --language python --type code       # Python code only
        codecontext search "config" --file src/config.py              # Specific file
        codecontext search "what are requirements" -i qa -t document  # Documents only
    """
    try:
        enable_logging = verbose
        suppress_ctx = SuppressLoggingContext() if not enable_logging else None

        with suppress_ctx if suppress_ctx else contextlib.nullcontext():
            ctx = initialize_command(
                project=project,
                need_embedding=True,
                enable_logging=enable_logging,
            )

            assert ctx.embedding_provider is not None, "Embedding provider required"
            embedding_provider = ctx.embedding_provider

            from codecontext_core.interfaces import InstructionType

            instruction_map = {
                "nl2code": InstructionType.NL2CODE_QUERY,
                "qa": InstructionType.QA_QUERY,
                "code2code": InstructionType.CODE2CODE_QUERY,
            }
            instruction_type = instruction_map.get(
                instruction or "nl2code", InstructionType.NL2CODE_QUERY
            )

            search_query = SearchQuery(
                query_text=query,
                limit=limit,
                language_filter=language,
                file_filter=file_path,
                type_filter=result_type,
            )

            retriever = SearchRetriever(ctx.storage, embedding_provider, ctx.config.search)
            results = retriever.search(search_query, instruction_type=instruction_type)

            expand_fields: set[str] | None = None
            if expand:
                valid_fields = {
                    "signature",
                    "snippet",
                    "content",
                    "relationships",
                    "complexity",
                    "impact",
                    "all",
                }
                fields = {f.strip().lower() for f in expand.split(",")}
                invalid = fields - valid_fields
                if invalid:
                    console.print(
                        f"[bold red]Error:[/bold red] Invalid expand fields: {', '.join(invalid)}",
                        style="red",
                    )
                    console.print(
                        f"Valid fields: {', '.join(sorted(valid_fields))}", style="yellow"
                    )
                    raise typer.Exit(code=1)
                expand_fields = fields

            formatted_output = format_results(
                results,
                output_format.value,
                query,
                ctx.storage,
                include_scoring=False,
                expand_fields=expand_fields,
            )

            print(formatted_output)
            ctx.storage.close()

    except CodeContextError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        logger.exception("Search failed")
        raise typer.Exit(code=1) from None
