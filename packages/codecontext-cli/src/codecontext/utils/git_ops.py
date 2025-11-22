"""Git operations wrapper using GitPython."""

from pathlib import Path

import git
from codecontext_core.exceptions import GitError
from git import Blob


class GitOperations:
    """Wrapper for git operations."""

    def __init__(self, repository_path: Path) -> None:
        """
        Initialize git operations for a repository.

        Args:
            repository_path: Path to git repository

        Raises:
            GitError: If repository is invalid
        """
        self.repository_path = repository_path
        try:
            self.repo = git.Repo(repository_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError as e:
            msg = f"Not a git repository: {repository_path}"
            raise GitError(msg) from e
        except git.NoSuchPathError as e:
            msg = f"Path does not exist: {repository_path}"
            raise GitError(msg) from e

    def get_current_commit(self) -> str:
        """
        Get current commit hash.

        Returns:
            Current commit SHA

        Raises:
            GitError: If operation fails
        """
        try:
            return self.repo.head.commit.hexsha
        except (AttributeError, ValueError) as e:
            msg = f"Failed to get current commit: {e}"
            raise GitError(msg) from e

    def get_changed_files(
        self, from_commit: str | None = None
    ) -> tuple[list[Path], list[Path], list[Path]]:
        """
        Get changed files since a commit.

        Args:
            from_commit: Commit hash to compare from (None for all tracked files)

        Returns:
            Tuple of (added_files, modified_files, deleted_files)

        Raises:
            GitError: If operation fails
        """
        try:
            if from_commit is None:
                # Return all tracked files as "added"
                tracked_files = []
                for item in self.repo.tree().traverse():
                    # Filter for blobs (files) only - cast to Blob after type check
                    if isinstance(item, Blob):
                        blob = item
                        tracked_files.append(self.repository_path / blob.path)
                return tracked_files, [], []

            # Get diff from commit
            commit = self.repo.commit(from_commit)
            diff_index = commit.diff(None)  # Compare to working tree

            added = []
            modified = []
            deleted = []

            for diff_item in diff_index:
                # Get the path, preferring a_path but falling back to b_path for additions
                path_str = diff_item.a_path if diff_item.a_path else diff_item.b_path
                if path_str:
                    file_path = self.repository_path / path_str

                    if diff_item.change_type == "A":
                        added.append(file_path)
                    elif diff_item.change_type == "M":
                        modified.append(file_path)
                    elif diff_item.change_type == "D":
                        deleted.append(file_path)

        except git.BadName as e:
            msg = f"Invalid commit hash: {from_commit}"
            raise GitError(msg) from e
        except (AttributeError, ValueError, OSError) as e:
            msg = f"Failed to get changed files: {e}"
            raise GitError(msg) from e
        else:
            return added, modified, deleted

    def is_repository(self) -> bool:
        """
        Check if path is a valid git repository.

        Returns:
            True if valid repository, False otherwise
        """
        try:
            return self.repo.git_dir is not None
        except (AttributeError, git.InvalidGitRepositoryError):
            return False

    def get_repository_root(self) -> Path:
        """
        Get repository root directory.

        Returns:
            Path to repository root
        """
        return Path(self.repo.working_dir)

    @staticmethod
    def is_git_repository(path: Path) -> bool:
        """
        Check if a path is in a git repository.

        Args:
            path: Path to check

        Returns:
            True if in git repository, False otherwise
        """
        try:
            git.Repo(path, search_parent_directories=True)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return False
        else:
            return True
