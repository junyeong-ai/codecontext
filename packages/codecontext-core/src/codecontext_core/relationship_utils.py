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
        source_name=rel.target_name,
        source_type=rel.target_type,
        source_file=rel.target_file,
        source_line=rel.target_line,
        target_id=rel.source_id,
        target_name=rel.source_name,
        target_type=rel.source_type,
        target_file=rel.source_file,
        target_line=rel.source_line,
        relation_type=reverse_type,
    )
