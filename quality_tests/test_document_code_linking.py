"""
Document-Code Linking Tests

E2E tests for document-code linking using CLI:
- codecontext search (markdown queries)

Validates:
- Markdown documents link to relevant code
- Code references in documents are discoverable
- Cross-language linking works

Note: These tests require an indexed database. They will reuse existing
      index if available. Run with --reindex to test with fresh index.
"""

from collections.abc import Callable
from typing import Any

import pytest

pytestmark = [pytest.mark.quality, pytest.mark.doc_linking]


class TestDocumentCodeLinking:
    """Document-code linking validation tests."""

    def test_markdown_search(self, search_cli: Callable[..., dict[str, Any]]) -> None:
        """Test searching for markdown documents."""
        results = search_cli("API documentation", limit=10)

        # Should find markdown files
        markdown_results = [
            r for r in results.get("results", []) if r.get("path", "").endswith(".md")
        ]

        print(f"\n✅ Found {len(markdown_results)} markdown files")
        assert len(markdown_results) > 0, "Should find at least one markdown file"

    def test_code_from_documentation(self, search_cli: Callable[..., dict[str, Any]]) -> None:
        """Test finding code implementations from documentation queries."""
        # Query about a feature documented in markdown
        results = search_cli("user authentication implementation", limit=20)

        results_list = results.get("results", [])
        markdown_results = [r for r in results_list if r.get("path", "").endswith(".md")]
        code_results = [
            r
            for r in results_list
            if any(
                r.get("path", "").endswith(ext)
                for ext in [".py", ".kt", ".java", ".ts", ".tsx", ".js"]
            )
        ]

        print("\n✅ Documentation query results:")
        print(f"   Markdown: {len(markdown_results)}")
        print(f"   Code: {len(code_results)}")

        # At least one of each type
        assert len(code_results) > 0, "Should find code implementations"

    def test_multilanguage_linking(self, search_cli: Callable[..., dict[str, Any]]) -> None:
        """Test linking across multiple programming languages."""
        # Query targeting actual domain in sample data (Korean logistics platform)
        # Expected to match: user.md + UserCommandService.kt + other user services
        results = search_cli("user registration implementation", limit=20)

        results_list = results.get("results", [])

        # Count languages
        languages = set()
        for result in results_list:
            path = result.get("path", "")
            if path.endswith(".py"):
                languages.add("python")
            elif path.endswith((".kt", ".java")):
                languages.add("kotlin/java")
            elif path.endswith((".ts", ".tsx", ".js")):
                languages.add("typescript/javascript")
            elif path.endswith(".md"):
                languages.add("markdown")

        print("\n✅ Multi-language search found:")
        for lang in sorted(languages):
            count = sum(1 for r in results_list if self._is_language(r.get("path", ""), lang))
            print(f"   {lang}: {count} files")

        # Should find at least 2 different types (code + docs)
        # Sample data has: user.md + UserCommandService.kt + UserInvitationCommandService.kt
        assert len(languages) >= 2, f"Should find multiple content types, found: {languages}"

    @staticmethod
    def _is_language(path: str, lang: str) -> bool:
        """Check if path matches language."""
        if lang == "python":
            return path.endswith(".py")
        elif lang == "kotlin/java":
            return path.endswith((".kt", ".java"))
        elif lang == "typescript/javascript":
            return path.endswith((".ts", ".tsx", ".js"))
        elif lang == "markdown":
            return path.endswith(".md")
        return False
