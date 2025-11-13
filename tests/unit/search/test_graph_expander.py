"""Unit tests for GraphExpander.

Phase 2: GraphRAG Integration
Tests PPR scoring, 1-hop traversal, and result expansion.

Type-safe implementation using Relationship objects.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
from codecontext.config.schema import CodeContextConfig, SearchConfig
from codecontext.search.graph_expander import GraphExpander
from codecontext_core.models import SearchResult, SearchScoring
from codecontext_core.models.core import Relationship, RelationType


class TestGraphExpander:
    """Test GraphExpander functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config with graph expansion enabled."""
        config = Mock(spec=CodeContextConfig)
        config.search = SearchConfig(
            enable_graph_expansion=True,
            graph_max_hops=1,
            graph_ppr_threshold=0.3,
            graph_score_weight=0.3,
        )
        return config

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage."""
        storage = MagicMock()
        return storage

    @pytest.fixture
    def expander(self, mock_config, mock_storage):
        """Create GraphExpander instance."""
        return GraphExpander(storage=mock_storage, config=mock_config)

    @pytest.fixture
    def sample_seed_result(self):
        """Create sample seed search result."""
        return SearchResult(
            chunk_id="seed123",
            file_path=Path("test/file.py"),
            content="def test_function():\n    pass",
            scoring=SearchScoring(final_score=0.9),
        )

    def test_ppr_scoring(self, expander, sample_seed_result):
        """Test Personalized PageRank scoring calculation."""
        # Test DOCUMENTS relationship (weight 1.0)
        ppr_score = expander._compute_ppr(
            source=sample_seed_result,
            target_id="target123",
            relationship_type=RelationType.DOCUMENTS,
            alpha=0.85,
        )
        assert abs(ppr_score - 0.135) < 0.001

        # Test CALLS relationship (weight 0.7)
        ppr_score = expander._compute_ppr(
            source=sample_seed_result,
            target_id="target456",
            relationship_type=RelationType.CALLS,
            alpha=0.85,
        )
        # ppr = 0.9 * 0.7 * 0.15 = 0.0945
        assert abs(ppr_score - 0.0945) < 0.001

        # Test CONTAINS relationship (weight 0.8)
        ppr_score = expander._compute_ppr(
            source=sample_seed_result,
            target_id="target789",
            relationship_type=RelationType.CONTAINS,
            alpha=0.85,
        )
        # ppr = 0.9 * 0.8 * 0.15 = 0.108
        assert abs(ppr_score - 0.108) < 0.001

    def test_traverse_relationships(self, expander, mock_storage, sample_seed_result):
        """Test 1-hop relationship traversal with Type-safe Relationship objects."""
        # Mock storage to return Relationship objects (Type-safe)
        mock_storage.get_relationships.return_value = [
            Relationship(
                source_id="seed123",
                source_type="function",
                target_id="doc1",
                target_type="document",
                relation_type=RelationType.DOCUMENTS,
                confidence=1.0,
            ),
            Relationship(
                source_id="seed123",
                source_type="function",
                target_id="func1",
                target_type="function",
                relation_type=RelationType.CALLS,
                confidence=0.9,
            ),
            Relationship(
                source_id="seed123",
                source_type="class",
                target_id="class1",
                target_type="function",
                relation_type=RelationType.CONTAINS,
                confidence=1.0,
            ),
            Relationship(
                source_id="seed123",
                source_type="function",
                target_id="ref1",
                target_type="variable",
                relation_type=RelationType.REFERENCES,
                confidence=0.8,
            ),
        ]

        neighbors = expander._traverse_relationships(sample_seed_result)

        # Should return all relationships with types
        assert len(neighbors) == 4
        assert ("doc1", RelationType.DOCUMENTS) in neighbors
        assert ("func1", RelationType.CALLS) in neighbors
        assert ("class1", RelationType.CONTAINS) in neighbors
        assert ("ref1", RelationType.REFERENCES) in neighbors

    def test_traverse_relationships_filtering(self, expander, mock_storage, sample_seed_result):
        """Test that only weighted relationship types are returned."""
        # Create a mock unknown type that's not in EDGE_WEIGHTS
        # We'll use DEPENDS_ON which exists but has low weight
        mock_storage.get_relationships.return_value = [
            Relationship(
                source_id="seed123",
                source_type="function",
                target_id="doc1",
                target_type="document",
                relation_type=RelationType.DOCUMENTS,
                confidence=1.0,
            ),
            Relationship(
                source_id="seed123",
                source_type="function",
                target_id="unknown1",
                target_type="module",
                relation_type=RelationType.DEPENDS_ON,  # This exists but not in EDGE_WEIGHTS
                confidence=0.8,
            ),
        ]

        neighbors = expander._traverse_relationships(sample_seed_result)

        # Should filter out DEPENDS_ON (not in EDGE_WEIGHTS)
        assert len(neighbors) == 1
        assert ("doc1", RelationType.DOCUMENTS) in neighbors

    def test_expand_results_disabled(self, mock_config, mock_storage):
        """Test that expansion is skipped when disabled."""
        mock_config.search.enable_graph_expansion = False
        expander = GraphExpander(storage=mock_storage, config=mock_config)

        initial_results = [
            SearchResult(
                chunk_id="id1",
                file_path=Path("test.py"),
                content="content",
                scoring=SearchScoring(final_score=0.9),
            )
        ]

        expanded = expander.expand_results(initial_results, top_k=5)

        # Should return original results unchanged
        assert len(expanded) == 1
        assert expanded[0].chunk_id == "id1"

    def test_expand_results_with_neighbors(self, expander, mock_storage):
        """Test result expansion with graph neighbors."""
        # Create seed result
        seed = SearchResult(
            chunk_id="seed1",
            file_path=Path("test.py"),
            content="seed content",
            scoring=SearchScoring(final_score=0.9),
        )

        # Mock relationships (Type-safe)
        mock_storage.get_relationships.return_value = [
            Relationship(
                source_id="seed1",
                source_type="function",
                target_id="neighbor1",
                target_type="document",
                relation_type=RelationType.DOCUMENTS,
                confidence=1.0,
            ),
            Relationship(
                source_id="seed1",
                source_type="function",
                target_id="neighbor2",
                target_type="function",
                relation_type=RelationType.CALLS,
                confidence=0.9,
            ),
        ]

        # Mock fetching neighbors
        neighbor1 = Mock()
        neighbor1.relative_path = "docs/readme.md"
        neighbor1.content = "neighbor1 content"
        neighbor1.file_path = "docs/readme.md"

        neighbor2 = Mock()
        neighbor2.relative_path = "test2.py"
        neighbor2.content = "neighbor2 content"
        neighbor2.nl_description = ""
        neighbor2.language = Mock(value="python")
        neighbor2.object_type = Mock(value="function")
        neighbor2.start_line = 0
        neighbor2.end_line = 0

        mock_storage.get_code_object.side_effect = lambda x: neighbor2 if x == "neighbor2" else None
        mock_storage.get_document.side_effect = lambda x: neighbor1 if x == "neighbor1" else None

        expanded = expander.expand_results([seed], top_k=1)

        # Should include seed + expanded neighbors (those above threshold)
        assert len(expanded) >= 1
        assert any(r.chunk_id == "seed1" for r in expanded)

        # Check that PPR scoring was applied
        # neighbor1: ppr = 0.9 * 1.0 * 0.15 = 0.135 (above threshold 0.3? No)
        # neighbor2: ppr = 0.9 * 0.7 * 0.15 = 0.0945 (above threshold 0.3? No)
        # Since both are below threshold (0.3), only seed should remain
        assert len(expanded) == 1

    def test_combine_results_scoring(self, expander):
        """Test that graph scores are properly weighted in combination."""
        # Create initial results
        initial = [
            SearchResult(
                chunk_id="initial1",
                file_path=Path("test.py"),
                content="initial content",
                scoring=SearchScoring(final_score=0.9),
            )
        ]

        # Create expanded entities with PPR scores
        expanded_entities = {
            "expanded1": (
                SearchResult(
                    chunk_id="expanded1",
                    file_path=Path("expanded.py"),
                    content="expanded content",
                    metadata={},
                ),
                0.5,  # PPR score
            )
        }

        combined = expander._combine_results(initial, expanded_entities)

        # Check that expanded result has weighted graph score
        # final_score = ppr_score * score_weight = 0.5 * 0.3 = 0.15
        expanded_result = next(r for r in combined if r.chunk_id == "expanded1")
        assert abs(expanded_result.score - 0.15) < 0.001
        assert expanded_result.metadata["_graph_expanded"] is True
        assert expanded_result.metadata["_ppr_score"] == 0.5

        # Check that initial result is preserved
        initial_result = next(r for r in combined if r.chunk_id == "initial1")
        assert initial_result.score == 0.9

        # Check sorting (initial should rank higher)
        assert combined[0].chunk_id == "initial1"
        assert combined[1].chunk_id == "expanded1"
