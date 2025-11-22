"""Project metadata management."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from codecontext.config.settings import get_data_dir


def _get_git_origin(repo_path: Path) -> str | None:
    """Get Git remote origin URL."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "config", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def update_project_metadata(project_id: str, repo_path: Path) -> None:
    """Update project metadata - saves in project directory for better isolation."""
    # Save metadata inside the project directory (alongside Qdrant data)
    project_dir = get_data_dir() / project_id
    metadata_path = project_dir / "metadata.json"

    # Project directory should already exist from indexing
    project_dir.mkdir(parents=True, exist_ok=True)

    git_origin = _get_git_origin(repo_path)

    metadata = {
        "project_id": project_id,
        "name": repo_path.name,
        "git_origin": git_origin,
        "indexed_at": datetime.now().isoformat(),
        "source_path": str(repo_path.resolve()),
        "last_used": datetime.now().isoformat(),
    }

    metadata_path.write_text(json.dumps(metadata, indent=2))


def get_project_info(project_id: str) -> dict[str, Any] | None:
    """Get project metadata by ID - reads from project directory."""
    metadata_path = get_data_dir() / project_id / "metadata.json"

    if not metadata_path.exists():
        return None

    result: dict[str, Any] = json.loads(metadata_path.read_text())
    return result


def list_all_projects() -> dict[str, dict[str, Any]]:
    """List all indexed projects - scans project directories."""
    data_dir = get_data_dir()

    if not data_dir.exists():
        return {}

    projects = {}
    for project_dir in data_dir.iterdir():
        if not project_dir.is_dir():
            continue

        metadata_path = project_dir / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
            projects[project_dir.name] = metadata

    return projects
