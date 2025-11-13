"""Comprehensive tests for ProjectIdentifier.

Tests cover:
- Git repository name detection from various URL formats
- Directory-based fallback detection
- Project ID normalization
- Priority order (Git → directory → hash)
- Edge cases and error handling
"""

from pathlib import Path
from unittest.mock import Mock, patch

from codecontext.utils.project_identifier import ProjectIdentifier
from git import GitCommandError, InvalidGitRepositoryError


class TestDetectFromGit:
    """Test Git repository name detection."""

    def test_detect_from_https_url_with_git_extension(self, tmp_path):
        """Should extract name from https URL with .git extension."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            mock_origin = Mock()
            mock_origin.url = "https://github.com/user/my-repo.git"
            mock_repo.return_value.remotes.origin = mock_origin

            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result == "my-repo"

    def test_detect_from_https_url_without_git_extension(self, tmp_path):
        """Should extract name from https URL without .git extension."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            mock_origin = Mock()
            mock_origin.url = "https://github.com/user/codecontext"
            mock_repo.return_value.remotes.origin = mock_origin

            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result == "codecontext"

    def test_detect_from_ssh_url_with_git_extension(self, tmp_path):
        """Should extract name from SSH URL with .git extension."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            mock_origin = Mock()
            mock_origin.url = "git@github.com:user/my-repo.git"
            mock_repo.return_value.remotes.origin = mock_origin

            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result == "my-repo"

    def test_detect_from_ssh_url_without_git_extension(self, tmp_path):
        """Should extract name from SSH URL without .git extension."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            mock_origin = Mock()
            mock_origin.url = "git@gitlab.com:group/project"
            mock_repo.return_value.remotes.origin = mock_origin

            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result == "project"

    def test_detect_from_gitlab_nested_groups(self, tmp_path):
        """Should extract name from GitLab nested group URL."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            mock_origin = Mock()
            mock_origin.url = "https://gitlab.com/group/subgroup/project.git"
            mock_repo.return_value.remotes.origin = mock_origin

            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result == "project"

    def test_detect_from_local_path(self, tmp_path):
        """Should extract name from local file path."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            mock_origin = Mock()
            mock_origin.url = "/workspace/my-repo.git"
            mock_repo.return_value.remotes.origin = mock_origin

            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result == "my-repo"

    def test_detect_without_origin_but_with_other_remote(self, tmp_path):
        """Should use first remote if origin not available."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            # Simulate missing origin remote by raising AttributeError
            mock_repo.return_value.remotes.origin = Mock(side_effect=AttributeError("No origin"))

            # But provide other remotes
            mock_upstream = Mock()
            mock_upstream.url = "https://github.com/upstream/repo.git"
            mock_repo.return_value.remotes = [mock_upstream]

            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result == "repo"

    def test_detect_without_any_remotes(self, tmp_path):
        """Should return None if no remotes configured."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            mock_repo.return_value.remotes.origin = Mock(side_effect=AttributeError("No origin"))
            mock_repo.return_value.remotes = []

            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result is None

    def test_detect_invalid_git_repository(self, tmp_path):
        """Should return None for invalid Git repository."""
        with patch(
            "codecontext.utils.project_identifier.Repo",
            side_effect=InvalidGitRepositoryError,
        ):
            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result is None

    def test_detect_git_command_error(self, tmp_path):
        """Should return None when Git command fails."""
        with patch(
            "codecontext.utils.project_identifier.Repo", side_effect=GitCommandError("git", "error")
        ):
            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result is None

    def test_detect_value_error(self, tmp_path):
        """Should return None when ValueError occurs."""
        with patch("codecontext.utils.project_identifier.Repo", side_effect=ValueError("error")):
            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result is None

    def test_detect_malformed_url(self, tmp_path):
        """Should return None for malformed URL that doesn't match regex."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            mock_origin = Mock()
            mock_origin.url = ""  # Empty URL
            mock_repo.return_value.remotes.origin = mock_origin

            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result is None

    def test_detect_with_remote_index_error(self, tmp_path):
        """Should return None when remote access raises IndexError."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            # Simulate IndexError when accessing origin
            mock_repo.return_value.remotes.origin = Mock(side_effect=IndexError)
            mock_repo.return_value.remotes = []

            result = ProjectIdentifier.detect_from_git(tmp_path)
            assert result is None


class TestDetectFromDirectory:
    """Test directory-based name detection."""

    def test_detect_normal_directory_name(self, tmp_path):
        """Should return clean directory name."""
        test_dir = tmp_path / "my-project"
        test_dir.mkdir()

        result = ProjectIdentifier.detect_from_directory(test_dir)
        assert result == "my-project"

    def test_detect_directory_with_underscores(self, tmp_path):
        """Should keep underscores in directory name."""
        test_dir = tmp_path / "my_project"
        test_dir.mkdir()

        result = ProjectIdentifier.detect_from_directory(test_dir)
        assert result == "my_project"

    def test_detect_directory_with_special_chars(self, tmp_path):
        """Should replace special chars with hyphens."""
        test_dir = tmp_path / "my@project#123"
        test_dir.mkdir()

        result = ProjectIdentifier.detect_from_directory(test_dir)
        assert result == "my-project-123"

    def test_detect_directory_with_spaces(self, tmp_path):
        """Should replace spaces with hyphens."""
        test_dir = tmp_path / "my project"
        test_dir.mkdir()

        result = ProjectIdentifier.detect_from_directory(test_dir)
        assert result == "my-project"

    def test_detect_directory_only_special_chars(self, tmp_path):
        """Should convert special chars to hyphens."""
        test_dir = tmp_path / "@#$%"
        test_dir.mkdir()

        result = ProjectIdentifier.detect_from_directory(test_dir)
        # @#$% becomes ---- (not hash because "----" != "-")
        assert result == "----"

    def test_detect_directory_dot(self):
        """Should return hash for '.' directory."""
        test_dir = Path()

        result = ProjectIdentifier.detect_from_directory(test_dir)
        assert result.startswith("project-")
        assert len(result) == 24

    def test_detect_directory_empty_name(self):
        """Should return hash for empty directory name."""
        # Create a Path with empty name (shouldn't happen normally but test edge case)
        with patch.object(Path, "name", ""):
            test_dir = Path("/tmp/test")
            result = ProjectIdentifier.detect_from_directory(test_dir)
            assert result.startswith("project-")

    def test_detect_hash_format(self, tmp_path):
        """Should generate hash for single hyphen directory."""
        # Create directory that becomes exactly "-" after cleaning
        # Actually, we need to test hash generation, so use "." directory
        test_dir = Path()

        result = ProjectIdentifier.detect_from_directory(test_dir)
        # Hash should be deterministic
        result2 = ProjectIdentifier.detect_from_directory(test_dir)
        assert result == result2

        # Format: project-<16 hex chars>
        assert result.startswith("project-")
        hash_part = result[8:]
        assert len(hash_part) == 16
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_detect_directory_with_only_hyphen(self, tmp_path):
        """Should return hash when clean name is exactly a single hyphen."""
        # Test that a name that becomes exactly "-" after cleaning triggers hash fallback
        with patch.object(Path, "name", "-"):
            test_dir = tmp_path / "test"
            test_dir.mkdir()

            result = ProjectIdentifier.detect_from_directory(test_dir)
            # When name is exactly "-", should return hash-based identifier
            assert result.startswith("project-")
            hash_part = result[8:]
            assert len(hash_part) == 16
            assert all(c in "0123456789abcdef" for c in hash_part)

    def test_detect_alphanumeric_with_hyphens(self, tmp_path):
        """Should preserve alphanumeric chars and hyphens."""
        test_dir = tmp_path / "project-123-abc"
        test_dir.mkdir()

        result = ProjectIdentifier.detect_from_directory(test_dir)
        assert result == "project-123-abc"


class TestDetect:
    """Test combined detection with priority order."""

    def test_detect_git_repo_returns_git_name(self, tmp_path):
        """Should prefer Git name over directory name."""
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            mock_origin = Mock()
            mock_origin.url = "https://github.com/user/git-repo.git"
            mock_repo.return_value.remotes.origin = mock_origin

            # Directory has different name
            test_dir = tmp_path / "local-dir"
            test_dir.mkdir()

            result = ProjectIdentifier.detect(test_dir)
            assert result == "git-repo"  # Git name wins

    def test_detect_non_git_returns_directory_name(self, tmp_path):
        """Should fall back to directory name for non-Git repos."""
        with patch(
            "codecontext.utils.project_identifier.Repo",
            side_effect=InvalidGitRepositoryError,
        ):
            test_dir = tmp_path / "my-directory"
            test_dir.mkdir()

            result = ProjectIdentifier.detect(test_dir)
            assert result == "my-directory"

    def test_detect_priority_order(self, tmp_path):
        """Should follow priority: Git → directory → hash."""
        # Test 1: Git available → use Git
        with patch("codecontext.utils.project_identifier.Repo") as mock_repo:
            mock_origin = Mock()
            mock_origin.url = "https://github.com/user/repo.git"
            mock_repo.return_value.remotes.origin = mock_origin

            result = ProjectIdentifier.detect(tmp_path)
            assert result == "repo"

        # Test 2: No Git, good directory → use directory
        with patch(
            "codecontext.utils.project_identifier.Repo",
            side_effect=InvalidGitRepositoryError,
        ):
            test_dir = tmp_path / "my-dir"
            test_dir.mkdir()

            result = ProjectIdentifier.detect(test_dir)
            assert result == "my-dir"

        # Test 3: No Git, directory with special chars → cleaned name
        with patch(
            "codecontext.utils.project_identifier.Repo",
            side_effect=InvalidGitRepositoryError,
        ):
            test_dir = tmp_path / "@@@"
            test_dir.mkdir()

            result = ProjectIdentifier.detect(test_dir)
            # @@@ becomes --- (not hash because "---" != "-")
            assert result == "---"


class TestNormalize:
    """Test project ID normalization."""

    def test_normalize_lowercase_conversion(self):
        """Should convert to lowercase."""
        result = ProjectIdentifier.normalize("My-Project")
        assert result == "my-project"

    def test_normalize_uppercase(self):
        """Should convert all uppercase to lowercase."""
        result = ProjectIdentifier.normalize("MYPROJECT")
        assert result == "myproject"

    def test_normalize_mixed_case(self):
        """Should normalize mixed case."""
        result = ProjectIdentifier.normalize("MyAwesomeProject")
        assert result == "myawesomeproject"

    def test_normalize_special_chars_replacement(self):
        """Should replace special chars with hyphens."""
        result = ProjectIdentifier.normalize("project@123")
        assert result == "project-123"

    def test_normalize_multiple_special_chars(self):
        """Should replace all special chars and strip trailing hyphens."""
        result = ProjectIdentifier.normalize("my#project@2024!")
        assert result == "my-project-2024"

    def test_normalize_leading_hyphens_removed(self):
        """Should remove leading hyphens."""
        result = ProjectIdentifier.normalize("--project")
        assert result == "project"

    def test_normalize_trailing_hyphens_removed(self):
        """Should remove trailing hyphens."""
        result = ProjectIdentifier.normalize("project--")
        assert result == "project"

    def test_normalize_leading_and_trailing_hyphens(self):
        """Should remove both leading and trailing hyphens."""
        result = ProjectIdentifier.normalize("--my-project--")
        assert result == "my-project"

    def test_normalize_length_under_limit(self):
        """Should not truncate strings under 63 chars."""
        short_id = "a" * 50
        result = ProjectIdentifier.normalize(short_id)
        assert result == short_id
        assert len(result) == 50

    def test_normalize_length_at_limit(self):
        """Should not truncate strings at exactly 63 chars."""
        exact_id = "a" * 63
        result = ProjectIdentifier.normalize(exact_id)
        assert result == exact_id
        assert len(result) == 63

    def test_normalize_length_over_limit(self):
        """Should truncate strings over 63 chars with hash suffix."""
        long_id = "a" * 100
        result = ProjectIdentifier.normalize(long_id)

        # Should be truncated to 50 chars + "-" + 10 char hash = 61 chars
        assert len(result) == 61
        assert result.startswith("a" * 50 + "-")

        # Hash part should be 10 hex chars
        hash_part = result[51:]
        assert len(hash_part) == 10
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_normalize_length_truncation_deterministic(self):
        """Should generate same hash for same input."""
        long_id = "my-very-long-project-name-that-exceeds-the-maximum-allowed-length-limit"
        result1 = ProjectIdentifier.normalize(long_id)
        result2 = ProjectIdentifier.normalize(long_id)

        assert result1 == result2
        assert len(result1) == 61

    def test_normalize_empty_string_fallback(self):
        """Should return default for empty string."""
        result = ProjectIdentifier.normalize("")
        assert result == "default-project"

    def test_normalize_only_special_chars_fallback(self):
        """Should return default for only special chars."""
        result = ProjectIdentifier.normalize("@#$%^&*()")
        assert result == "default-project"

    def test_normalize_only_hyphens_fallback(self):
        """Should return default for only hyphens."""
        result = ProjectIdentifier.normalize("-----")
        assert result == "default-project"

    def test_normalize_whitespace_only_fallback(self):
        """Should return default for whitespace only."""
        result = ProjectIdentifier.normalize("   ")
        assert result == "default-project"

    def test_normalize_preserves_existing_hyphens(self):
        """Should keep valid hyphens in name."""
        result = ProjectIdentifier.normalize("my-project-name")
        assert result == "my-project-name"

    def test_normalize_preserves_numbers(self):
        """Should keep numbers in name."""
        result = ProjectIdentifier.normalize("project123")
        assert result == "project123"

    def test_normalize_alphanumeric_with_hyphens(self):
        """Should handle complex valid names."""
        result = ProjectIdentifier.normalize("my-project-2024-v1")
        assert result == "my-project-2024-v1"

    def test_normalize_consecutive_special_chars(self):
        """Should replace consecutive special chars."""
        result = ProjectIdentifier.normalize("my@@project##2024")
        assert result == "my--project--2024"

    def test_normalize_underscore_becomes_hyphen(self):
        """Should replace underscores with hyphens."""
        result = ProjectIdentifier.normalize("my_project_name")
        assert result == "my-project-name"
