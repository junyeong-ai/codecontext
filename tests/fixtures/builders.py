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
    """Fluent builder for creating test Relationship instances.

    Provides a clean API for creating relationships with sensible defaults:
    - Automatic ID generation for source/target
    - Type-specific confidence defaults
    - Common relationship type shortcuts

    Example:
        >>> builder = RelationshipBuilder()
        >>> rel = builder.contains(parent_id, child_id).build()
        >>> rel = builder.references(source_id, target_id).build()
    """

    def __init__(self) -> None:
        """Initialize builder with default values."""
        self._source_id = uuid4()
        self._source_type = "code_object"
        self._target_id = uuid4()
        self._target_type = "code_object"
        self._relation_type = RelationType.CONTAINS
        self._confidence = 1.0

    def from_source(self, source_id) -> "RelationshipBuilder":
        """Set the source object ID."""
        self._source_id = source_id
        return self

    def to_target(self, target_id) -> "RelationshipBuilder":
        """Set the target object ID."""
        self._target_id = target_id
        return self

    def with_type(self, relation_type: RelationType) -> "RelationshipBuilder":
        """Set the relationship type."""
        self._relation_type = relation_type
        return self

    def with_confidence(self, confidence: float) -> "RelationshipBuilder":
        """Set the confidence score."""
        self._confidence = confidence
        return self

    def contains(self, parent_id, child_id) -> "RelationshipBuilder":
        """Configure as a CONTAINS relationship (parent -> child)."""
        self._source_id = parent_id
        self._target_id = child_id
        self._relation_type = RelationType.CONTAINS
        self._confidence = 1.0
        return self

    def references(self, source_id, target_id, confidence: float = 0.8) -> "RelationshipBuilder":
        """Configure as a REFERENCES relationship (inheritance)."""
        self._source_id = source_id
        self._target_id = target_id
        self._relation_type = RelationType.REFERENCES
        self._confidence = confidence
        return self

    def calls(self, caller_id, callee_id, confidence: float = 0.6) -> "RelationshipBuilder":
        """Configure as a CALLS relationship (function call)."""
        self._source_id = caller_id
        self._target_id = callee_id
        self._relation_type = RelationType.CALLS
        self._confidence = confidence
        return self

    def build(self) -> Relationship:
        """Build the Relationship instance.

        Returns:
            Fully configured Relationship with all fields set
        """
        return Relationship(
            source_id=str(self._source_id),
            source_type=self._source_type,
            target_id=str(self._target_id),
            target_type=self._target_type,
            relation_type=self._relation_type,
            confidence=self._confidence,
        )
