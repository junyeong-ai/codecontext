"""Assertion helpers for test validation.

This module provides reusable assertion functions that make test validation
more concise and expressive.
"""

from codecontext_core.models import CodeObject, ObjectType, Relationship, RelationType


def assert_relationship(
    rel: Relationship,
    *,
    source_id=None,
    target_id=None,
    relation_type: RelationType | None = None,
    confidence: float | None = None,
    source_type: str | None = None,
    target_type: str | None = None,
) -> None:
    """Assert relationship properties with optional matchers.

    Args:
        rel: Relationship to validate
        source_id: Expected source ID (optional)
        target_id: Expected target ID (optional)
        relation_type: Expected relationship type (optional)
        confidence: Expected confidence score (optional)
        source_type: Expected source type (optional)
        target_type: Expected target type (optional)

    Raises:
        AssertionError: If any specified expectation doesn't match

    Example:
        >>> assert_relationship(rel, source_id=user_id, relation_type=RelationType.CONTAINS)
    """
    if source_id is not None:
        assert rel.source_id == source_id, f"Expected source_id {source_id}, got {rel.source_id}"

    if target_id is not None:
        assert rel.target_id == target_id, f"Expected target_id {target_id}, got {rel.target_id}"

    if relation_type is not None:
        assert rel.relation_type == relation_type, (
            f"Expected relation_type {relation_type}, got {rel.relation_type}"
        )

    if confidence is not None:
        assert rel.confidence == confidence, (
            f"Expected confidence {confidence}, got {rel.confidence}"
        )

    if source_type is not None:
        assert rel.source_type == source_type, (
            f"Expected source_type {source_type}, got {rel.source_type}"
        )

    if target_type is not None:
        assert rel.target_type == target_type, (
            f"Expected target_type {target_type}, got {rel.target_type}"
        )


def assert_contains_relationship(
    rel: Relationship,
    parent_id,
    child_id,
) -> None:
    """Assert a CONTAINS relationship with standard properties.

    Args:
        rel: Relationship to validate
        parent_id: Expected parent (source) ID
        child_id: Expected child (target) ID

    Raises:
        AssertionError: If relationship doesn't match expectations

    Example:
        >>> assert_contains_relationship(rel, class_id, method_id)
    """
    assert_relationship(
        rel,
        source_id=parent_id,
        target_id=child_id,
        relation_type=RelationType.CONTAINS,
        confidence=1.0,
    )


def assert_references_relationship(
    rel: Relationship,
    source_id,
    target_id,
    confidence: float = 0.8,
) -> None:
    """Assert a REFERENCES relationship (inheritance).

    Args:
        rel: Relationship to validate
        source_id: Expected source (child) ID
        target_id: Expected target (base) ID
        confidence: Expected confidence (default: 0.8)

    Raises:
        AssertionError: If relationship doesn't match expectations

    Example:
        >>> assert_references_relationship(rel, child_id, base_id)
    """
    assert_relationship(
        rel,
        source_id=source_id,
        target_id=target_id,
        relation_type=RelationType.REFERENCES,
        confidence=confidence,
    )


def assert_calls_relationship(
    rel: Relationship,
    caller_id,
    callee_id,
    confidence: float | None = None,
) -> None:
    """Assert a CALLS relationship.

    Args:
        rel: Relationship to validate
        caller_id: Expected caller (source) ID
        callee_id: Expected callee (target) ID
        confidence: Expected confidence (optional, varies by implementation)

    Raises:
        AssertionError: If relationship doesn't match expectations

    Example:
        >>> assert_calls_relationship(rel, func1_id, func2_id)
    """
    assert_relationship(
        rel,
        source_id=caller_id,
        target_id=callee_id,
        relation_type=RelationType.CALLS,
        confidence=confidence,
    )


def assert_code_object(
    obj: CodeObject,
    *,
    name: str | None = None,
    object_type: ObjectType | None = None,
    parent_id=None,
    language=None,
    file_path: str | None = None,
) -> None:
    """Assert CodeObject properties with optional matchers.

    Args:
        obj: CodeObject to validate
        name: Expected name (optional)
        object_type: Expected object type (optional)
        parent_id: Expected parent ID (optional)
        language: Expected language (optional)
        file_path: Expected file path (optional)

    Raises:
        AssertionError: If any specified expectation doesn't match

    Example:
        >>> assert_code_object(obj, name="User", object_type=ObjectType.CLASS)
    """
    if name is not None:
        assert obj.name == name, f"Expected name {name}, got {obj.name}"

    if object_type is not None:
        assert obj.object_type == object_type, (
            f"Expected object_type {object_type}, got {obj.object_type}"
        )

    if parent_id is not None:
        assert obj.parent_id == parent_id, f"Expected parent_id {parent_id}, got {obj.parent_id}"

    if language is not None:
        assert obj.language == language, f"Expected language {language}, got {obj.language}"

    if file_path is not None:
        assert obj.file_path == file_path, f"Expected file_path {file_path}, got {obj.file_path}"


def assert_relationship_count(
    relationships: list[Relationship],
    expected_count: int,
    relation_type: RelationType | None = None,
) -> None:
    """Assert the count of relationships, optionally filtered by type.

    Args:
        relationships: List of relationships to check
        expected_count: Expected number of relationships
        relation_type: Optional filter by relationship type

    Raises:
        AssertionError: If count doesn't match

    Example:
        >>> assert_relationship_count(rels, 3, RelationType.CONTAINS)
    """
    if relation_type is not None:
        filtered = [r for r in relationships if r.relation_type == relation_type]
        actual_count = len(filtered)
        assert actual_count == expected_count, (
            f"Expected {expected_count} {relation_type} relationships, got {actual_count}"
        )
    else:
        actual_count = len(relationships)
        assert actual_count == expected_count, (
            f"Expected {expected_count} relationships, got {actual_count}"
        )


def assert_relationship_exists(
    relationships: list[Relationship],
    source_id,
    target_id,
    relation_type: RelationType,
) -> Relationship:
    """Assert that a specific relationship exists in the list.

    Args:
        relationships: List of relationships to search
        source_id: Expected source ID
        target_id: Expected target ID
        relation_type: Expected relationship type

    Returns:
        The matching relationship

    Raises:
        AssertionError: If no matching relationship found

    Example:
        >>> rel = assert_relationship_exists(rels, parent_id, child_id, RelationType.CONTAINS)
    """
    matches = [
        r
        for r in relationships
        if r.source_id == source_id
        and r.target_id == target_id
        and r.relation_type == relation_type
    ]

    assert len(matches) > 0, (
        f"No {relation_type} relationship found from {source_id} to {target_id}"
    )

    return matches[0]


def assert_all_have_confidence(
    relationships: list[Relationship],
    expected_confidence: float,
) -> None:
    """Assert that all relationships have the expected confidence.

    Args:
        relationships: List of relationships to check
        expected_confidence: Expected confidence value

    Raises:
        AssertionError: If any relationship has different confidence

    Example:
        >>> assert_all_have_confidence(contains_rels, 1.0)
    """
    for rel in relationships:
        assert rel.confidence == expected_confidence, (
            f"Expected confidence {expected_confidence}, "
            f"got {rel.confidence} for relationship {rel.source_id} -> {rel.target_id}"
        )
