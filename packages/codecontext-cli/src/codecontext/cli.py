"""CodeContext CLI - Intelligent Code Search Engine."""

import os
import warnings

# MPS memory configuration - must be set before PyTorch import
# HIGH_WATERMARK: max memory ratio (0.0 = unlimited, default behavior varies)
# LOW_WATERMARK: cleanup threshold (must be <= HIGH)
if "PYTORCH_MPS_HIGH_WATERMARK_RATIO" not in os.environ:
    os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"  # Disable limit for stability

# Suppress known NumPy float32 subnormal warnings (NumPy internal issue)
warnings.filterwarnings("ignore", message=".*smallest subnormal.*", category=UserWarning)

import typer  # noqa: E402

from codecontext.commands import (  # noqa: E402
    config_cmd,
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

# Config subcommands
config_app = typer.Typer(help="Manage configuration")
config_app.command("init")(config_cmd.init)
config_app.command("show")(config_cmd.show)
config_app.command("path")(config_cmd.path)
config_app.command("edit")(config_cmd.edit)
config_app.command("validate")(config_cmd.validate)
app.add_typer(config_app, name="config")

if __name__ == "__main__":
    app()
