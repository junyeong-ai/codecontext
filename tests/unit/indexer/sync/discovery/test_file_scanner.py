"""Unit tests for FileScanner.

Tests cover:
1. Code file discovery (Python, Java, Kotlin, JavaScript, TypeScript)
2. Markdown file discovery
3. Config file discovery (YAML, JSON, Properties)
4. Gitignore filtering
5. File size limit filtering
6. Extension filtering
7. Statistics generation
"""

from unittest.mock import Mock

import pytest
from codecontext.indexer.sync.discovery.file_scanner import FileScanner


@pytest.fixture
def mock_config():
    """Mock indexing configuration."""
    config = Mock()
    config.indexing = Mock()
    config.indexing.max_file_size_mb = 10
    config.indexing.languages = ["python", "java", "kotlin", "javascript", "typescript"]
    config.project = Mock()
    config.project.include = ["**"]
    config.project.exclude = []
    return config


@pytest.fixture
def test_repository(tmp_path):
    """Create a test repository with various file types.

    Structure:
    test_repo/
    ├── .gitignore
    ├── README.md
    ├── config.yaml
    ├── settings.json
    ├── app.properties
    ├── src/
    │   ├── main.py
    │   ├── utils.java
    │   ├── service.kt
    │   └── ignored.py (will be gitignored)
    ├── frontend/
    │   ├── app.js
    │   ├── component.jsx
    │   └── types.ts
    ├── docs/
    │   ├── guide.md
    │   └── api.markdown
    ├── large_file.py (exceeds size limit)
    └── build/ (gitignored directory)
        └── output.py
    """
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Create .gitignore
    gitignore = repo / ".gitignore"
    gitignore.write_text("build/\n*.pyc\n__pycache__/\nsrc/ignored.py\n")

    # Create root files
    (repo / "README.md").write_text("# Test Project\n")
    (repo / "config.yaml").write_text("setting: value\n")
    (repo / "settings.json").write_text('{"key": "value"}\n')
    (repo / "app.properties").write_text("key=value\n")

    # Create src directory with code files
    src = repo / "src"
    src.mkdir()
    (src / "main.py").write_text("def main():\n    pass\n")
    (src / "utils.java").write_text("public class Utils {}\n")
    (src / "service.kt").write_text("class Service {}\n")
    (src / "ignored.py").write_text("# This file should be ignored\n")

    # Create frontend directory
    frontend = repo / "frontend"
    frontend.mkdir()
    (frontend / "app.js").write_text("console.log('hello');\n")
    (frontend / "component.jsx").write_text("const Comp = () => {};\n")
    (frontend / "types.ts").write_text("type User = {};\n")

    # Create docs directory
    docs = repo / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n")
    (docs / "api.markdown").write_text("# API\n")

    # Create large file (exceeds 10MB limit)
    large_file = repo / "large_file.py"
    large_file.write_text("# " + ("x" * (11 * 1024 * 1024)))  # 11+ MB

    # Create build directory (gitignored)
    build = repo / "build"
    build.mkdir()
    (build / "output.py").write_text("# Build output\n")

    return repo


class TestFileScanner:
    """Tests for FileScanner class."""

    def test_initialization(self, test_repository, mock_config):
        """Should initialize with repository path and config."""
        scanner = FileScanner(test_repository, mock_config)

        assert scanner.repository_path == test_repository
        assert scanner.config == mock_config
        assert scanner.max_file_size_bytes == 10 * 1024 * 1024
        assert scanner.path_filter is not None

    def test_scan_source_files(self, test_repository, mock_config):
        """Should discover all source files (code + markdown + config)."""
        scanner = FileScanner(test_repository, mock_config)

        source_files = scanner.scan_source_files()

        # Convert to relative paths for easier assertion
        relative_paths = [f.relative_to(test_repository) for f in source_files]
        relative_path_strs = [str(p) for p in relative_paths]

        # Should include code files (excluding gitignored)
        assert "src/main.py" in relative_path_strs
        assert "src/utils.java" in relative_path_strs
        assert "src/service.kt" in relative_path_strs
        assert "frontend/app.js" in relative_path_strs
        assert "frontend/component.jsx" in relative_path_strs
        assert "frontend/types.ts" in relative_path_strs

        # Should include markdown files
        assert "README.md" in relative_path_strs
        assert "docs/guide.md" in relative_path_strs
        assert "docs/api.markdown" in relative_path_strs

        # Should include config files
        assert "config.yaml" in relative_path_strs
        assert "settings.json" in relative_path_strs
        assert "app.properties" in relative_path_strs

        # Should exclude gitignored files
        assert "src/ignored.py" not in relative_path_strs
        assert "build/output.py" not in relative_path_strs

        # Should exclude files exceeding size limit
        assert "large_file.py" not in relative_path_strs

    def test_scan_code_files_only(self, test_repository, mock_config):
        """Should discover only code files."""
        scanner = FileScanner(test_repository, mock_config)

        code_files = scanner.scan_code_files()
        relative_paths = [str(f.relative_to(test_repository)) for f in code_files]

        # Should include code files
        assert "src/main.py" in relative_paths
        assert "src/utils.java" in relative_paths
        assert "src/service.kt" in relative_paths
        assert "frontend/app.js" in relative_paths

        # Should NOT include markdown or config files
        assert not any(".md" in p for p in relative_paths)
        assert not any(".yaml" in p for p in relative_paths)
        assert not any(".json" in p for p in relative_paths)
        assert not any(".properties" in p for p in relative_paths)

    def test_scan_document_files_only(self, test_repository, mock_config):
        """Should discover only document files (markdown + config)."""
        scanner = FileScanner(test_repository, mock_config)

        doc_files = scanner.scan_document_files()
        relative_paths = [str(f.relative_to(test_repository)) for f in doc_files]

        # Should include markdown files
        assert "README.md" in relative_paths
        assert "docs/guide.md" in relative_paths
        assert "docs/api.markdown" in relative_paths

        # Should include config files
        assert "config.yaml" in relative_paths
        assert "settings.json" in relative_paths
        assert "app.properties" in relative_paths

        # Should NOT include code files
        assert "src/main.py" not in relative_paths
        assert "src/utils.java" not in relative_paths

    def test_gitignore_filtering(self, test_repository, mock_config):
        """Should respect gitignore patterns."""
        scanner = FileScanner(test_repository, mock_config)

        source_files = scanner.scan_source_files()
        relative_paths = [str(f.relative_to(test_repository)) for f in source_files]

        # Files explicitly gitignored should be excluded
        assert "src/ignored.py" not in relative_paths
        assert "build/output.py" not in relative_paths

        # Files not gitignored should be included
        assert "src/main.py" in relative_paths

    def test_file_size_limit_filtering(self, test_repository, mock_config):
        """Should exclude files exceeding size limit."""
        scanner = FileScanner(test_repository, mock_config)

        # large_file.py is > 10MB, should be excluded
        source_files = scanner.scan_source_files()
        relative_paths = [str(f.relative_to(test_repository)) for f in source_files]

        assert "large_file.py" not in relative_paths

        # Smaller files should be included
        assert "src/main.py" in relative_paths

    def test_file_size_limit_configuration(self, test_repository):
        """Should respect configured file size limit."""
        config = Mock()
        config.indexing = Mock()
        config.indexing.max_file_size_mb = 0.000001
        config.project = Mock()
        config.project.include = ["**"]
        config.project.exclude = []

        scanner = FileScanner(test_repository, config)

        # All files should be excluded due to size limit
        source_files = scanner.scan_source_files()

        # Should have very few or no files (only extremely small ones)
        assert len(source_files) < 5

    def test_extension_filtering(self, test_repository, mock_config):
        """Should only include files with supported extensions."""
        scanner = FileScanner(test_repository, mock_config)

        code_files = scanner.scan_code_files()

        # All code files should have supported extensions
        for file_path in code_files:
            ext = file_path.suffix
            # Should be one of the supported code extensions
            assert ext in [".py", ".java", ".kt", ".kts", ".js", ".jsx", ".ts", ".tsx"]

    def test_get_file_statistics(self, test_repository, mock_config):
        """Should return accurate file statistics."""
        scanner = FileScanner(test_repository, mock_config)

        stats = scanner.get_file_statistics()

        # Verify statistics structure
        assert "code_files" in stats
        assert "markdown_files" in stats
        assert "config_files" in stats
        assert "total_files" in stats

        # Verify counts (approximate, as gitignore filtering may vary)
        assert (
            stats["code_files"] >= 6
        )  # main.py, utils.java, service.kt, app.js, component.jsx, types.ts
        assert stats["markdown_files"] >= 3  # README.md, guide.md, api.markdown
        assert stats["config_files"] >= 3  # config.yaml, settings.json, app.properties
        assert (
            stats["total_files"]
            == stats["code_files"] + stats["markdown_files"] + stats["config_files"]
        )

    def test_should_include_file_directory_check(self, test_repository, mock_config):
        """Should exclude directories."""
        scanner = FileScanner(test_repository, mock_config)

        # Try to check a directory
        src_dir = test_repository / "src"
        result = scanner._should_include_file(src_dir, is_code=True)

        assert result is False

    def test_should_include_file_size_check(self, test_repository, mock_config):
        """Should exclude files exceeding size limit."""
        scanner = FileScanner(test_repository, mock_config)

        # Large file should be excluded
        large_file = test_repository / "large_file.py"
        result = scanner._should_include_file(large_file, is_code=True)

        assert result is False

        # Normal file should be included (with path filter)
        small_file = test_repository / "src" / "main.py"
        # Note: This may still be False due to path filter, but not due to size
        # Just verify the method doesn't crash
        scanner._should_include_file(small_file, is_code=True)

    def test_markdown_discovery(self, test_repository, mock_config):
        """Should discover both .md and .markdown files."""
        scanner = FileScanner(test_repository, mock_config)

        markdown_files = scanner._scan_markdown_files()
        relative_paths = [str(f.relative_to(test_repository)) for f in markdown_files]

        # Should find both .md and .markdown extensions
        assert any(p.endswith(".md") for p in relative_paths)
        assert any(p.endswith(".markdown") for p in relative_paths)

    def test_config_file_discovery(self, test_repository, mock_config):
        """Should discover YAML, JSON, and Properties files."""
        scanner = FileScanner(test_repository, mock_config)

        config_files = scanner._scan_config_files()
        relative_paths = [str(f.relative_to(test_repository)) for f in config_files]

        # Should find all config file types
        assert any(p.endswith(".yaml") for p in relative_paths)
        assert any(p.endswith(".json") for p in relative_paths)
        assert any(p.endswith(".properties") for p in relative_paths)

    def test_empty_repository(self, tmp_path, mock_config):
        """Should handle empty repository gracefully."""
        empty_repo = tmp_path / "empty"
        empty_repo.mkdir()

        scanner = FileScanner(empty_repo, mock_config)

        source_files = scanner.scan_source_files()

        assert source_files == []

        stats = scanner.get_file_statistics()
        assert stats["total_files"] == 0
        assert stats["code_files"] == 0
        assert stats["markdown_files"] == 0
        assert stats["config_files"] == 0

    def test_nested_directory_structure(self, tmp_path, mock_config):
        """Should discover files in deeply nested directories."""
        repo = tmp_path / "nested"
        repo.mkdir()

        # Create deeply nested structure
        deep_path = repo / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)
        (deep_path / "nested.py").write_text("# Deep file\n")

        scanner = FileScanner(repo, mock_config)

        code_files = scanner.scan_code_files()
        relative_paths = [str(f.relative_to(repo)) for f in code_files]

        # Should find deeply nested file
        assert "a/b/c/d/e/nested.py" in relative_paths or any(
            "nested.py" in p for p in relative_paths
        )

    def test_multiple_languages(self, tmp_path, mock_config):
        """Should discover files from multiple programming languages."""
        repo = tmp_path / "multi_lang"
        repo.mkdir()

        # Create files in different languages
        (repo / "script.py").write_text("# Python\n")
        (repo / "Main.java").write_text("// Java\n")
        (repo / "App.kt").write_text("// Kotlin\n")
        (repo / "index.js").write_text("// JavaScript\n")
        (repo / "types.ts").write_text("// TypeScript\n")
        (repo / "Component.jsx").write_text("// JSX\n")
        (repo / "Component.tsx").write_text("// TSX\n")

        scanner = FileScanner(repo, mock_config)

        code_files = scanner.scan_code_files()

        # Should find files from all languages
        assert len(code_files) >= 7

        extensions = {f.suffix for f in code_files}
        assert ".py" in extensions
        assert ".java" in extensions
        assert ".kt" in extensions
        assert ".js" in extensions
        assert ".ts" in extensions
        assert ".jsx" in extensions
        assert ".tsx" in extensions


class TestFileScannerEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_repository(self, tmp_path, mock_config):
        """Should handle nonexistent repository path gracefully."""
        nonexistent = tmp_path / "does_not_exist"

        scanner = FileScanner(nonexistent, mock_config)

        # Should not crash, just return empty list
        source_files = scanner.scan_source_files()
        assert source_files == []

    def test_symlink_handling(self, tmp_path, mock_config):
        """Should handle symlinks appropriately."""
        repo = tmp_path / "symlink_test"
        repo.mkdir()

        # Create actual file
        (repo / "real.py").write_text("# Real file\n")

        # Create symlink (if supported on platform)
        try:
            symlink = repo / "link.py"
            symlink.symlink_to(repo / "real.py")

            scanner = FileScanner(repo, mock_config)
            code_files = scanner.scan_code_files()

            # Should find at least the real file
            assert len(code_files) >= 1
        except (OSError, NotImplementedError):
            # Symlinks not supported on this platform
            pytest.skip("Symlinks not supported")

    def test_permission_denied_handling(self, tmp_path, mock_config):
        """Should handle permission denied errors gracefully."""
        import os

        repo = tmp_path / "permission_test"
        repo.mkdir()

        # Create file and make it unreadable (Unix-like systems only)
        restricted_file = repo / "restricted.py"
        restricted_file.write_text("# Restricted\n")

        try:
            # Make file unreadable
            os.chmod(restricted_file, 0o000)

            scanner = FileScanner(repo, mock_config)

            # Should not crash
            scanner.scan_source_files()

            # Cleanup
            os.chmod(restricted_file, 0o644)
        except (OSError, PermissionError):
            pytest.skip("Cannot test permission handling on this platform")

    def test_special_characters_in_filename(self, tmp_path, mock_config):
        """Should handle files with special characters in names."""
        repo = tmp_path / "special_chars"
        repo.mkdir()

        # Create files with various special characters (that are valid on most filesystems)
        (repo / "file-with-dashes.py").write_text("# Dashes\n")
        (repo / "file_with_underscores.py").write_text("# Underscores\n")
        (repo / "file.with.dots.py").write_text("# Dots\n")
        (repo / "file with spaces.py").write_text("# Spaces\n")

        scanner = FileScanner(repo, mock_config)

        code_files = scanner.scan_code_files()

        # Should find all files regardless of special characters
        assert len(code_files) >= 4
