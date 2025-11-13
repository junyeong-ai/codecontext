"""Comprehensive tests for Python Optimizer.

Test Coverage Strategy:
- Decorator detection (property, staticmethod, classmethod, dataclass, pytest, async)
- Comprehensions (list, dict, set, generator)
- Generators (yield)
- Context managers (with)
- Type hints
- Async/await patterns
- Magic methods
- Exception handling
- Metaclasses
- Complexity calculations
- Search term enhancements

Target: 90%+ coverage (Industry Standard: Google, SonarQube)
Current: 0% → Target: 90%+
"""

from pathlib import Path

import pytest
from codecontext.parsers.factory import ParserFactory
from codecontext.parsers.language_optimizers.python_optimizer import PythonOptimizer
from codecontext_core.models import Language
from codecontext_core.models.cast_chunk import CASTChunk


@pytest.fixture
def python_optimizer():
    """Create Python optimizer instance."""
    return PythonOptimizer()


@pytest.fixture
def python_parser():
    """Create Python parser instance using factory."""
    factory = ParserFactory()
    return factory.get_parser_by_language(Language.PYTHON)


def parse_python(parser, code: str):
    """Helper to parse Python code and return relevant node."""
    tree = parser.parser.parse_text(code)
    root = tree.root_node

    # Find the first class_definition or function_definition
    for child in root.children:
        if child.type in ("class_definition", "function_definition", "decorated_definition"):
            return child

    # Return root for integration tests
    return root


def create_test_chunk(
    raw_content: str,
    node_type: str = "",
    language_metadata: dict | None = None,
    imports: list[str] | None = None,
) -> CASTChunk:
    """Helper to create test CASTChunk instances."""
    return CASTChunk(
        deterministic_id="test_chunk",
        file_path=Path("test.py"),
        language="python",
        content=raw_content,
        raw_content=raw_content,
        node_type=node_type,
        start_line=1,
        end_line=1,
        language_metadata=language_metadata or {},
        imports=imports or [],
    )


class TestPythonOptimizerDecorators:
    """Test decorator detection."""

    def test_detects_property_decorator(self, python_optimizer, python_parser):
        """Should detect @property decorator."""
        code = """
@property
def name(self):
    return self._name
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "decorated" in metadata.semantic_tags
        assert "property" in metadata.semantic_tags

    def test_detects_staticmethod_decorator(self, python_optimizer, python_parser):
        """Should detect @staticmethod decorator."""
        code = """
@staticmethod
def add(a, b):
    return a + b
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "decorated" in metadata.semantic_tags
        assert "static_method" in metadata.semantic_tags

    def test_detects_classmethod_decorator(self, python_optimizer, python_parser):
        """Should detect @classmethod decorator."""
        code = """
@classmethod
def create(cls):
    return cls()
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "decorated" in metadata.semantic_tags
        assert "class_method" in metadata.semantic_tags

    def test_detects_dataclass_decorator(self, python_optimizer, python_parser):
        """Should detect @dataclass decorator."""
        code = """
@dataclass
class User:
    name: str
    age: int
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "decorated" in metadata.semantic_tags
        assert "dataclass" in metadata.semantic_tags

    def test_detects_pytest_decorator(self, python_optimizer, python_parser):
        """Should detect pytest decorators."""
        code = """
@pytest.fixture
def user():
    return User()
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "decorated" in metadata.semantic_tags
        assert "test" in metadata.semantic_tags

    def test_multiple_decorators(self, python_optimizer, python_parser):
        """Should detect multiple decorators."""
        code = """
@decorator1
@decorator2
@decorator3
def complex_function():
    return value
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert metadata.complexity_factors.get("decorators", 0) >= 2


class TestPythonOptimizerComprehensions:
    """Test comprehension detection."""

    def test_detects_list_comprehension(self, python_optimizer, python_parser):
        """Should detect list comprehension."""
        code = """
def process():
    result = [x * 2 for x in range(10)]
    return result
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "functional" in metadata.semantic_tags
        assert metadata.complexity_factors.get("comprehensions", 0) >= 1

    def test_detects_dict_comprehension(self, python_optimizer, python_parser):
        """Should detect dict comprehension."""
        code = """
def process():
    result = {x: x * 2 for x in range(10)}
    return result
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "functional" in metadata.semantic_tags

    def test_detects_set_comprehension(self, python_optimizer, python_parser):
        """Should detect set comprehension."""
        code = """
def process():
    result = {x * 2 for x in range(10)}
    return result
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "functional" in metadata.semantic_tags

    def test_detects_generator_expression(self, python_optimizer, python_parser):
        """Should detect generator expression."""
        code = """
def process():
    result = (x * 2 for x in range(10))
    return result
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "functional" in metadata.semantic_tags

    def test_nested_comprehensions(self, python_optimizer, python_parser):
        """Should detect nested comprehensions."""
        code = """
def matrix():
    return [[i * j for j in range(10)] for i in range(10)]
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert metadata.complexity_factors.get("comprehensions", 0) >= 2


class TestPythonOptimizerGenerators:
    """Test generator detection."""

    def test_detects_yield_expression(self, python_optimizer, python_parser):
        """Should detect yield expression."""
        code = """
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "generator" in metadata.special_constructs
        assert "generator" in metadata.semantic_tags

    def test_generator_search_terms(self, python_optimizer):
        """Should add generator-specific search terms."""
        chunk = create_test_chunk(
            raw_content="def gen(): yield 1",
            node_type="function_definition",
            language_metadata={"semantic_tags": ["generator"]},
        )

        terms = python_optimizer.enhance_search_terms(chunk)

        assert "generator" in terms
        assert "yield" in terms
        assert "iterator" in terms


class TestPythonOptimizerContextManagers:
    """Test context manager detection."""

    def test_detects_with_statement(self, python_optimizer, python_parser):
        """Should detect with statement."""
        code = """
def read_file():
    with open('file.txt') as f:
        return f.read()
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "context_manager" in metadata.special_constructs
        assert "resource_management" in metadata.semantic_tags

    def test_multiple_context_managers(self, python_optimizer, python_parser):
        """Should detect multiple context managers."""
        code = """
def process():
    with open('in.txt') as f1:
        with open('out.txt') as f2:
            f2.write(f1.read())
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "context_manager" in metadata.special_constructs


class TestPythonOptimizerTypeHints:
    """Test type hint detection."""

    def test_detects_function_type_hints(self, python_optimizer, python_parser):
        """Should detect function type hints."""
        code = """
def greet(name: str) -> str:
    return f"Hello, {name}"
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "type_hints" in metadata.special_constructs
        assert "typed" in metadata.semantic_tags

    def test_detects_variable_type_hints(self, python_optimizer, python_parser):
        """Should detect variable type hints."""
        code = """
def process():
    count: int = 0
    name: str = "test"
    return count, name
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "type_hints" in metadata.special_constructs
        assert "typed" in metadata.semantic_tags

    def test_type_hint_complexity(self, python_optimizer, python_parser):
        """Should count type hints in complexity."""
        code = """
def process(a: int, b: str, c: float) -> tuple[int, str, float]:
    return a, b, c
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert metadata.complexity_factors.get("type_hints", 0) >= 1


class TestPythonOptimizerAsync:
    """Test async/await detection."""

    def test_detects_async_function(self, python_optimizer, python_parser):
        """Should detect async function."""
        code = """
async def fetch_data():
    await asyncio.sleep(1)
    return "data"
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "async_await" in metadata.special_constructs
        assert "async" in metadata.semantic_tags

    def test_async_search_terms(self, python_optimizer):
        """Should add async-specific search terms."""
        chunk = create_test_chunk(
            raw_content="async def fetch(): await sleep(1)",
            node_type="function_definition",
            language_metadata={"semantic_tags": ["async"]},
        )

        terms = python_optimizer.enhance_search_terms(chunk)

        assert "async" in terms
        assert "await" in terms
        assert "coroutine" in terms
        assert "asyncio" in terms


class TestPythonOptimizerMagicMethods:
    """Test magic method detection."""

    def test_detects_init_magic_method(self, python_optimizer, python_parser):
        """Should detect __init__ magic method."""
        code = """
class User:
    def __init__(self, name):
        self.name = name
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "magic_methods" in metadata.semantic_tags
        assert "constructor" in metadata.semantic_tags

    def test_detects_str_repr_magic_methods(self, python_optimizer, python_parser):
        """Should detect __str__ and __repr__ magic methods."""
        code = """
class User:
    def __str__(self):
        return self.name

    def __repr__(self):
        return f"User({self.name})"
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "magic_methods" in metadata.semantic_tags
        assert "representation" in metadata.semantic_tags

    def test_detects_enter_exit_magic_methods(self, python_optimizer, python_parser):
        """Should detect __enter__ and __exit__ magic methods."""
        code = """
class Resource:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "magic_methods" in metadata.semantic_tags
        assert "context_manager" in metadata.semantic_tags

    def test_detects_iter_next_magic_methods(self, python_optimizer, python_parser):
        """Should detect __iter__ and __next__ magic methods."""
        code = """
class Counter:
    def __iter__(self):
        return self

    def __next__(self):
        return self.value
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "magic_methods" in metadata.semantic_tags
        assert "iterator" in metadata.semantic_tags


class TestPythonOptimizerExceptionHandling:
    """Test exception handling detection."""

    def test_detects_try_except(self, python_optimizer, python_parser):
        """Should detect try/except blocks."""
        code = """
def process():
    try:
        risky_operation()
    except Exception as e:
        handle_error(e)
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "exception_handling" in metadata.special_constructs
        assert "error_handling" in metadata.semantic_tags

    def test_detects_try_except_finally(self, python_optimizer, python_parser):
        """Should detect try/except/finally blocks."""
        code = """
def process():
    try:
        risky_operation()
    except Exception as e:
        handle_error(e)
    finally:
        cleanup()
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "exception_handling" in metadata.special_constructs

    def test_detects_raise_statement(self, python_optimizer, python_parser):
        """Should detect raise statement."""
        code = """
def validate(value):
    if value < 0:
        raise ValueError("Value must be positive")
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "exception_handling" in metadata.special_constructs


class TestPythonOptimizerComplexity:
    """Test complexity calculation."""

    def test_calculates_low_complexity(self, python_optimizer, python_parser):
        """Should calculate low complexity for simple code."""
        code = """
def simple():
    return 42
"""
        ast = parse_python(python_parser, code)
        score = python_optimizer.calculate_complexity_score(ast, code.encode())

        assert score == 1

    def test_calculates_medium_complexity(self, python_optimizer, python_parser):
        """Should calculate medium complexity."""
        code = """
def process(value):
    if value > 0:
        return value * 2
    elif value < 0:
        return value * -1
    elif value == 0:
        return 0
    elif value == 1:
        return 1
    elif value == 2:
        return 2
    elif value == 3:
        return 3
    else:
        return 99
"""
        ast = parse_python(python_parser, code)
        score = python_optimizer.calculate_complexity_score(ast, code.encode())

        assert score >= 2

    def test_complexity_with_decorators(self, python_optimizer, python_parser):
        """Should add complexity for decorators."""
        code = """
@decorator1
@decorator2
@decorator3
@decorator4
def complex():
    return value
"""
        ast = parse_python(python_parser, code)
        score = python_optimizer.calculate_complexity_score(ast, code.encode())

        assert score >= 3

    def test_complexity_capped_at_10(self, python_optimizer, python_parser):
        """Should cap complexity at 10."""
        code = """
@decorator1
@decorator2
@decorator3
@decorator4
async def very_complex():
    result = [x for x in range(10)]
    yield result
    if a: pass
    if b: pass
    if c: pass
    if d: pass
    if e: pass
    if f: pass
    if g: pass
    if h: pass
"""
        ast = parse_python(python_parser, code)
        score = python_optimizer.calculate_complexity_score(ast, code.encode())

        assert score <= 10


class TestPythonOptimizerSearchTerms:
    """Test search term generation."""

    def test_adds_python_class_terms(self, python_optimizer):
        """Should add Python-specific class terms."""
        chunk = create_test_chunk(
            raw_content="class MyClass: pass",
            node_type="class_definition",
        )

        terms = python_optimizer.enhance_search_terms(chunk)

        assert "python class" in terms
        assert "py class" in terms

    def test_adds_python_function_terms(self, python_optimizer):
        """Should add Python-specific function terms."""
        chunk = create_test_chunk(
            raw_content="def my_function(): pass",
            node_type="function_definition",
        )

        terms = python_optimizer.enhance_search_terms(chunk)

        assert "python function" in terms
        assert "py function" in terms
        assert "def" in terms

    def test_adds_dataclass_terms(self, python_optimizer):
        """Should add dataclass-specific search terms."""
        chunk = create_test_chunk(
            raw_content="@dataclass\nclass User: pass",
            node_type="class_definition",
            language_metadata={"semantic_tags": ["dataclass"]},
        )

        terms = python_optimizer.enhance_search_terms(chunk)

        assert "dataclass" in terms
        assert "data class" in terms
        assert "@dataclass" in terms

    def test_adds_test_terms(self, python_optimizer):
        """Should add test-specific search terms."""
        chunk = create_test_chunk(
            raw_content="def test_something(): pass",
            node_type="function_definition",
            language_metadata={"semantic_tags": ["test"]},
        )

        terms = python_optimizer.enhance_search_terms(chunk)

        assert "test" in terms
        assert "unit test" in terms

    def test_adds_numpy_import_terms(self, python_optimizer):
        """Should add numpy-specific search terms."""
        chunk = create_test_chunk(
            raw_content="def process(): pass",
            node_type="function_definition",
            imports=["numpy as np"],
        )

        terms = python_optimizer.enhance_search_terms(chunk)

        assert "numpy" in terms
        assert "array" in terms

    def test_adds_pandas_import_terms(self, python_optimizer):
        """Should add pandas-specific search terms."""
        chunk = create_test_chunk(
            raw_content="def process(): pass",
            node_type="function_definition",
            imports=["pandas as pd"],
        )

        terms = python_optimizer.enhance_search_terms(chunk)

        assert "pandas" in terms
        assert "dataframe" in terms

    def test_removes_duplicate_terms(self, python_optimizer):
        """Should remove duplicate search terms."""
        chunk = create_test_chunk(
            raw_content="@dataclass\nclass User: pass",
            node_type="class_definition",
            language_metadata={"semantic_tags": ["dataclass"]},
            imports=["dataclasses"],
        )

        terms = python_optimizer.enhance_search_terms(chunk)

        # Should have unique terms
        assert len(terms) == len(set(terms))


class TestPythonOptimizerIntegration:
    """Integration tests with real code."""

    def test_optimize_chunk_integration(self, python_optimizer, python_parser):
        """Should optimize chunk with all features."""
        code = """
@dataclass
class UserRepository:
    async def get_user(self, user_id: int) -> User:
        try:
            with db.session() as session:
                user = await session.query(User).filter_by(id=user_id).first()
                return user
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
"""
        ast = parse_python(python_parser, code)

        chunk = create_test_chunk(
            raw_content=code,
            node_type="class_definition",
        )

        optimized = python_optimizer.optimize_chunk(chunk, ast)

        # Should have metadata
        assert optimized.language_metadata is not None
        assert "semantic_tags" in optimized.language_metadata
        assert "special_constructs" in optimized.language_metadata

        # Should have search keywords
        assert optimized.search_keywords is not None
        assert len(optimized.search_keywords) > 0

    def test_complex_dataclass_example(self, python_optimizer, python_parser):
        """Should handle complex dataclass."""
        code = """
@dataclass
class Config:
    name: str
    value: int

    def __post_init__(self):
        self.validate()
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "dataclass" in metadata.semantic_tags
        assert "typed" in metadata.semantic_tags


class TestPythonOptimizerEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_function(self, python_optimizer, python_parser):
        """Should handle empty function."""
        code = """
def empty():
    pass
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        # Should not crash
        assert isinstance(metadata.special_constructs, list)
        assert isinstance(metadata.semantic_tags, list)

    def test_empty_class(self, python_optimizer, python_parser):
        """Should handle empty class."""
        code = """
class Empty:
    pass
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        # Should not crash
        assert isinstance(metadata.special_constructs, list)

    def test_chunk_without_metadata(self, python_optimizer):
        """Should handle chunk without language_metadata."""
        chunk = CASTChunk(
            deterministic_id="test",
            file_path=Path("test.py"),
            language="python",
            content="class Test: pass",
            raw_content="class Test: pass",
            node_type="class_definition",
            start_line=1,
            end_line=1,
        )

        # Should not crash
        terms = python_optimizer.enhance_search_terms(chunk)
        assert isinstance(terms, list)


class TestPythonOptimizerFeatureCombinations:
    """Test combinations of multiple features."""

    def test_dataclass_with_type_hints(self, python_optimizer, python_parser):
        """Should detect dataclass with type hints."""
        code = """
@dataclass
class User:
    name: str
    age: int
    email: str
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "dataclass" in metadata.semantic_tags
        assert "typed" in metadata.semantic_tags

    def test_async_with_context_manager(self, python_optimizer, python_parser):
        """Should detect async with context manager."""
        code = """
async def process():
    async with aiohttp.ClientSession() as session:
        response = await session.get(url)
        return await response.text()
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "async" in metadata.semantic_tags
        assert "context_manager" in metadata.special_constructs

    def test_generator_with_comprehension(self, python_optimizer, python_parser):
        """Should detect generator with comprehension."""
        code = """
def process():
    yield from (x * 2 for x in range(10))
"""
        ast = parse_python(python_parser, code)
        metadata = python_optimizer.extract_language_features(ast, code.encode())

        assert "generator" in metadata.semantic_tags
        assert "functional" in metadata.semantic_tags
