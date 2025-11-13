"""Tests for language-specific parsers.

These tests verify AST parsing, code object extraction,
and language detection across all supported languages.
"""

from pathlib import Path

import pytest
from codecontext.indexer.ast_parser import LanguageDetector
from codecontext.parsers.factory import ParserFactory
from codecontext_core.models import Language, ObjectType


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


class TestPythonParser:
    """Test Python-specific parsing."""

    @pytest.fixture
    def factory(self):
        """Create parser factory for testing."""
        return ParserFactory()

    def test_parses_python_class(self, factory):
        """Should parse Python class definition."""
        code = """
class MyClass:
    def __init__(self):
        pass

    def my_method(self):
        return 42
"""
        parser = factory.get_parser_by_language(Language.PYTHON)
        objects = parser.extract_code_objects(Path("/test.py"), code)

        # Should find class and methods
        assert len(objects) > 0
        class_objs = [o for o in objects if o.object_type == ObjectType.CLASS]
        assert len(class_objs) > 0
        assert class_objs[0].name == "MyClass"

    def test_parses_python_function(self, factory):
        """Should parse Python function definition."""
        code = """
def my_function(arg1, arg2):
    return arg1 + arg2
"""
        parser = factory.get_parser_by_language(Language.PYTHON)
        objects = parser.extract_code_objects(Path("/test.py"), code)

        # Should find function
        funcs = [o for o in objects if o.object_type == ObjectType.FUNCTION]
        assert len(funcs) > 0
        assert funcs[0].name == "my_function"

    def test_handles_python_syntax_error(self, factory):
        """Should handle Python syntax errors gracefully."""
        code = """
def broken_function(
    # Syntax error: unclosed parenthesis
"""
        parser = factory.get_parser_by_language(Language.PYTHON)
        objects = parser.extract_code_objects(Path("/test.py"), code)

        # Should return empty or handle gracefully
        assert isinstance(objects, list)


class TestJavaParser:
    """Test Java-specific parsing."""

    @pytest.fixture
    def factory(self):
        """Create parser factory for testing."""
        return ParserFactory()

    def test_parses_java_class(self, factory):
        """Should parse Java class definition."""
        code = """
public class MyClass {
    private int value;

    public void myMethod() {
        System.out.println("Hello");
    }
}
"""
        parser = factory.get_parser_by_language(Language.JAVA)
        objects = parser.extract_code_objects(Path("/Test.java"), code)

        # Should find class
        assert len(objects) > 0
        class_objs = [o for o in objects if o.object_type == ObjectType.CLASS]
        assert len(class_objs) > 0

    def test_parses_java_interface(self, factory):
        """Should parse Java interface definition."""
        code = """
public interface MyInterface {
    void doSomething();
}
"""
        parser = factory.get_parser_by_language(Language.JAVA)
        objects = parser.extract_code_objects(Path("/MyInterface.java"), code)

        # Should find interface
        assert len(objects) > 0


class TestJavaScriptParser:
    """Test JavaScript-specific parsing."""

    @pytest.fixture
    def factory(self):
        """Create parser factory for testing."""
        return ParserFactory()

    def test_parses_javascript_class(self, factory):
        """Should parse JavaScript ES6 class."""
        code = """
class MyClass {
    constructor() {
        this.value = 0;
    }

    myMethod() {
        return this.value;
    }
}
"""
        parser = factory.get_parser_by_language(Language.JAVASCRIPT)
        objects = parser.extract_code_objects(Path("/app.js"), code)

        # Should find class
        assert len(objects) > 0

    def test_parses_javascript_function(self, factory):
        """Should parse JavaScript function."""
        code = """
function myFunction(arg) {
    return arg * 2;
}

const arrowFunc = (x) => x + 1;
"""
        parser = factory.get_parser_by_language(Language.JAVASCRIPT)
        objects = parser.extract_code_objects(Path("/app.js"), code)

        # Should find functions
        assert len(objects) > 0


class TestTypeScriptParser:
    """Test TypeScript-specific parsing."""

    @pytest.fixture
    def factory(self):
        """Create parser factory for testing."""
        return ParserFactory()

    def test_parses_typescript_class(self, factory):
        """Should parse TypeScript class with types."""
        code = """
class MyClass {
    private value: number;

    constructor(value: number) {
        this.value = value;
    }

    public getValue(): number {
        return this.value;
    }
}
"""
        parser = factory.get_parser_by_language(Language.TYPESCRIPT)
        objects = parser.extract_code_objects(Path("/app.ts"), code)

        # Should find class
        assert len(objects) > 0

    def test_parses_typescript_interface(self, factory):
        """Should parse TypeScript interface."""
        code = """
interface User {
    name: string;
    age: number;
    email?: string;
}
"""
        parser = factory.get_parser_by_language(Language.TYPESCRIPT)
        objects = parser.extract_code_objects(Path("/types.ts"), code)

        # Should find interface
        assert len(objects) > 0


class TestKotlinParser:
    """Test Kotlin-specific parsing."""

    @pytest.fixture
    def factory(self):
        """Create parser factory for testing."""
        return ParserFactory()

    def test_parses_kotlin_class(self, factory):
        """Should parse Kotlin class."""
        code = """
class MyClass(val value: Int) {
    fun myMethod(): Int {
        return value * 2
    }
}
"""
        parser = factory.get_parser_by_language(Language.KOTLIN)
        objects = parser.extract_code_objects(Path("/Main.kt"), code)

        # Should find class
        assert len(objects) > 0

    def test_parses_kotlin_function(self, factory):
        """Should parse Kotlin top-level function."""
        code = """
fun myFunction(arg: String): Int {
    return arg.length
}
"""
        parser = factory.get_parser_by_language(Language.KOTLIN)
        objects = parser.extract_code_objects(Path("/Utils.kt"), code)

        # Should find function
        assert len(objects) > 0


class TestParserEdgeCases:
    """Test edge cases in parsing."""

    @pytest.fixture
    def factory(self):
        """Create parser factory for testing."""
        return ParserFactory()

    def test_empty_file(self, factory):
        """Should handle empty files."""
        parser = factory.get_parser_by_language(Language.PYTHON)
        objects = parser.extract_code_objects(Path("/empty.py"), "")

        assert objects == []

    def test_file_with_only_comments(self, factory):
        """Should handle files with only comments."""
        code = """
# This is a comment
# Another comment
"""
        parser = factory.get_parser_by_language(Language.PYTHON)
        objects = parser.extract_code_objects(Path("/comments.py"), code)

        # Should return empty or minimal objects
        assert isinstance(objects, list)

    def test_unicode_content(self, factory):
        """Should handle Unicode content."""
        code = """
class 한글클래스:
    def 메서드(self):
        return "테스트"
"""
        parser = factory.get_parser_by_language(Language.PYTHON)
        objects = parser.extract_code_objects(Path("/unicode.py"), code)

        # Should handle Unicode names
        assert isinstance(objects, list)

    def test_very_large_file(self, factory):
        """Should handle large files efficiently."""
        # Generate large code
        code = "\n".join([f"def func_{i}(): pass" for i in range(1000)])

        parser = factory.get_parser_by_language(Language.PYTHON)
        objects = parser.extract_code_objects(Path("/large.py"), code)

        # Should parse without timeout
        assert isinstance(objects, list)
        assert len(objects) > 0

    def test_deeply_nested_code(self, factory):
        """Should handle deeply nested code structures."""
        code = """
class Outer:
    class Inner:
        class DeepInner:
            def method(self):
                def nested_func():
                    return 42
                return nested_func
"""
        parser = factory.get_parser_by_language(Language.PYTHON)
        objects = parser.extract_code_objects(Path("/nested.py"), code)

        # Should handle nesting
        assert isinstance(objects, list)
