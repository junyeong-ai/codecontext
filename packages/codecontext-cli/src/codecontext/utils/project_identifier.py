"""Project identification for multi-project support."""

import hashlib
import re
from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, Repo


class ProjectIdentifier:
    """Auto-detects project identifiers from Git repositories or directory names."""

    @staticmethod
    def detect_from_git(repo_path: Path) -> str | None:
        """
        Extract repository name from Git remote URL.

        Args:
            repo_path: Path to repository

        Returns:
            Repository name if Git repo detected, None otherwise

        Examples:
            https://github.com/user/my-repo.git → my-repo
            git@github.com:user/my-repo.git → my-repo
            https://gitlab.com/group/subgroup/project.git → project
        """
        try:
            repo = Repo(repo_path, search_parent_directories=True)

            # Try origin first, then any remote
            try:
                remote_url = repo.remotes.origin.url
            except (AttributeError, IndexError):
                if repo.remotes:
                    remote_url = repo.remotes[0].url
                else:
                    return None

            # Extract repository name from various URL formats
            # https://github.com/user/my-repo.git
            # git@github.com:user/my-repo.git
            # /path/to/my-repo.git
            match = re.search(r"([^/:]+?)(\.git)?$", remote_url)
            if match:
                return match.group(1)

        except (InvalidGitRepositoryError, GitCommandError, ValueError):
            return None
        else:
            return None

    @staticmethod
    def detect_from_directory(repo_path: Path) -> str:
        """
        Use directory name or path hash as fallback.

        Args:
            repo_path: Path to repository

        Returns:
            Directory name or hash-based identifier

        Examples:
            /workspace/my-project → my-project
            /tmp/tmpXYZ → <hash of absolute path>
        """
        # Try directory name first
        if repo_path.name and repo_path.name not in [".", "..", ""]:
            # Clean directory name (remove special chars)
            clean_name = re.sub(r"[^a-zA-Z0-9_-]", "-", repo_path.name)
            if clean_name and clean_name != "-":
                return clean_name

        # Fallback to hash of absolute path
        abs_path = str(repo_path.resolve())
        hash_val = hashlib.sha256(abs_path.encode()).hexdigest()[:16]
        return f"project-{hash_val}"

    @staticmethod
    def detect(repo_path: Path) -> str:
        """
        Auto-detect project ID (Git → directory → hash).

        Priority:
        1. Git remote repository name
        2. Directory name
        3. Hash of absolute path

        Args:
            repo_path: Path to repository

        Returns:
            Project identifier string

        Examples:
            Git repo: codecontext
            Non-Git dir: my-project
            Temp dir: project-a1b2c3d4e5f6g7h8
        """
        # Try Git first
        git_name = ProjectIdentifier.detect_from_git(repo_path)
        if git_name:
            return git_name

        # Fallback to directory-based detection
        return ProjectIdentifier.detect_from_directory(repo_path)

    @staticmethod
    def normalize(project_id: str) -> str:
        """
        Normalize project ID for use as collection name.

        Rules:
        - Lowercase
        - Replace special chars with hyphens
        - Remove leading/trailing hyphens
        - Max 63 chars (DNS label limit)

        Args:
            project_id: Raw project identifier

        Returns:
            Normalized project identifier

        Examples:
            "My-Project" → "my-project"
            "project@123" → "project-123"
            "a" * 100 → "aaa...aaa" (63 chars)
        """
        # Lowercase
        normalized = project_id.lower()

        # Replace special chars with hyphens
        normalized = re.sub(r"[^a-z0-9-]", "-", normalized)

        # Remove leading/trailing hyphens
        normalized = normalized.strip("-")

        # Limit length (DNS label limit)
        if len(normalized) > 63:
            # Keep first 50 chars + hash of full name
            hash_suffix = hashlib.sha256(project_id.encode()).hexdigest()[:10]
            normalized = f"{normalized[:50]}-{hash_suffix}"

        return normalized or "default-project"
