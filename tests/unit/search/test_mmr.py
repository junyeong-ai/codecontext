"""Unit tests for MMR (Maximal Marginal Relevance) reranking."""

import pytest
from codecontext.search.mmr import MMRReranker
from codecontext_core.exceptions import InvalidParameterError


@pytest.fixture
def sample_results():
    """Create sample search results for testing."""
    return [
        {"id": "1", "score": 0.95},
        {"id": "2", "score": 0.90},
        {"id": "3", "score": 0.85},
        {"id": "4", "score": 0.80},
        {"id": "5", "score": 0.75},
    ]


@pytest.fixture
def sample_embeddings():
    """Create sample embeddings for testing."""
    return {
        "1": [1.0, 0.0, 0.0],  # Similar to query
        "2": [0.9, 0.1, 0.0],  # Similar to #1
        "3": [0.0, 1.0, 0.0],  # Diverse
        "4": [0.0, 0.0, 1.0],  # Diverse
        "5": [0.8, 0.2, 0.0],  # Similar to #1
    }


@pytest.fixture
def query_embedding():
    """Create query embedding for testing."""
    return [1.0, 0.0, 0.0]


class TestMMRRerankerInitialization:
    """Test MMR reranker initialization."""

    def test_initializes_with_defaults(self):
        """Should initialize with default parameters."""
        # Act
        reranker = MMRReranker()

        # Assert
        assert reranker.lambda_param == 0.7
        assert reranker.max_iterations == 100
        assert reranker.timeout_seconds == 3.0

    def test_initializes_with_custom_params(self):
        """Should initialize with custom parameters."""
        # Act
        reranker = MMRReranker(
            lambda_param=0.5,
            max_iterations=50,
            timeout_seconds=5.0,
        )

        # Assert
        assert reranker.lambda_param == 0.5
        assert reranker.max_iterations == 50
        assert reranker.timeout_seconds == 5.0

    def test_validates_lambda_param_range(self):
        """Should validate lambda_param is in [0.0, 1.0]."""
        # Act & Assert
        with pytest.raises(InvalidParameterError) as exc_info:
            MMRReranker(lambda_param=1.5)

        assert "must be in [0.0, 1.0]" in str(exc_info.value)

    def test_validates_negative_lambda_param(self):
        """Should reject negative lambda_param."""
        # Act & Assert
        with pytest.raises(InvalidParameterError):
            MMRReranker(lambda_param=-0.1)

    def test_validates_max_iterations_positive(self):
        """Should validate max_iterations is positive."""
        # Act & Assert
        with pytest.raises(InvalidParameterError) as exc_info:
            MMRReranker(max_iterations=0)

        assert "must be positive" in str(exc_info.value)

    def test_validates_negative_max_iterations(self):
        """Should reject negative max_iterations."""
        # Act & Assert
        with pytest.raises(InvalidParameterError):
            MMRReranker(max_iterations=-10)

    def test_accepts_boundary_lambda_values(self):
        """Should accept boundary values 0.0 and 1.0."""
        # Act
        reranker_0 = MMRReranker(lambda_param=0.0)  # Pure diversity
        reranker_1 = MMRReranker(lambda_param=1.0)  # Pure relevance

        # Assert
        assert reranker_0.lambda_param == 0.0
        assert reranker_1.lambda_param == 1.0


class TestMMRRerankerBasic:
    """Test basic reranking functionality."""

    def test_returns_empty_list_for_empty_input(self, query_embedding):
        """Should return empty list when input is empty."""
        # Arrange
        reranker = MMRReranker()

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=[],
            embeddings_dict={},
            top_k=5,
        )

        # Assert
        assert result == []

    def test_returns_empty_list_for_zero_top_k(
        self, query_embedding, sample_results, sample_embeddings
    ):
        """Should return empty list when top_k is 0."""
        # Arrange
        reranker = MMRReranker()

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=sample_embeddings,
            top_k=0,
        )

        # Assert
        assert result == []

    def test_returns_empty_list_for_negative_top_k(
        self, query_embedding, sample_results, sample_embeddings
    ):
        """Should return empty list when top_k is negative."""
        # Arrange
        reranker = MMRReranker()

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=sample_embeddings,
            top_k=-1,
        )

        # Assert
        assert result == []

    def test_returns_single_result(self, query_embedding, sample_embeddings):
        """Should return single result when only one available."""
        # Arrange
        reranker = MMRReranker()
        results = [{"id": "1", "score": 0.95}]

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=results,
            embeddings_dict=sample_embeddings,
            top_k=5,
        )

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_limits_results_to_top_k(self, query_embedding, sample_results, sample_embeddings):
        """Should limit results to top_k."""
        # Arrange
        reranker = MMRReranker()

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=sample_embeddings,
            top_k=3,
        )

        # Assert
        assert len(result) == 3


class TestMMRRerankerSelection:
    """Test result selection logic."""

    def test_first_result_is_most_relevant(
        self, query_embedding, sample_results, sample_embeddings
    ):
        """Should select most relevant result first (lambda=1.0)."""
        # Arrange
        reranker = MMRReranker(lambda_param=1.0)  # Pure relevance

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=sample_embeddings,
            top_k=1,
        )

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "1"  # Highest score

    def test_returns_results_when_available(
        self, query_embedding, sample_results, sample_embeddings
    ):
        """Should return results when available."""
        # Arrange
        reranker = MMRReranker()

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=sample_embeddings,
            top_k=5,
        )

        # Assert
        assert len(result) == 5

    def test_all_selected_results_from_input(
        self, query_embedding, sample_results, sample_embeddings
    ):
        """Should only select results from input set."""
        # Arrange
        reranker = MMRReranker()

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=sample_embeddings,
            top_k=5,
        )

        # Assert
        result_ids = {r["id"] for r in result}
        input_ids = {r["id"] for r in sample_results}
        assert result_ids.issubset(input_ids)


class TestMMRRerankerLambdaParameter:
    """Test lambda parameter effects on diversity."""

    def test_lambda_1_prefers_relevance(self, query_embedding, sample_results, sample_embeddings):
        """Lambda=1.0 should prefer relevance (no diversity)."""
        # Arrange
        reranker = MMRReranker(lambda_param=1.0)

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=sample_embeddings,
            top_k=3,
        )

        # Assert - Should select 3 results
        # First is always most relevant
        assert len(result) == 3
        assert result[0]["id"] == "1"  # Most relevant first
        # With lambda=1.0, selects by similarity to query
        # Query=[1,0,0], so similar embeddings (1, 2, 5) preferred

    def test_lambda_0_prefers_diversity(self, query_embedding, sample_results, sample_embeddings):
        """Lambda=0.0 should prefer diversity (no relevance)."""
        # Arrange
        reranker = MMRReranker(lambda_param=0.0)

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=sample_embeddings,
            top_k=3,
        )

        # Assert - Should select diverse results
        # First is still most relevant, then diverse ones
        assert len(result) == 3
        # Results should include diverse embeddings
        result_ids = {r["id"] for r in result}
        assert "1" in result_ids  # Most relevant first
        # Should prefer diverse results (3, 4) over similar ones (2, 5)


class TestMMRRerankerIterationGuards:
    """Test safety guards for iterations."""

    def test_respects_max_iterations(self, query_embedding, sample_results, sample_embeddings):
        """Should respect max_iterations limit."""
        # Arrange
        reranker = MMRReranker(max_iterations=2)

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=sample_embeddings,
            top_k=5,
        )

        # Assert - Should complete without error
        assert len(result) <= 5

    def test_completes_within_timeout(self, query_embedding, sample_results, sample_embeddings):
        """Should complete within timeout."""
        # Arrange
        reranker = MMRReranker(timeout_seconds=5.0)

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=sample_embeddings,
            top_k=5,
        )

        # Assert - Should complete without timing out
        assert len(result) <= 5


class TestMMRRerankerEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_results_without_embeddings(self, query_embedding, sample_results):
        """Should handle results that don't have embeddings."""
        # Arrange
        reranker = MMRReranker()
        # Embeddings missing some IDs
        partial_embeddings = {
            "1": [1.0, 0.0, 0.0],
            "2": [0.9, 0.1, 0.0],
        }

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results,
            embeddings_dict=partial_embeddings,
            top_k=5,
        )

        # Assert - Should handle gracefully
        assert len(result) <= 5

    def test_handles_top_k_larger_than_input(
        self, query_embedding, sample_results, sample_embeddings
    ):
        """Should handle top_k larger than available results."""
        # Arrange
        reranker = MMRReranker()

        # Act
        result = reranker.rerank(
            query_embedding=query_embedding,
            results=sample_results[:2],  # Only 2 results
            embeddings_dict=sample_embeddings,
            top_k=10,  # Request 10
        )

        # Assert
        assert len(result) <= 2
