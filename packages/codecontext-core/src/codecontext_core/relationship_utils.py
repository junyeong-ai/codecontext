from __future__ import annotations

from typing import TYPE_CHECKING

from codecontext_core.models.core import RelationType

if TYPE_CHECKING:
    from codecontext_core.models import Relationship

REVERSE_MAP = {
    RelationType.CALLS: RelationType.CALLED_BY,
    RelationType.EXTENDS: RelationType.EXTENDED_BY,
    RelationType.IMPLEMENTS: RelationType.IMPLEMENTED_BY,
    RelationType.REFERENCES: RelationType.REFERENCED_BY,
    RelationType.CONTAINS: RelationType.CONTAINED_BY,
    RelationType.IMPORTS: RelationType.IMPORTED_BY,
}


def get_reverse_type(relation_type: RelationType) -> RelationType | None:
    return REVERSE_MAP.get(relation_type)


def create_reverse_relationship(rel: Relationship) -> Relationship | None:
    from codecontext_core.models import Relationship

    reverse_type = get_reverse_type(rel.relation_type)
    if not reverse_type:
        return None

    return Relationship(
        source_id=rel.target_id,
        source_type=rel.target_type,
        target_id=rel.source_id,
        target_type=rel.source_type,
        relation_type=reverse_type,
        confidence=rel.confidence,
    )
