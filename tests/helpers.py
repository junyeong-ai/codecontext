"""Test helper functions and utilities."""

from uuid import uuid4

from codecontext_core.models import CodeObject, Language, ObjectType, Relationship, RelationType


def create_test_code_object(
    name: str = "TestClass",
    file_path: str = "/test/file.py",
    object_type: ObjectType = ObjectType.CLASS,
    language: Language = Language.PYTHON,
    content: str = "class TestClass: pass",
    start_line: int = 1,
    end_line: int = 1,
    checksum: str = "test_checksum",
) -> CodeObject:
    """Create a test CodeObject with default values."""
    return CodeObject(
        file_path=file_path,
        relative_path=file_path,
        object_type=object_type,
        name=name,
        language=language,
        start_line=start_line,
        end_line=end_line,
        content=content,
        checksum=checksum,
    )


def create_test_relationship(
    source_id: str | None = None,
    target_id: str | None = None,
    relation_type: RelationType = RelationType.CALLS,
    confidence: float = 0.8,
) -> Relationship:
    """Create a test Relationship with default values."""
    return Relationship(
        source_id=str(source_id or uuid4()),
        source_type="code_object",
        target_id=str(target_id or uuid4()),
        target_type="code_object",
        relation_type=relation_type,
        confidence=confidence,
    )


def assert_no_duplicates(ids: list[str]) -> None:
    """Assert that there are no duplicate IDs in the list."""
    unique_ids = set(ids)
    duplicates = len(ids) - len(unique_ids)
    assert duplicates == 0, f"Found {duplicates} duplicate IDs"


def assert_deterministic_ids(objects: list[CodeObject]) -> None:
    """Assert that all objects generate deterministic IDs."""
    for obj in objects:
        id1 = obj.generate_deterministic_id()
        id2 = obj.generate_deterministic_id()
        assert id1 == id2, f"IDs not deterministic: {id1} != {id2}"
        assert len(id1) == 32, f"ID length should be 32, got {len(id1)}"
        assert all(c in "0123456789abcdef" for c in id1), f"ID should be hexadecimal, got {id1}"
