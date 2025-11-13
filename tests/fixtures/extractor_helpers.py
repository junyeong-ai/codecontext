"""Helper utilities for testing relationship extractors.

This module provides common patterns for extractor testing, reducing
boilerplate in extractor test files.
"""

from codecontext_core.models import CodeObject, Relationship


def extract_relationships(extractor, objects: list[CodeObject]) -> list[Relationship]:
    """Run extractor on objects and return all relationships.

    This is the standard pattern for testing language-specific extractors
    that implement the extract_from_object() interface.

    Args:
        extractor: Extractor instance (InheritanceExtractor, CallGraphExtractor, etc.)
        objects: List of CodeObject instances to process

    Returns:
        List of extracted relationships

    Example:
        >>> from codecontext.indexer.relationships.inheritance import PythonInheritanceExtractor
        >>> extractor = PythonInheritanceExtractor()
        >>> relationships = extract_relationships(extractor, [base, child])
    """
    relationships = []
    for obj in objects:
        if extractor.can_extract(obj):
            obj_relationships = extractor.extract_from_object(obj, objects)
            relationships.extend(obj_relationships)
    return relationships


def filter_by_source(relationships: list[Relationship], source_id) -> list[Relationship]:
    """Filter relationships by source ID.

    Args:
        relationships: List of relationships to filter
        source_id: Source ID to match

    Returns:
        Filtered list of relationships

    Example:
        >>> child_relationships = filter_by_source(all_rels, child_id)
    """
    return [r for r in relationships if r.source_id == source_id]


def filter_by_target(relationships: list[Relationship], target_id) -> list[Relationship]:
    """Filter relationships by target ID.

    Args:
        relationships: List of relationships to filter
        target_id: Target ID to match

    Returns:
        Filtered list of relationships

    Example:
        >>> refs_to_base = filter_by_target(all_rels, base_id)
    """
    return [r for r in relationships if r.target_id == target_id]


def filter_by_type(relationships: list[Relationship], relation_type) -> list[Relationship]:
    """Filter relationships by type.

    Args:
        relationships: List of relationships to filter
        relation_type: RelationType to match

    Returns:
        Filtered list of relationships

    Example:
        >>> contains_rels = filter_by_type(all_rels, RelationType.CONTAINS)
    """
    return [r for r in relationships if r.relation_type == relation_type]


def get_target_ids(relationships: list[Relationship]) -> set:
    """Extract all unique target IDs from relationships.

    Args:
        relationships: List of relationships

    Returns:
        Set of target IDs

    Example:
        >>> target_ids = get_target_ids(relationships)
        >>> assert target_ids == {method1_id, method2_id, method3_id}
    """
    return {r.target_id for r in relationships}


def get_source_ids(relationships: list[Relationship]) -> set:
    """Extract all unique source IDs from relationships.

    Args:
        relationships: List of relationships

    Returns:
        Set of source IDs

    Example:
        >>> source_ids = get_source_ids(relationships)
        >>> assert child_id in source_ids
    """
    return {r.source_id for r in relationships}
