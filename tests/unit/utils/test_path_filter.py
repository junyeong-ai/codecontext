"""Tests for PathFilter utility.

This module contains tests for gitignore-style path filtering functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from codecontext.utils.path_filter import PathFilter, create_path_filter

# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def temp_repo():
    """Create a temporary repository directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        yield repo_path


@pytest.fixture
def path_filter(temp_repo):
    """Create a PathFilter instance for testing."""
    return PathFilter(repository_path=temp_repo, respect_gitignore=False)


@pytest.fixture
def temp_repo_with_ignore(temp_repo):
    """Create a temporary repository with .codecontextignore file."""
    ignore_file = temp_repo / ".codecontextignore"
    ignore_file.write_text(
        """
# Test patterns
*.log
temp/
!important.log
test_*.py
"""
    )
    return temp_repo


@pytest.fixture
def temp_repo_with_gitignore(temp_repo):
    """Create a temporary repository with .gitignore file."""
    gitignore = temp_repo / ".gitignore"
    gitignore.write_text(
        """
node_modules/
*.pyc
.env
"""
    )
    return temp_repo


# ======================================================================
# Test Classes
# ======================================================================


class TestPathFilterInitialization:
    """Test PathFilter initialization."""

    def test_initializes_with_repository_path(self, temp_repo):
        """Should initialize with repository path.

        Given: A valid repository path
        When: PathFilter is initialized
        Then: Repository path should be stored
        """
        # Act
        filter = PathFilter(repository_path=temp_repo)

        # Assert
        assert filter.repository_path == temp_repo
        assert filter.ignore_file_name == ".codecontextignore"
        assert filter.respect_gitignore is True

    def test_initializes_with_custom_ignore_file(self, temp_repo):
        """Should initialize with custom ignore file name."""
        # Act
        filter = PathFilter(repository_path=temp_repo, ignore_file_name=".customignore")

        # Assert
        assert filter.ignore_file_name == ".customignore"

    def test_loads_default_patterns(self, temp_repo):
        """Should load default ignore patterns."""
        # Act
        filter = PathFilter(repository_path=temp_repo)

        # Assert
        assert ".git/" in filter.patterns
        assert "__pycache__/" in filter.patterns
        assert "node_modules/" in filter.patterns
        assert "*.pyc" in filter.patterns

    def test_initializes_without_gitignore_respect(self, temp_repo):
        """Should initialize without respecting .gitignore."""
        # Act
        filter = PathFilter(repository_path=temp_repo, respect_gitignore=False)

        # Assert
        assert filter.respect_gitignore is False


class TestLoadPatterns:
    """Test pattern loading from ignore files."""

    def test_loads_codecontextignore_patterns(self, temp_repo_with_ignore):
        """Should load patterns from .codecontextignore file.

        Given: Repository with .codecontextignore file
        When: PathFilter is initialized
        Then: Patterns should be loaded from file
        """
        # Act
        filter = PathFilter(repository_path=temp_repo_with_ignore, respect_gitignore=False)

        # Assert
        assert "*.log" in filter.patterns
        assert "temp/" in filter.patterns
        assert "!important.log" in filter.patterns
        assert "test_*.py" in filter.patterns

    def test_loads_gitignore_patterns_when_enabled(self, temp_repo_with_gitignore):
        """Should load patterns from .gitignore when enabled.

        Given: Repository with .gitignore and respect_gitignore=True
        When: PathFilter is initialized
        Then: Patterns should be loaded from .gitignore
        """
        # Act
        filter = PathFilter(repository_path=temp_repo_with_gitignore, respect_gitignore=True)

        # Assert
        assert "node_modules/" in filter.patterns
        assert "*.pyc" in filter.patterns
        assert ".env" in filter.patterns

    def test_skips_gitignore_when_disabled(self, temp_repo_with_gitignore):
        """Should not load .gitignore when disabled.

        Given: Repository with .gitignore and respect_gitignore=False
        When: PathFilter is initialized
        Then: Patterns should not include .gitignore patterns
        """
        # Act
        filter = PathFilter(repository_path=temp_repo_with_gitignore, respect_gitignore=False)

        # Assert
        # Default patterns should exist but not gitignore-specific ones
        assert ".git/" in filter.patterns
        # Gitignore patterns should not be present beyond defaults
        pattern_count_without_defaults = len(
            [p for p in filter.patterns if p not in PathFilter.DEFAULT_IGNORE_PATTERNS]
        )
        assert pattern_count_without_defaults == 0

    def test_handles_nonexistent_ignore_files(self, temp_repo):
        """Should handle missing ignore files gracefully.

        Given: Repository without ignore files
        When: PathFilter is initialized
        Then: Only default patterns should be loaded
        """
        # Act
        filter = PathFilter(repository_path=temp_repo, respect_gitignore=False)

        # Assert
        assert len(filter.patterns) == len(PathFilter.DEFAULT_IGNORE_PATTERNS)


class TestReadIgnoreFile:
    """Test ignore file reading functionality."""

    def test_reads_file_content(self, temp_repo):
        """Should read patterns from ignore file."""
        # Arrange
        ignore_file = temp_repo / ".codecontextignore"
        ignore_file.write_text("*.test\n#comment\n\npattern/\n")
        filter = PathFilter(repository_path=temp_repo, respect_gitignore=False)

        # Act
        patterns = filter._read_ignore_file(ignore_file)

        # Assert
        assert "*.test" in patterns
        assert "pattern/" in patterns
        assert "#comment" not in patterns  # Comments should be skipped

    def test_skips_empty_lines(self, temp_repo):
        """Should skip empty lines in ignore file."""
        # Arrange
        ignore_file = temp_repo / ".codecontextignore"
        ignore_file.write_text("pattern1\n\n\npattern2\n")
        filter = PathFilter(repository_path=temp_repo, respect_gitignore=False)

        # Act
        patterns = filter._read_ignore_file(ignore_file)

        # Assert
        assert len(patterns) == 2
        assert "pattern1" in patterns
        assert "pattern2" in patterns

    def test_handles_file_read_errors(self, temp_repo, path_filter):
        """Should handle file read errors gracefully.

        Given: Invalid file path
        When: Reading ignore file
        Then: Should return empty list and log warning
        """
        # Arrange
        nonexistent_file = temp_repo / "nonexistent.txt"

        # Act
        patterns = path_filter._read_ignore_file(nonexistent_file)

        # Assert
        assert patterns == []


class TestShouldIndex:
    """Test file indexing decision logic."""

    def test_allows_normal_files(self, path_filter, temp_repo):
        """Should allow normal files to be indexed.

        Given: A normal source file
        When: Checking if should index
        Then: Should return True
        """
        # Arrange
        file_path = temp_repo / "main.py"

        # Act
        result = path_filter.should_index(file_path)

        # Assert
        assert result is True

    def test_ignores_pycache_directory(self, path_filter, temp_repo):
        """Should ignore __pycache__ directories."""
        # Arrange
        file_path = temp_repo / "__pycache__" / "module.pyc"

        # Act
        result = path_filter.should_index(file_path)

        # Assert
        assert result is False

    def test_ignores_pyc_files(self, path_filter, temp_repo):
        """Should ignore .pyc files."""
        # Arrange
        file_path = temp_repo / "module.pyc"

        # Act
        result = path_filter.should_index(file_path)

        # Assert
        assert result is False

    def test_ignores_node_modules(self, path_filter, temp_repo):
        """Should ignore node_modules directory."""
        # Arrange
        file_path = temp_repo / "node_modules" / "package" / "index.js"

        # Act
        result = path_filter.should_index(file_path)

        # Assert
        assert result is False

    def test_ignores_git_directory(self, path_filter, temp_repo):
        """Should ignore .git directory."""
        # Arrange
        file_path = temp_repo / ".git" / "config"

        # Act
        result = path_filter.should_index(file_path)

        # Assert
        assert result is False

    def test_handles_absolute_paths(self, path_filter, temp_repo):
        """Should handle absolute file paths.

        Given: Absolute file path within repository
        When: Checking if should index
        Then: Should convert to relative and check correctly
        """
        # Arrange
        file_path = temp_repo / "src" / "main.py"

        # Act
        result = path_filter.should_index(file_path)

        # Assert
        assert result is True

    def test_handles_relative_paths(self, path_filter):
        """Should handle relative file paths."""
        # Arrange
        file_path = Path("src/main.py")

        # Act
        result = path_filter.should_index(file_path)

        # Assert
        assert result is True

    def test_rejects_files_outside_repository(self, path_filter):
        """Should reject files outside repository.

        Given: Absolute path outside repository
        When: Checking if should index
        Then: Should return False
        """
        # Arrange
        file_path = Path("/outside/repository/file.py")

        # Act
        result = path_filter.should_index(file_path)

        # Assert
        assert result is False

    def test_handles_windows_path_separators(self, path_filter):
        """Should handle Windows path separators."""
        # Arrange
        file_path = Path("src\\module\\file.py")

        # Act
        result = path_filter.should_index(file_path)

        # Assert
        assert result is True  # Should normalize separators


class TestFilterPaths:
    """Test batch path filtering."""

    def test_filters_list_of_paths(self, path_filter, temp_repo):
        """Should filter a list of paths.

        Given: List of paths with mixed indexed/ignored files
        When: Filtering paths
        Then: Should return only indexable paths
        """
        # Arrange
        paths = [
            temp_repo / "main.py",
            temp_repo / "__pycache__" / "module.pyc",
            temp_repo / "utils.py",
            temp_repo / "node_modules" / "package.json",
            temp_repo / "tests.py",
        ]

        # Act
        result = path_filter.filter_paths(paths)

        # Assert
        assert len(result) == 3
        assert temp_repo / "main.py" in result
        assert temp_repo / "utils.py" in result
        assert temp_repo / "tests.py" in result

    def test_returns_empty_list_when_all_ignored(self, path_filter, temp_repo):
        """Should return empty list when all paths are ignored."""
        # Arrange
        paths = [
            temp_repo / "__pycache__" / "module.pyc",
            temp_repo / "node_modules" / "package.json",
            temp_repo / ".git" / "config",
        ]

        # Act
        result = path_filter.filter_paths(paths)

        # Assert
        assert len(result) == 0

    def test_returns_all_when_none_ignored(self, path_filter, temp_repo):
        """Should return all paths when none are ignored."""
        # Arrange
        paths = [
            temp_repo / "main.py",
            temp_repo / "utils.py",
            temp_repo / "tests.py",
        ]

        # Act
        result = path_filter.filter_paths(paths)

        # Assert
        assert len(result) == 3
        assert result == paths


class TestAddPattern:
    """Test runtime pattern addition."""

    def test_adds_pattern_at_runtime(self, path_filter, temp_repo):
        """Should add pattern at runtime.

        Given: PathFilter instance
        When: Adding a new pattern
        Then: Pattern should be added and take effect
        """
        # Arrange
        file_path = temp_repo / "custom.tmp"
        assert path_filter.should_index(file_path) is True

        # Act
        path_filter.add_pattern("*.tmp")

        # Assert
        assert "*.tmp" in path_filter.patterns
        assert path_filter.should_index(file_path) is False

    def test_pattern_applies_immediately(self, path_filter, temp_repo):
        """Should apply pattern immediately after adding."""
        # Arrange
        paths = [
            temp_repo / "file.py",
            temp_repo / "temp.xyz",
        ]

        # Act
        path_filter.add_pattern("*.xyz")
        result = path_filter.filter_paths(paths)

        # Assert
        assert len(result) == 1
        assert temp_repo / "file.py" in result
        assert temp_repo / "temp.xyz" not in result


class TestCustomPatterns:
    """Test custom pattern scenarios."""

    def test_matches_wildcard_patterns(self, temp_repo):
        """Should match wildcard patterns correctly."""
        # Arrange
        ignore_file = temp_repo / ".codecontextignore"
        ignore_file.write_text("test_*.py\n*.log\n")
        filter = PathFilter(repository_path=temp_repo, respect_gitignore=False)

        # Act & Assert
        assert filter.should_index(temp_repo / "test_main.py") is False
        assert filter.should_index(temp_repo / "test_utils.py") is False
        assert filter.should_index(temp_repo / "debug.log") is False
        assert filter.should_index(temp_repo / "main.py") is True

    def test_matches_directory_patterns(self, temp_repo):
        """Should match directory patterns."""
        # Arrange
        ignore_file = temp_repo / ".codecontextignore"
        ignore_file.write_text("temp/\nbuild/\n")
        filter = PathFilter(repository_path=temp_repo, respect_gitignore=False)

        # Act & Assert
        assert filter.should_index(temp_repo / "temp" / "file.txt") is False
        assert filter.should_index(temp_repo / "build" / "output.js") is False
        assert filter.should_index(temp_repo / "src" / "main.py") is True

    def test_handles_negation_patterns(self, temp_repo):
        """Should handle negation patterns (!pattern).

        Given: Pattern with negation
        When: Checking files
        Then: Negated files should be included
        """
        # Arrange
        ignore_file = temp_repo / ".codecontextignore"
        ignore_file.write_text("*.log\n!important.log\n")
        filter = PathFilter(repository_path=temp_repo, respect_gitignore=False)

        # Act & Assert
        assert filter.should_index(temp_repo / "debug.log") is False
        assert filter.should_index(temp_repo / "important.log") is True


class TestCreatePathFilter:
    """Test convenience factory function."""

    def test_creates_path_filter_instance(self, temp_repo):
        """Should create PathFilter instance.

        Given: Repository path
        When: Using create_path_filter()
        Then: Should return PathFilter instance
        """
        # Act
        filter = create_path_filter(temp_repo)

        # Assert
        assert isinstance(filter, PathFilter)
        assert filter.repository_path == temp_repo


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_handles_invalid_utf8_in_ignore_file(self, path_filter, temp_repo):
        """Should handle invalid UTF-8 in ignore files."""
        # Arrange
        ignore_file = temp_repo / ".codecontextignore"
        ignore_file.write_bytes(b"\x80\x81\x82")  # Invalid UTF-8

        # Act
        patterns = path_filter._read_ignore_file(ignore_file)

        # Assert
        assert patterns == []  # Should return empty on error

    def test_defaults_to_indexing_on_error(self, path_filter):
        """Should default to indexing when error occurs.

        Given: Path that causes an error
        When: Checking if should index
        Then: Should default to True (index)
        """
        # Arrange
        # Mock pathspec to raise exception
        with patch.object(path_filter.spec, "match_file", side_effect=RuntimeError("Test error")):
            # Act
            result = path_filter.should_index(Path("test.py"))

            # Assert
            assert result is True  # Default to indexing on error


# ======================================================================
# Parametrized Tests
# ======================================================================


@pytest.mark.parametrize(
    "pattern,file_path,should_ignore",
    [
        ("*.pyc", "module.pyc", True),
        ("*.pyc", "module.py", False),
        ("__pycache__/", "__pycache__/module.pyc", True),
        ("node_modules/", "node_modules/package/index.js", True),
        ("build/", "build/output.js", True),
        ("build/", "src/build.py", False),
        ("*.log", "debug.log", True),
        ("*.log", "debug.txt", False),
        ("test_*", "test_main.py", True),
        ("test_*", "main_test.py", False),
    ],
)
def test_pattern_matching(temp_repo, pattern, file_path, should_ignore):
    """Should match various patterns correctly."""
    # Arrange
    ignore_file = temp_repo / ".codecontextignore"
    ignore_file.write_text(pattern)
    filter = PathFilter(repository_path=temp_repo, respect_gitignore=False)

    # Act
    result = filter.should_index(temp_repo / file_path)

    # Assert
    assert result is not should_ignore  # should_index is opposite of should_ignore
