"""Tests for language detection functionality.

Tests the LanguageDetector class from indexer.ast_parser module.
"""

from pathlib import Path

from codecontext.indexer.ast_parser import LanguageDetector
from codecontext_core.models import Language


class TestLanguageDetection:
    """Test language detection from file extensions."""

    def test_detects_python(self):
        """Should detect Python files."""
        assert LanguageDetector.detect_language(Path("test.py")) == Language.PYTHON

    def test_detects_java(self):
        """Should detect Java files."""
        assert LanguageDetector.detect_language(Path("Test.java")) == Language.JAVA

    def test_detects_javascript(self):
        """Should detect JavaScript files."""
        assert LanguageDetector.detect_language(Path("app.js")) == Language.JAVASCRIPT
        assert LanguageDetector.detect_language(Path("app.jsx")) == Language.JAVASCRIPT

    def test_detects_typescript(self):
        """Should detect TypeScript files."""
        assert LanguageDetector.detect_language(Path("app.ts")) == Language.TYPESCRIPT
        assert LanguageDetector.detect_language(Path("component.tsx")) == Language.TYPESCRIPT

    def test_detects_kotlin(self):
        """Should detect Kotlin files."""
        assert LanguageDetector.detect_language(Path("Main.kt")) == Language.KOTLIN
        assert LanguageDetector.detect_language(Path("App.kts")) == Language.KOTLIN

    def test_is_supported_python(self):
        """Should recognize Python as supported."""
        assert LanguageDetector.is_supported(Path("test.py")) is True

    def test_is_supported_unsupported_file(self):
        """Should recognize unsupported files."""
        assert LanguageDetector.is_supported(Path("readme.txt")) is False
