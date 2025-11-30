"""Test builders for creating CodeObject and Relationship instances.

This module provides fluent builder APIs for creating test data with sensible
defaults, reducing boilerplate and improving test readability.
"""

from uuid import UUID, uuid4

from codecontext_core.models import (
    CodeObject,
    Language,
    ObjectType,
    Relationship,
    RelationType,
)


class CodeObjectBuilder:
    """Fluent builder for creating test CodeObject instances.

    Provides a clean API for test data creation with sensible defaults:
    - Automatic ID and checksum generation
    - Type-specific content templates
    - Sensible default values for all fields

    Example:
        >>> builder = CodeObjectBuilder()
        >>> user_class = builder.as_class("User").in_file("models.py").build()
        >>> method = builder.as_method("login", parent_id=user_class.id).build()
    """

    def __init__(self) -> None:
        """Initialize builder with default values."""
        self._id = uuid4()
        self._name = "TestObject"
        self._object_type = ObjectType.CLASS
        self._parent_id: UUID | None = None
        self._language = Language.PYTHON
        self._file_path = "test.py"
        self._relative_path = "test.py"
        self._content = "test content"
        self._start_line = 1
        self._end_line = 1
        self._checksum = f"checksum_{uuid4().hex[:8]}"

    def with_id(self, obj_id) -> "CodeObjectBuilder":
        """Set a specific ID (useful for relationship testing)."""
        self._id = obj_id
        return self

    def with_name(self, name: str) -> "CodeObjectBuilder":
        """Set the object name."""
        self._name = name
        return self

    def with_type(self, object_type: ObjectType) -> "CodeObjectBuilder":
        """Set the object type."""
        self._object_type = object_type
        return self

    def as_class(self, name: str) -> "CodeObjectBuilder":
        """Configure as a class with appropriate defaults."""
        self._object_type = ObjectType.CLASS
        self._name = name
        self._content = f"class {name}: pass"
        return self

    def as_interface(self, name: str) -> "CodeObjectBuilder":
        """Configure as an interface with appropriate defaults."""
        self._object_type = ObjectType.INTERFACE
        self._name = name
        self._content = f"interface {name} {{}}"
        self._language = Language.TYPESCRIPT  # Interfaces common in TS/Java
        return self

    def as_method(self, name: str, parent_id: UUID | None = None) -> "CodeObjectBuilder":
        """Configure as a method with appropriate defaults."""
        self._object_type = ObjectType.METHOD
        self._name = name
        if parent_id is not None:
            self._parent_id = parent_id
        self._content = f"def {name}(self): pass"
        return self

    def as_function(self, name: str) -> "CodeObjectBuilder":
        """Configure as a function with appropriate defaults."""
        self._object_type = ObjectType.FUNCTION
        self._name = name
        self._content = f"def {name}(): pass"
        return self

    def in_file(self, file_path: str) -> "CodeObjectBuilder":
        """Set the file path (also sets relative_path)."""
        self._file_path = file_path
        self._relative_path = file_path
        return self

    def with_language(self, language: Language) -> "CodeObjectBuilder":
        """Set the programming language."""
        self._language = language
        return self

    def with_parent(self, parent_id) -> "CodeObjectBuilder":
        """Set the parent object ID (for containment relationships)."""
        self._parent_id = parent_id
        return self

    def with_content(self, content: str) -> "CodeObjectBuilder":
        """Set the source code content."""
        self._content = content
        return self

    def at_lines(self, start: int, end: int) -> "CodeObjectBuilder":
        """Set the line number range."""
        self._start_line = start
        self._end_line = end
        return self

    def with_checksum(self, checksum: str) -> "CodeObjectBuilder":
        """Set a specific checksum."""
        self._checksum = checksum
        return self

    def build(self) -> CodeObject:
        """Build the CodeObject instance.

        Returns:
            Fully configured CodeObject with all fields set
        """
        return CodeObject(
            id=self._id,
            name=self._name,
            object_type=self._object_type,
            parent_id=self._parent_id,
            language=self._language,
            file_path=self._file_path,
            relative_path=self._relative_path,
            content=self._content,
            start_line=self._start_line,
            end_line=self._end_line,
            checksum=self._checksum,
        )


class RelationshipBuilder:
    """Fluent builder for creating test Relationship instances."""

    def __init__(self) -> None:
        self._source_id = uuid4()
        self._source_name = "source"
        self._source_type = "function"
        self._source_file = "test.py"
        self._source_line = 1
        self._target_id = uuid4()
        self._target_name = "target"
        self._target_type = "function"
        self._target_file = "test.py"
        self._target_line = 10
        self._relation_type = RelationType.CONTAINS

    def from_source(self, source_id) -> "RelationshipBuilder":
        self._source_id = source_id
        return self

    def to_target(self, target_id) -> "RelationshipBuilder":
        self._target_id = target_id
        return self

    def with_type(self, relation_type: RelationType) -> "RelationshipBuilder":
        self._relation_type = relation_type
        return self

    def with_source_info(
        self, name: str, obj_type: str, file: str, line: int
    ) -> "RelationshipBuilder":
        self._source_name = name
        self._source_type = obj_type
        self._source_file = file
        self._source_line = line
        return self

    def with_target_info(
        self, name: str, obj_type: str, file: str, line: int
    ) -> "RelationshipBuilder":
        self._target_name = name
        self._target_type = obj_type
        self._target_file = file
        self._target_line = line
        return self

    def contains(self, parent_id, child_id) -> "RelationshipBuilder":
        self._source_id = parent_id
        self._target_id = child_id
        self._relation_type = RelationType.CONTAINS
        return self

    def references(self, source_id, target_id) -> "RelationshipBuilder":
        self._source_id = source_id
        self._target_id = target_id
        self._relation_type = RelationType.REFERENCES
        return self

    def calls(self, caller_id, callee_id) -> "RelationshipBuilder":
        self._source_id = caller_id
        self._target_id = callee_id
        self._relation_type = RelationType.CALLS
        return self

    def build(self) -> Relationship:
        return Relationship(
            source_id=str(self._source_id),
            source_name=self._source_name,
            source_type=self._source_type,
            source_file=self._source_file,
            source_line=self._source_line,
            target_id=str(self._target_id),
            target_name=self._target_name,
            target_type=self._target_type,
            target_file=self._target_file,
            target_line=self._target_line,
            relation_type=self._relation_type,
        )
