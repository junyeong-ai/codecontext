"""Version command implementation."""

from rich.console import Console
from rich.panel import Panel

console = Console()


def version() -> None:
    """Show CodeContext version information."""
    console.print(
        Panel.fit(
            "[bold blue]CodeContext[/bold blue] - Intelligent Code Search Engine\n"
            "Version: [green]0.5.0[/green]\n"
            "Python: [yellow]3.13[/yellow]\n"
            "\nFor more information, visit: https://github.com/junyeong-ai/codecontext",
            border_style="blue",
        )
    )
