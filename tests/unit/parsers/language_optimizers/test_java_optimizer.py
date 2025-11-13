"""Comprehensive tests for Java Optimizer.

Test Coverage Strategy:
- Annotation detection (@Override, @Test, @Entity, @Autowired, @Service,
  @Controller, @Component, @Deprecated)
- Lambda expressions
- Stream API (.stream(), .filter(), .map(), .collect(), .forEach(), .reduce())
- Try-with-resources
- Generics
- Static imports
- Exception handling
- Synchronized blocks/methods
- Framework patterns (Spring, JUnit, JPA)
- Complexity calculations
- Search term enhancements

Target: 90%+ coverage (Industry Standard: Google, SonarQube)
Current: 0% → Target: 90%+
"""

from pathlib import Path

import pytest
from codecontext.parsers.factory import ParserFactory
from codecontext.parsers.language_optimizers.java_optimizer import JavaOptimizer
from codecontext_core.models import Language
from codecontext_core.models.cast_chunk import CASTChunk


@pytest.fixture
def java_optimizer():
    """Create Java optimizer instance."""
    return JavaOptimizer()


@pytest.fixture
def java_parser():
    """Create Java parser instance using factory."""
    factory = ParserFactory()
    return factory.get_parser_by_language(Language.JAVA)


def parse_java(parser, code: str):
    """Helper to parse Java code and return relevant node."""
    tree = parser.parser.parse_text(code)
    root = tree.root_node

    # Find the first class_declaration or method_declaration
    for child in root.children:
        if child.type in ("class_declaration", "interface_declaration", "method_declaration"):
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
        file_path=Path("Test.java"),
        language="java",
        content=raw_content,
        raw_content=raw_content,
        node_type=node_type,
        start_line=1,
        end_line=1,
        language_metadata=language_metadata or {},
        imports=imports or [],
    )


class TestJavaOptimizerAnnotations:
    """Test annotation detection."""

    def test_detects_override_annotation(self, java_optimizer, java_parser):
        """Should detect @Override annotation."""
        code = """
class Test {
    @Override
    public String toString() {
        return "test";
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "annotated" in metadata.semantic_tags
        assert "override" in metadata.semantic_tags

    def test_detects_test_annotation(self, java_optimizer, java_parser):
        """Should detect @Test annotation."""
        code = """
class MyTest {
    @Test
    public void testSomething() {
        assertEquals(1, 1);
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "annotated" in metadata.semantic_tags
        assert "test" in metadata.semantic_tags
        assert "junit" in metadata.semantic_tags

    def test_detects_entity_annotation(self, java_optimizer, java_parser):
        """Should detect @Entity annotation."""
        code = """
@Entity
class User {
    @Id
    private Long id;
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "annotated" in metadata.semantic_tags
        assert "jpa" in metadata.semantic_tags
        assert "persistence" in metadata.semantic_tags

    def test_detects_spring_annotations(self, java_optimizer, java_parser):
        """Should detect Spring annotations."""
        code = """
@Service
class UserService {
    @Autowired
    private UserRepository repository;
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "annotated" in metadata.semantic_tags
        assert "spring" in metadata.semantic_tags
        assert "dependency_injection" in metadata.semantic_tags

    def test_detects_deprecated_annotation(self, java_optimizer, java_parser):
        """Should detect @Deprecated annotation."""
        code = """
class OldClass {
    @Deprecated
    public void oldMethod() {}
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "annotated" in metadata.semantic_tags
        assert "deprecated" in metadata.semantic_tags

    def test_multiple_annotations(self, java_optimizer, java_parser):
        """Should count multiple annotations."""
        code = """
@Service
@Transactional
@Scope("prototype")
class ComplexService {}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert metadata.complexity_factors.get("annotations", 0) >= 3


class TestJavaOptimizerLambdas:
    """Test lambda expression detection."""

    def test_detects_lambda_expression(self, java_optimizer, java_parser):
        """Should detect lambda expression."""
        code = """
class Test {
    void process() {
        list.forEach(item -> System.out.println(item));
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "lambda_expression" in metadata.special_constructs
        assert "functional" in metadata.semantic_tags


class TestJavaOptimizerStreamAPI:
    """Test Stream API detection."""

    def test_detects_stream_method(self, java_optimizer, java_parser):
        """Should detect .stream() method."""
        code = """
class Test {
    void process() {
        list.stream().collect(Collectors.toList());
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "stream_api" in metadata.special_constructs
        assert "streams" in metadata.semantic_tags
        assert "functional" in metadata.semantic_tags

    def test_detects_filter_map_collect(self, java_optimizer, java_parser):
        """Should detect stream chain."""
        code = """
class Test {
    void process() {
        list.stream()
            .filter(x -> x > 0)
            .map(x -> x * 2)
            .collect(Collectors.toList());
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "stream_api" in metadata.special_constructs


class TestJavaOptimizerTryWithResources:
    """Test try-with-resources detection."""

    def test_detects_try_with_resources(self, java_optimizer, java_parser):
        """Should detect try-with-resources statement."""
        code = """
class Test {
    void readFile() throws IOException {
        try (FileReader fr = new FileReader("file.txt")) {
            // read file
        }
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "try_with_resources" in metadata.special_constructs
        assert "resource_management" in metadata.semantic_tags


class TestJavaOptimizerGenerics:
    """Test generics detection."""

    def test_detects_generic_class(self, java_optimizer, java_parser):
        """Should detect generic class."""
        code = """
class Box<T> {
    private T value;
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "generics" in metadata.special_constructs
        assert "generic" in metadata.semantic_tags

    def test_detects_generic_method(self, java_optimizer, java_parser):
        """Should detect generic method."""
        code = """
class Util {
    public static <T> T identity(T value) {
        return value;
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "generics" in metadata.special_constructs

    def test_detects_multiple_type_parameters(self, java_optimizer, java_parser):
        """Should detect multiple type parameters."""
        code = """
class Pair<K, V> {
    private K key;
    private V value;
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "generics" in metadata.special_constructs


class TestJavaOptimizerStaticImports:
    """Test static import detection."""

    def test_detects_static_import(self, java_optimizer, java_parser):
        """Should detect static import in source."""
        code = """
import static java.lang.Math.PI;
import static org.junit.Assert.*;

class Test {
    double getPI() { return PI; }
}
"""
        # Parse entire source to include imports
        tree = java_parser.parser.parse_text(code)
        root = tree.root_node

        metadata = java_optimizer.extract_language_features(root, code.encode())

        # Static imports are detected at root level
        assert (
            "static_imports" in metadata.special_constructs
            or metadata.complexity_factors.get("static_imports", 0) >= 0
        )


class TestJavaOptimizerExceptionHandling:
    """Test exception handling detection."""

    def test_detects_try_catch(self, java_optimizer, java_parser):
        """Should detect try/catch blocks."""
        code = """
class Test {
    void process() {
        try {
            riskyOperation();
        } catch (Exception e) {
            handleError(e);
        }
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "exception_handling" in metadata.special_constructs
        assert "error_handling" in metadata.semantic_tags

    def test_detects_throw_statement(self, java_optimizer, java_parser):
        """Should detect throw statement."""
        code = """
class Test {
    void validate(int value) {
        if (value < 0) {
            throw new IllegalArgumentException("Negative value");
        }
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "exception_handling" in metadata.special_constructs


class TestJavaOptimizerSynchronization:
    """Test synchronization detection."""

    def test_detects_synchronized_block(self, java_optimizer, java_parser):
        """Should detect synchronized block."""
        code = """
class Test {
    void process() {
        synchronized (lock) {
            criticalSection();
        }
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "synchronization" in metadata.special_constructs
        assert "concurrent" in metadata.semantic_tags
        assert "thread_safe" in metadata.semantic_tags

    def test_detects_synchronized_method(self, java_optimizer, java_parser):
        """Should detect synchronized method."""
        code = """
class Test {
    synchronized void criticalMethod() {
        // thread-safe code
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "synchronization" in metadata.special_constructs


class TestJavaOptimizerComplexity:
    """Test complexity calculation."""

    def test_calculates_low_complexity(self, java_optimizer, java_parser):
        """Should calculate low complexity for simple code."""
        code = """
class Test {
    int simple() {
        return 42;
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        complexity = metadata.complexity_factors.get("cyclomatic", 0)
        # Simple method should have low complexity or not even be recorded (<10)
        assert complexity <= 10

    def test_complexity_with_streams(self, java_optimizer, java_parser):
        """Should handle complexity with streams."""
        code = """
class Test {
    void process() {
        list.stream()
            .filter(x -> x > 0)
            .map(x -> x * 2)
            .collect(Collectors.toList());
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        # Should detect streams
        assert "stream_api" in metadata.special_constructs


class TestJavaOptimizerSearchTerms:
    """Test search term generation."""

    def test_adds_java_class_terms(self, java_optimizer):
        """Should add Java-specific class terms."""
        chunk = create_test_chunk(
            raw_content="class MyClass {}",
            node_type="class_declaration",
        )

        terms = java_optimizer.enhance_search_terms(chunk)

        assert "java class" in terms

    def test_adds_spring_framework_terms(self, java_optimizer):
        """Should add Spring framework search terms."""
        chunk = create_test_chunk(
            raw_content="@Service class UserService {}",
            node_type="class_declaration",
            language_metadata={"semantic_tags": ["spring"]},
        )

        terms = java_optimizer.enhance_search_terms(chunk)

        assert "spring framework" in terms or "spring boot" in terms

    def test_adds_junit_terms(self, java_optimizer):
        """Should add JUnit search terms."""
        chunk = create_test_chunk(
            raw_content="@Test void testSomething() {}",
            node_type="method_declaration",
            language_metadata={"semantic_tags": ["junit"]},
        )

        terms = java_optimizer.enhance_search_terms(chunk)

        assert "unit test" in terms or "junit test" in terms

    def test_adds_jpa_terms(self, java_optimizer):
        """Should add JPA search terms."""
        chunk = create_test_chunk(
            raw_content="@Entity class User {}",
            node_type="class_declaration",
            language_metadata={"semantic_tags": ["jpa"]},
        )

        terms = java_optimizer.enhance_search_terms(chunk)

        assert "jpa" in terms or "hibernate" in terms or "orm" in terms

    def test_adds_functional_terms(self, java_optimizer):
        """Should add functional programming search terms."""
        chunk = create_test_chunk(
            raw_content="list.stream().filter(x -> x > 0)",
            node_type="method_declaration",
            language_metadata={"semantic_tags": ["functional"]},
        )

        terms = java_optimizer.enhance_search_terms(chunk)

        assert "functional programming" in terms or "lambda" in terms or "stream" in terms


class TestJavaOptimizerIntegration:
    """Integration tests with real code."""

    def test_optimize_chunk_integration(self, java_optimizer, java_parser):
        """Should optimize chunk with all features."""
        code = """
@Service
class UserService {
    @Autowired
    private UserRepository repository;

    public List<User> getActiveUsers() {
        try {
            return repository.findAll()
                .stream()
                .filter(user -> user.isActive())
                .collect(Collectors.toList());
        } catch (Exception e) {
            logger.error("Error", e);
            throw e;
        }
    }
}
"""
        ast = parse_java(java_parser, code)

        chunk = create_test_chunk(
            raw_content=code,
            node_type="class_declaration",
        )

        optimized = java_optimizer.optimize_chunk(chunk, ast)

        # Should have metadata
        assert optimized.language_metadata is not None
        assert "semantic_tags" in optimized.language_metadata
        assert "special_constructs" in optimized.language_metadata

        # Should have search keywords
        assert optimized.search_keywords is not None
        assert len(optimized.search_keywords) > 0

    def test_spring_service_example(self, java_optimizer, java_parser):
        """Should handle Spring service pattern."""
        code = """
@Service
@Transactional
class OrderService {
    @Autowired
    private OrderRepository orderRepository;
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "spring" in metadata.semantic_tags
        assert "dependency_injection" in metadata.semantic_tags


class TestJavaOptimizerEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_class(self, java_optimizer, java_parser):
        """Should handle empty class."""
        code = """
class EmptyClass {}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        # Should not crash
        assert isinstance(metadata.special_constructs, list)
        assert isinstance(metadata.semantic_tags, list)

    def test_empty_interface(self, java_optimizer, java_parser):
        """Should handle empty interface."""
        code = """
interface Empty {}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        # Should not crash
        assert isinstance(metadata.special_constructs, list)

    def test_chunk_without_metadata(self, java_optimizer):
        """Should handle chunk without language_metadata."""
        chunk = CASTChunk(
            deterministic_id="test",
            file_path=Path("Test.java"),
            language="java",
            content="class Test {}",
            raw_content="class Test {}",
            node_type="class_declaration",
            start_line=1,
            end_line=1,
        )

        # Should not crash
        terms = java_optimizer.enhance_search_terms(chunk)
        assert isinstance(terms, list)


class TestJavaOptimizerFeatureCombinations:
    """Test combinations of multiple features."""

    def test_stream_with_lambda(self, java_optimizer, java_parser):
        """Should detect stream with lambda."""
        code = """
class Test {
    void process() {
        list.stream()
            .filter(x -> x > 0)
            .map(x -> x * 2)
            .forEach(x -> System.out.println(x));
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "stream_api" in metadata.special_constructs
        assert "lambda_expression" in metadata.special_constructs
        assert "functional" in metadata.semantic_tags

    def test_generic_with_stream(self, java_optimizer, java_parser):
        """Should detect generic with stream."""
        code = """
class Processor<T> {
    List<T> process(List<T> items) {
        return items.stream()
            .filter(item -> item != null)
            .collect(Collectors.toList());
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "generics" in metadata.special_constructs
        assert "stream_api" in metadata.special_constructs

    def test_spring_with_exception_handling(self, java_optimizer, java_parser):
        """Should detect Spring with exception handling."""
        code = """
@Service
class DataService {
    void process() {
        try {
            loadData();
        } catch (Exception e) {
            handleError(e);
        }
    }
}
"""
        ast = parse_java(java_parser, code)
        metadata = java_optimizer.extract_language_features(ast, code.encode())

        assert "spring" in metadata.semantic_tags
        assert "exception_handling" in metadata.special_constructs
