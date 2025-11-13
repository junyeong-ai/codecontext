"""Text/table output formatter for search results."""

from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from codecontext_core.models import SearchResult
from codecontext.formatters.base_formatter import BaseFormatter

if TYPE_CHECKING:
    from codecontext_core import VectorStore


class TextFormatter(BaseFormatter):
    """Format search results as human-readable text."""

    def format(
        self,
        results: list[SearchResult],
        _query: str = "",
        _storage: "VectorStore | None" = None,
        include_scoring: bool = False,
    ) -> str:
        """Format results as text."""
        if not results:
            return "No results found."

        console = Console()
        table = Table(title=f"Search Results ({len(results)} found)")

        table.add_column("Rank", style="cyan", width=4)
        table.add_column("Score", style="green", width=6)

        if include_scoring:
            table.add_column("BM25", style="yellow", width=6)
            table.add_column("Vector", style="magenta", width=6)

        table.add_column("Type", style="yellow", width=10)
        table.add_column("Name", style="magenta", width=25)
        table.add_column("Location", style="blue", width=50)

        for result in results:
            metadata = result.metadata
            location = f"{result.file_path}:{result.start_line}"

            row_data = [
                str(result.rank),
                f"{result.score:.3f}",
            ]

            if include_scoring:
                bm25 = result.scoring.bm25_score or 0.0
                vector = result.scoring.vector_code_score or 0.0
                row_data.extend([f"{bm25:.3f}", f"{vector:.3f}"])

            row_data.extend(
                [
                    metadata.get("object_type", ""),
                    metadata.get("name", ""),
                    location,
                ]
            )

            table.add_row(*row_data)

        with console.capture() as capture:
            console.print(table)

        return capture.get()
