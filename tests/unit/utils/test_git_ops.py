"""Unit tests for GitOperations."""

import git
import pytest
from codecontext.utils.git_ops import GitOperations
from codecontext_core.exceptions import GitError


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository."""
    repo = git.Repo.init(tmp_path)

    # Create initial commit
    test_file = tmp_path / "test.txt"
    test_file.write_text("initial content")
    repo.index.add(["test.txt"])
    repo.index.commit("Initial commit")

    return tmp_path, repo


@pytest.fixture
def git_ops(temp_git_repo):
    """Create GitOperations instance for temporary repo."""
    repo_path, _ = temp_git_repo
    return GitOperations(repo_path)


def test_get_changed_files_invalid_commit_hash(git_ops):
    """Test get_changed_files with invalid commit hash.

    Given: GitOperations instance
    When: get_changed_files is called with invalid commit hash
    Then: Should raise GitError
    """
    # Act & Assert
    with pytest.raises(GitError, match="Invalid commit hash"):
        git_ops.get_changed_files(from_commit="invalid_hash_12345")


def test_get_changed_files_no_changes(temp_git_repo):
    """Test get_changed_files when there are no changes.

    Given: Git repository with initial commit
    When: get_changed_files is called with current commit
    Then: Should return empty lists for all change types
    """
    # Arrange
    repo_path, repo = temp_git_repo
    git_ops = GitOperations(repo_path)
    current_commit = repo.head.commit.hexsha

    # Act
    added, modified, deleted = git_ops.get_changed_files(from_commit=current_commit)

    # Assert
    assert len(added) == 0, "Should have no added files"
    assert len(modified) == 0, "Should have no modified files"
    assert len(deleted) == 0, "Should have no deleted files"


def test_is_git_repository_not_a_git_repo(tmp_path):
    """Test is_git_repository with a non-git directory.

    Given: A directory that is not a git repository
    When: is_git_repository is called
    Then: Should return False
    """
    # Arrange
    non_git_dir = tmp_path / "not_a_repo"
    non_git_dir.mkdir()

    # Act
    result = GitOperations.is_git_repository(non_git_dir)

    # Assert
    assert result is False, "Should return False for non-git directory"


def test_get_repository_root_from_nested_path(temp_git_repo):
    """Test get_repository_root from a nested subdirectory.

    Given: Git repository with nested subdirectories
    When: GitOperations is initialized from nested path
    Then: Should find repository root correctly
    """
    # Arrange
    repo_path, _ = temp_git_repo

    # Create nested directory structure
    nested_dir = repo_path / "level1" / "level2" / "level3"
    nested_dir.mkdir(parents=True)

    # Act
    git_ops = GitOperations(nested_dir)
    root = git_ops.get_repository_root()

    # Assert
    assert root == repo_path, "Should find correct repository root from nested path"
    assert root.is_dir(), "Repository root should be a directory"


def test_get_current_commit(git_ops, temp_git_repo):
    """Test get_current_commit returns valid SHA.

    Given: GitOperations instance
    When: get_current_commit is called
    Then: Should return a valid 40-character SHA
    """
    # Act
    commit_hash = git_ops.get_current_commit()

    # Assert
    assert isinstance(commit_hash, str), "Commit hash should be a string"
    assert len(commit_hash) == 40, "Commit hash should be 40 characters"
    assert all(c in "0123456789abcdef" for c in commit_hash), "Commit hash should be hexadecimal"


def test_get_changed_files_with_modifications(temp_git_repo):
    """Test get_changed_files detects modified files.

    Given: Git repository with modified file
    When: get_changed_files is called with base commit
    Then: Should detect the modified file
    """
    # Arrange
    repo_path, repo = temp_git_repo
    git_ops = GitOperations(repo_path)

    # Get initial commit
    initial_commit = repo.head.commit.hexsha

    # Modify file
    test_file = repo_path / "test.txt"
    test_file.write_text("modified content")

    # Act
    _added, modified, _deleted = git_ops.get_changed_files(from_commit=initial_commit)

    # Assert
    assert len(modified) == 1, "Should detect one modified file"
    assert modified[0].name == "test.txt", "Should detect correct file"


def test_get_changed_files_none_returns_all_tracked(temp_git_repo):
    """Test get_changed_files with None returns all tracked files.

    Given: Git repository with tracked files
    When: get_changed_files is called with None (no base commit)
    Then: Should return all tracked files as added
    """
    # Arrange
    repo_path, _repo = temp_git_repo
    git_ops = GitOperations(repo_path)

    # Act
    added, modified, deleted = git_ops.get_changed_files(from_commit=None)

    # Assert
    assert len(added) >= 1, "Should return at least the initial file"
    assert any(f.name == "test.txt" for f in added), "Should include test.txt"
    assert len(modified) == 0, "Should have no modified files"
    assert len(deleted) == 0, "Should have no deleted files"


def test_is_repository_returns_true_for_valid_repo(git_ops):
    """Test is_repository returns True for valid repository.

    Given: GitOperations instance with valid repository
    When: is_repository is called
    Then: Should return True
    """
    # Act
    result = git_ops.is_repository()

    # Assert
    assert result is True, "Should return True for valid repository"


def test_git_operations_raises_error_for_invalid_path(tmp_path):
    """Test GitOperations initialization with invalid path.

    Given: Non-existent path
    When: GitOperations is initialized
    Then: Should raise GitError
    """
    # Arrange
    invalid_path = tmp_path / "nonexistent"

    # Act & Assert
    with pytest.raises(GitError, match="Path does not exist"):
        GitOperations(invalid_path)


def test_git_operations_raises_error_for_non_git_directory(tmp_path):
    """Test GitOperations initialization with non-git directory.

    Given: Directory that is not a git repository
    When: GitOperations is initialized
    Then: Should raise GitError
    """
    # Arrange
    non_git_dir = tmp_path / "not_a_repo"
    non_git_dir.mkdir()

    # Act & Assert
    with pytest.raises(GitError, match="Not a git repository"):
        GitOperations(non_git_dir)
