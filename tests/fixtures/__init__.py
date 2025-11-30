"""Test fixtures and utilities for reducing test boilerplate.

This package provides builder patterns, factory methods, assertion helpers,
and extractor utilities for creating clean, readable tests.

Quick Start:
    >>> from tests.fixtures import create_class, create_method, create_containment_scenario
    >>> from tests.fixtures import assert_contains_relationship, extract_relationships

    >>> # Create test objects
    >>> parent, method = create_containment_scenario()

    >>> # Extract relationships
    >>> builder = ContainmentBuilder()
    >>> rels = builder.extract([parent, method])

    >>> # Assert results
    >>> assert len(rels) == 1
    >>> assert_contains_relationship(rels[0], parent.id, method.id)
"""

# Builders
# Assertion helpers
from tests.fixtures.assertions import (
    assert_calls_relationship,
    assert_code_object,
    assert_contains_relationship,
    assert_references_relationship,
    assert_relationship,
    assert_relationship_count,
    assert_relationship_exists,
)
from tests.fixtures.builders import CodeObjectBuilder, RelationshipBuilder

# Extractor helpers
from tests.fixtures.extractor_helpers import (
    extract_relationships,
    filter_by_source,
    filter_by_target,
    filter_by_type,
    get_source_ids,
    get_target_ids,
)

# Factory methods
from tests.fixtures.factories import (
    create_call_graph_scenario,
    create_calls_relationship,
    # Individual object factories
    create_class,
    # Direct CodeObject factory
    create_code_object,
    create_containment_scenario,
    # Relationship factories
    create_contains_relationship,
    create_function,
    # Scenario factories
    create_inheritance_scenario,
    create_interface,
    create_method,
    create_multi_level_hierarchy,
    create_multiple_inheritance_scenario,
    create_references_relationship,
)

# NOTE: Fixture modules (parsers, storage, documents) are registered via
# pytest_plugins in conftest.py for auto-discovery. DO NOT import from them
# here to avoid "Module already imported" warnings.
#
# Tests can import fixtures directly if needed:
#   from tests.fixtures.parsers import create_test_parser_for_language
#   from tests.fixtures.storage import create_mock_search_result
#   from tests.fixtures.documents import create_document_node
#
# Pytest fixtures are auto-discovered and don't need explicit imports.

__all__ = [
    # Builders
    "CodeObjectBuilder",
    "RelationshipBuilder",
    # Direct factory
    "create_code_object",
    # Object factories
    "create_class",
    "create_interface",
    "create_method",
    "create_function",
    # Scenario factories
    "create_inheritance_scenario",
    "create_containment_scenario",
    "create_multi_level_hierarchy",
    "create_multiple_inheritance_scenario",
    "create_call_graph_scenario",
    # Relationship factories
    "create_contains_relationship",
    "create_references_relationship",
    "create_calls_relationship",
    # Assertions
    "assert_relationship",
    "assert_contains_relationship",
    "assert_references_relationship",
    "assert_calls_relationship",
    "assert_code_object",
    "assert_relationship_count",
    "assert_relationship_exists",
    # Extractor helpers
    "extract_relationships",
    "filter_by_source",
    "filter_by_target",
    "filter_by_type",
    "get_target_ids",
    "get_source_ids",
    # NOTE: Fixture helpers are imported directly from their modules when needed
    # See comment above for import instructions
]
