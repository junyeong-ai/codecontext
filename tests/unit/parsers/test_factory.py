"""Tests for ParserFactory functionality.

Tests the ParserFactory class from parsers.factory module.
"""

import pytest
from codecontext.parsers.factory import ParserFactory
from codecontext_core.models import Language


class TestParserFactory:
    """Test parser factory functionality."""

    @pytest.fixture
    def factory(self):
        """Create parser factory for testing."""
        return ParserFactory()

    def test_creates_python_parser(self, factory):
        """Should create Python parser."""
        parser = factory.get_parser_by_language(Language.PYTHON)
        assert parser is not None
        assert parser.get_language() == Language.PYTHON

    def test_creates_java_parser(self, factory):
        """Should create Java parser."""
        parser = factory.get_parser_by_language(Language.JAVA)
        assert parser is not None
        assert parser.get_language() == Language.JAVA

    def test_creates_javascript_parser(self, factory):
        """Should create JavaScript parser."""
        parser = factory.get_parser_by_language(Language.JAVASCRIPT)
        assert parser is not None
        assert parser.get_language() == Language.JAVASCRIPT

    def test_creates_typescript_parser(self, factory):
        """Should create TypeScript parser."""
        parser = factory.get_parser_by_language(Language.TYPESCRIPT)
        assert parser is not None
        assert parser.get_language() == Language.TYPESCRIPT

    def test_creates_kotlin_parser(self, factory):
        """Should create Kotlin parser."""
        parser = factory.get_parser_by_language(Language.KOTLIN)
        assert parser is not None
        assert parser.get_language() == Language.KOTLIN
