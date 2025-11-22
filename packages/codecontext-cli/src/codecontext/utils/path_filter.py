"""Path filtering using gitignore-style patterns.

This module provides selective indexing support through .codecontextignore files
that follow gitignore semantics.

The pathspec library provides full gitignore semantics with acceptable overhead.
"""

import logging
from pathlib import Path
from typing import ClassVar

import pathspec

logger = logging.getLogger(__name__)


class PathFilter:
    """Filter file paths using gitignore-style patterns.

    This class implements selective indexing by respecting .codecontextignore
    files in the repository. It uses the pathspec library for full gitignore
    semantics including negation patterns.

    Features:
    - Gitignore-style pattern matching
    - Negation patterns (!pattern)
    - Directory-specific patterns
    - Cascading ignore files (repository root takes precedence)
    """

    DEFAULT_IGNORE_PATTERNS: ClassVar[list[str]] = [
        # Version control
        ".git/",
        ".svn/",
        ".hg/",
        # Build artifacts
        "build/",
        "dist/",
        "target/",
        "*.class",
        "*.pyc",
        "__pycache__/",
        # Dependencies
        "node_modules/",
        "vendor/",
        "venv/",
        ".venv/",
        # IDE files
        ".idea/",
        ".vscode/",
        "*.swp",
        "*.swo",
        # Test coverage
        ".coverage",
        "htmlcov/",
        "coverage/",
        # Large media files
        "*.mp4",
        "*.mov",
        "*.avi",
        "*.mkv",
        # Binary files
        "*.exe",
        "*.dll",
        "*.so",
        "*.dylib",
    ]

    def __init__(
        self,
        repository_path: Path,
        ignore_file_name: str = ".codecontextignore",
        respect_gitignore: bool = True,
    ) -> None:
        """Initialize path filter.

        Args:
            repository_path: Root path of the repository
            ignore_file_name: Name of ignore file (default: .codecontextignore)
            respect_gitignore: Whether to also respect .gitignore (default: True)
        """
        self.repository_path = repository_path
        self.ignore_file_name = ignore_file_name
        self.respect_gitignore = respect_gitignore

        # Load patterns
        self.patterns = self._load_patterns()

        # Compile pathspec for efficient matching
        self.spec = pathspec.PathSpec.from_lines("gitwildmatch", self.patterns)

        logger.info(
            f"Initialized PathFilter with {len(self.patterns)} patterns from {repository_path}"
        )

    def _load_patterns(self) -> list[str]:
        """Load ignore patterns from files.

        Returns:
            List of patterns to ignore
        """
        patterns = list(self.DEFAULT_IGNORE_PATTERNS)

        # Load .codecontextignore
        ignore_file = self.repository_path / self.ignore_file_name
        if ignore_file.exists():
            patterns.extend(self._read_ignore_file(ignore_file))
            logger.info(f"Loaded patterns from {self.ignore_file_name}")

        # Load .gitignore if requested
        if self.respect_gitignore:
            gitignore = self.repository_path / ".gitignore"
            if gitignore.exists():
                patterns.extend(self._read_ignore_file(gitignore))
                logger.info("Loaded patterns from .gitignore")

        return patterns

    def _read_ignore_file(self, file_path: Path) -> list[str]:
        """Read patterns from an ignore file.

        Args:
            file_path: Path to ignore file

        Returns:
            List of patterns from file
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            patterns = []

            for line in content.splitlines():
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    patterns.append(line)

        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to read ignore file {file_path}: {e}")
            return []
        else:
            logger.debug(f"Read {len(patterns)} patterns from {file_path}")
            return patterns

    def should_index(self, file_path: Path) -> bool:
        """Check if a file should be indexed.

        Args:
            file_path: Absolute or relative file path

        Returns:
            True if file should be indexed, False if it should be ignored
        """
        # Convert to relative path from repository root
        try:
            if file_path.is_absolute():
                relative_path = file_path.relative_to(self.repository_path)
            else:
                relative_path = file_path

            # Convert to string with forward slashes (pathspec expects this)
            path_str = str(relative_path).replace("\\", "/")

            # Check if path matches any ignore pattern
            is_ignored = self.spec.match_file(path_str)

            if is_ignored:
                logger.debug(f"Ignoring file: {path_str}")

        except ValueError:
            # File is outside repository, don't index
            logger.warning(f"File outside repository: {file_path}")
            return False
        except (OSError, RuntimeError) as e:
            # On error, default to indexing
            logger.warning(f"Error checking file {file_path}: {e}")
            return True
        else:
            return not is_ignored

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        """Filter a list of paths.

        Args:
            paths: List of file paths

        Returns:
            List of paths that should be indexed
        """
        filtered = [p for p in paths if self.should_index(p)]
        ignored_count = len(paths) - len(filtered)

        if ignored_count > 0:
            logger.info(f"Filtered {ignored_count} files, {len(filtered)} remaining")

        return filtered

    def add_pattern(self, pattern: str) -> None:
        """Add a pattern at runtime.

        Args:
            pattern: Gitignore-style pattern
        """
        self.patterns.append(pattern)
        # Recompile pathspec
        self.spec = pathspec.PathSpec.from_lines("gitwildmatch", self.patterns)
        logger.debug(f"Added pattern: {pattern}")


def create_path_filter(repository_path: Path) -> PathFilter:
    """Convenience function to create a path filter.

    Args:
        repository_path: Root path of the repository

    Returns:
        PathFilter instance
    """
    return PathFilter(repository_path)
