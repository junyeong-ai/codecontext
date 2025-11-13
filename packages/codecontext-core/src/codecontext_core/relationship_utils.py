"""
Utilities for relationship type conversion and validation.

Provides helper functions for bidirectional relationship handling.
"""

from codecontext_core.models.core import RelationType


# Bidirectional relationship mappings
FORWARD_TO_REVERSE: dict[RelationType, RelationType] = {
    # Code-to-Code
    RelationType.CALLS: RelationType.CALLED_BY,
    RelationType.REFERENCES: RelationType.REFERENCED_BY,
    RelationType.EXTENDS: RelationType.EXTENDED_BY,
    RelationType.IMPLEMENTS: RelationType.IMPLEMENTED_BY,
    RelationType.CONTAINS: RelationType.CONTAINED_BY,
    RelationType.IMPORTS: RelationType.IMPORTED_BY,
    RelationType.DEPENDS_ON: RelationType.DEPENDED_BY,
    RelationType.ANNOTATES: RelationType.ANNOTATED_BY,
    # Document-to-Code
    RelationType.DOCUMENTS: RelationType.DOCUMENTED_BY,
    RelationType.MENTIONS: RelationType.MENTIONED_IN,
    RelationType.IMPLEMENTS_SPEC: RelationType.IMPLEMENTED_IN,
}

REVERSE_TO_FORWARD: dict[RelationType, RelationType] = {v: k for k, v in FORWARD_TO_REVERSE.items()}


def get_reverse_type(relation_type: RelationType) -> RelationType:
    """
    Get the reverse relationship type.

    Args:
        relation_type: Forward relationship type

    Returns:
        Reverse relationship type

    Examples:
        >>> get_reverse_type(RelationType.CALLS)
        RelationType.CALLED_BY
        >>> get_reverse_type(RelationType.DOCUMENTED_BY)
        RelationType.DOCUMENTS
    """
    if relation_type in FORWARD_TO_REVERSE:
        return FORWARD_TO_REVERSE[relation_type]
    elif relation_type in REVERSE_TO_FORWARD:
        return REVERSE_TO_FORWARD[relation_type]
    else:
        # For non-directional types (e.g., SIMILAR_TO), return same
        return relation_type


def get_forward_type(relation_type: RelationType) -> RelationType:
    """
    Get the forward relationship type.

    If already forward, returns the same. If reverse, converts to forward.

    Args:
        relation_type: Any relationship type

    Returns:
        Forward relationship type
    """
    if relation_type in REVERSE_TO_FORWARD:
        return REVERSE_TO_FORWARD[relation_type]
    return relation_type


def is_forward_type(relation_type: RelationType) -> bool:
    """Check if relationship type is forward direction."""
    return relation_type in FORWARD_TO_REVERSE


def is_reverse_type(relation_type: RelationType) -> bool:
    """Check if relationship type is reverse direction."""
    return relation_type in REVERSE_TO_FORWARD


def is_bidirectional_type(relation_type: RelationType) -> bool:
    """Check if relationship type has bidirectional support."""
    return relation_type in FORWARD_TO_REVERSE or relation_type in REVERSE_TO_FORWARD


def is_document_code_type(relation_type: RelationType) -> bool:
    """Check if relationship type is document-code link."""
    return relation_type in {
        RelationType.DOCUMENTS,
        RelationType.DOCUMENTED_BY,
        RelationType.MENTIONS,
        RelationType.MENTIONED_IN,
        RelationType.IMPLEMENTS_SPEC,
        RelationType.IMPLEMENTED_IN,
    }


def is_code_code_type(relation_type: RelationType) -> bool:
    """Check if relationship type is code-to-code."""
    return not is_document_code_type(relation_type) and is_bidirectional_type(relation_type)
