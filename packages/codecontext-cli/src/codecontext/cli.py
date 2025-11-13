"""CodeContext CLI - Intelligent Code Search Engine."""

import warnings

# Suppress known NumPy float32 subnormal warnings (NumPy internal issue)
warnings.filterwarnings("ignore", message=".*smallest subnormal.*", category=UserWarning)

import typer  # noqa: E402

from codecontext.commands import (  # noqa: E402
    index_cmd,
    init_cmd,
    project_cmd,
    search_cmd,
    status_cmd,
    version_cmd,
)

app = typer.Typer(
    name="codecontext",
    help="CodeContext - Intelligent Code Search Engine CLI",
    add_completion=False,
)

# Register commands
app.command()(init_cmd.init)
app.command()(index_cmd.index)
app.command()(search_cmd.search)
app.command()(status_cmd.status)
app.command(name="list-projects")(project_cmd.list_projects)
app.command(name="delete-project")(project_cmd.delete_project)
app.command()(version_cmd.version)

if __name__ == "__main__":
    app()
