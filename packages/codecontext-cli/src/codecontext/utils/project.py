"""Project identification utilities."""

import hashlib
import subprocess
from pathlib import Path


def get_project_id(repo_path: Path) -> str:
    """Generate stable project ID (Git origin > path hash)."""
    if git_id := _get_git_origin_id(repo_path):
        return git_id
    return _get_path_hash_id(repo_path)


def _get_git_origin_id(repo_path: Path) -> str | None:
    """Generate ID from Git remote origin URL."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "config", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            origin = result.stdout.strip()
            origin = origin.replace("https://", "").replace("http://", "")
            origin = origin.replace("git@", "").replace(":", "/")
            origin = origin.removesuffix(".git")
            return hashlib.sha256(origin.encode()).hexdigest()[:16]
    except Exception:
        pass
    return None


def _get_path_hash_id(repo_path: Path) -> str:
    """Generate ID from absolute path hash."""
    abs_path = repo_path.resolve()
    return hashlib.sha256(str(abs_path).encode()).hexdigest()[:16]


def normalize_project_id(project_id: str) -> str:
    """Normalize project ID for Qdrant collection name.

    Rules:
    - Lowercase
    - Replace special chars with hyphens
    - Remove leading/trailing hyphens
    - Max 63 chars (DNS label limit)
    """
    import re

    normalized = project_id.lower()
    normalized = re.sub(r"[^a-z0-9-]", "-", normalized)
    normalized = normalized.strip("-")

    if len(normalized) > 63:
        hash_suffix = hashlib.sha256(project_id.encode()).hexdigest()[:10]
        normalized = f"{normalized[:50]}-{hash_suffix}"

    return normalized or "default-project"
