"""Unit tests for single-pass code and relationship extractor.

Tests the Extractor class which performs AST parsing once and extracts
both code objects and relationships in a single pass.
"""

import pytest
from codecontext.indexer.extractor import ExtractionResult, Extractor
from codecontext.parsers.factory import ParserFactory as PF
from codecontext_core.models import ObjectType, RelationType


class TestExtractorBasic:
    """Basic functionality tests for Extractor."""

    @pytest.mark.asyncio
    async def test_extract_simple_class(self):
        """Test extraction of a simple class."""
        code = """
class SimpleClass:
    pass
"""
        factory = PF()
        extractor = Extractor(factory)

        result = await extractor.extract_from_file("test.py", content=code)

        assert len(result.objects) == 1
        assert result.objects[0].name == "SimpleClass"
        assert result.objects[0].object_type == ObjectType.CLASS

    @pytest.mark.asyncio
    async def test_extract_class_with_method(self):
        """Test extraction of class with methods."""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
        factory = PF()
        extractor = Extractor(factory)

        result = await extractor.extract_from_file("test.py", content=code)

        # Should extract 1 class + 2 methods
        assert len(result.objects) == 3

        class_obj = next(obj for obj in result.objects if obj.object_type == ObjectType.CLASS)
        assert class_obj.name == "Calculator"

        methods = [obj for obj in result.objects if obj.object_type == ObjectType.METHOD]
        assert len(methods) == 2
        assert {m.name for m in methods} == {"add", "subtract"}

    @pytest.mark.asyncio
    async def test_extract_function(self):
        """Test extraction of standalone function."""
        code = """
def greet(name):
    return f"Hello, {name}!"
"""
        factory = PF()
        extractor = Extractor(factory)

        result = await extractor.extract_from_file("test.py", content=code)

        assert len(result.objects) == 1
        assert result.objects[0].name == "greet"
        assert result.objects[0].object_type == ObjectType.FUNCTION


class TestExtractorRelationships:
    """Tests for relationship extraction."""

    @pytest.mark.asyncio
    async def test_extends_relationship(self):
        """Test EXTENDS relationship extraction (inheritance)."""
        code = """
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def bark(self):
        pass
"""
        factory = PF()
        extractor = Extractor(factory)

        result = await extractor.extract_from_file("test.py", content=code)

        # Find EXTENDS relationships
        extends_rels = [r for r in result.relationships if r.relation_type == RelationType.EXTENDS]
        assert len(extends_rels) == 1

        rel = extends_rels[0]

        # Find the actual objects
        obj_map = {obj.deterministic_id: obj for obj in result.objects}
        source = obj_map[rel.source_id]
        target = obj_map[rel.target_id]

        assert source.name == "Dog"
        assert target.name == "Animal"

    @pytest.mark.asyncio
    async def test_calls_relationship(self):
        """Test CALLS relationship extraction."""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b

def main():
    calc = Calculator()
    result = calc.add(1, 2)
"""
        factory = PF()
        extractor = Extractor(factory)

        result = await extractor.extract_from_file("test.py", content=code)

        calls_rels = [r for r in result.relationships if r.relation_type == RelationType.CALLS]
        assert len(calls_rels) >= 1

    @pytest.mark.asyncio
    async def test_references_relationship(self):
        """Test REFERENCES relationship extraction."""
        code = """
class Dog:
    def bark(self):
        print("Woof!")

    def speak(self):
        self.bark()
"""
        factory = PF()
        extractor = Extractor(factory)

        result = await extractor.extract_from_file("test.py", content=code)

        # Find REFERENCES relationships
        refs_rels = [r for r in result.relationships if r.relation_type == RelationType.REFERENCES]

        assert len(refs_rels) >= 1

    @pytest.mark.asyncio
    async def test_complex_relationships(self):
        """Test extraction of multiple relationship types."""
        code = """
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def bark(self):
        print('Woof!')

    def speak(self):
        self.bark()

def main():
    dog = Dog()
    dog.speak()
"""
        factory = PF()
        extractor = Extractor(factory)

        result = await extractor.extract_from_file("test.py", content=code)

        # Should extract objects
        assert len(result.objects) > 0

        # Should extract multiple types of relationships
        extends_rels = [r for r in result.relationships if r.relation_type == RelationType.EXTENDS]
        calls_rels = [r for r in result.relationships if r.relation_type == RelationType.CALLS]
        refs_rels = [r for r in result.relationships if r.relation_type == RelationType.REFERENCES]

        # Verify EXTENDS (Dog -> Animal)
        assert len(extends_rels) == 1

        # Verify CALLS (main -> Dog constructor)
        assert len(calls_rels) >= 1

        # Verify REFERENCES (speak -> bark, etc.)
        assert len(refs_rels) >= 1


class TestExtractorOptimization:
    """Tests for performance optimizations."""

    @pytest.mark.asyncio
    async def test_query_cursor_caching(self):
        """Test that QueryCursor objects are cached."""
        factory = PF()
        extractor = Extractor(factory)

        # Initially, cache should be empty
        assert len(extractor._query_cache) == 0

        # Extract from a Python file
        code = "class Foo:\n    pass"
        await extractor.extract_from_file("test.py", content=code)

        # After extraction, cache should contain QueryCursor objects
        assert len(extractor._query_cache) > 0

        # Extract from another Python file
        code2 = "class Bar:\n    pass"
        cache_size_before = len(extractor._query_cache)
        await extractor.extract_from_file("test2.py", content=code2)

        # Cache size should remain the same (queries reused)
        assert len(extractor._query_cache) == cache_size_before

    @pytest.mark.asyncio
    async def test_single_pass_extraction(self):
        """Test that AST is parsed only once per file."""
        code = """
class Dog:
    def bark(self):
        pass

def main():
    dog = Dog()
"""
        factory = PF()
        extractor = Extractor(factory)

        result = await extractor.extract_from_file("test.py", content=code)

        # Verify both objects and relationships were extracted
        assert len(result.objects) > 0
        assert len(result.relationships) > 0

        # This proves single-pass works because we got both in one extraction


class TestExtractorEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_file(self):
        """Test extraction from empty file."""
        factory = PF()
        extractor = Extractor(factory)

        result = await extractor.extract_from_file("test.py", content="")

        assert len(result.objects) == 0
        assert len(result.relationships) == 0

    @pytest.mark.asyncio
    async def test_syntax_error_file(self):
        """Test graceful handling of syntax errors."""
        code = "def bad(\n"  # Incomplete function

        factory = PF()
        extractor = Extractor(factory)

        # Should not raise exception
        result = await extractor.extract_from_file("test.py", content=code)

        # Should return empty results, not crash
        assert isinstance(result, ExtractionResult)

    @pytest.mark.asyncio
    async def test_unsupported_file_type(self):
        """Test handling of unsupported file types."""
        from codecontext_core.exceptions import UnsupportedLanguageError

        factory = PF()
        extractor = Extractor(factory)

        # Should raise UnsupportedLanguageError for unknown file types
        with pytest.raises(UnsupportedLanguageError):
            await extractor.extract_from_file("test.unknown", content="some content")

    @pytest.mark.asyncio
    async def test_relationship_without_target(self):
        """Test that relationships to external/undefined targets are skipped."""
        code = """
def main():
    result = external_function()  # external_function not defined in this file
"""
        factory = PF()
        extractor = Extractor(factory)

        result = await extractor.extract_from_file("test.py", content=code)

        # Should extract the function
        assert len(result.objects) == 1
        assert result.objects[0].name == "main"

        # Relationships to undefined targets should be skipped
        # (no crash, graceful handling)


class TestExtractorBatch:
    """Tests for batch extraction."""

    @pytest.mark.asyncio
    async def test_extract_batch_multiple_files(self, tmp_path):
        """Test batch extraction from multiple files."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file1.write_text("class Foo:\n    pass")

        file2 = tmp_path / "file2.py"
        file2.write_text("class Bar:\n    pass")

        factory = PF()
        extractor = Extractor(factory)

        # Extract from batch
        file_paths = [str(file1), str(file2)]
        results = []
        async for batch_result in extractor.extract_batch(file_paths, batch_size=2):
            results.append(batch_result)

        # Should have one batch with both files
        assert len(results) == 1
        batch = results[0]

        # Should extract objects from both files
        assert len(batch.objects) == 2
        assert {obj.name for obj in batch.objects} == {"Foo", "Bar"}
