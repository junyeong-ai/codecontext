from collections.abc import Callable
from typing import Any

import pytest

pytestmark = [pytest.mark.quality]


class TestDocCodeLink:
    def test_markdown_search(self, search_cli: Callable[..., dict[str, Any]]) -> None:
        results = search_cli("API documentation", limit=10)
        markdown_results = [
            r for r in results.get("results", []) if r.get("file_path", "").endswith(".md")
        ]

        print(f"\n✅ Found {len(markdown_results)} markdown files")
        assert len(markdown_results) > 0

    def test_code_from_docs(self, search_cli: Callable[..., dict[str, Any]]) -> None:
        results = search_cli("user authentication implementation", limit=20)
        results_list = results.get("results", [])

        markdown_results = [r for r in results_list if r.get("file_path", "").endswith(".md")]
        code_results = [
            r
            for r in results_list
            if any(
                r.get("file_path", "").endswith(ext)
                for ext in [".py", ".kt", ".java", ".ts", ".tsx", ".js"]
            )
        ]

        print(f"\n✅ Markdown: {len(markdown_results)}, Code: {len(code_results)}")
        assert len(code_results) > 0

    def test_multilang_linking(self, search_cli: Callable[..., dict[str, Any]]) -> None:
        results = search_cli("user registration implementation", limit=20)
        results_list = results.get("results", [])

        languages = set()
        for result in results_list:
            path = result.get("file_path", "")
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
            count = sum(1 for r in results_list if self._is_language(r.get("file_path", ""), lang))
            print(f"   {lang}: {count} files")

        assert len(languages) >= 2, f"Expected multiple content types, found: {languages}"

    @staticmethod
    def _is_language(path: str, lang: str) -> bool:
        if lang == "python":
            return path.endswith(".py")
        elif lang == "kotlin/java":
            return path.endswith((".kt", ".java"))
        elif lang == "typescript/javascript":
            return path.endswith((".ts", ".tsx", ".js"))
        elif lang == "markdown":
            return path.endswith(".md")
        return False
