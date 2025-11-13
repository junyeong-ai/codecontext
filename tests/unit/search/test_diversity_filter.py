"""Unit tests for file diversity filter."""

from pathlib import Path

import pytest
from codecontext.search.diversity_filter import DiversityConfig, FileDiversityFilter
from codecontext_core.models import SearchResult, SearchScoring


def make_result(chunk_id: str, file_path: str, score: float = 1.0) -> SearchResult:
    """Helper to create SearchResult for testing."""
    return SearchResult(
        chunk_id=chunk_id,
        file_path=Path(file_path),
        content="test content",
        scoring=SearchScoring(final_score=score),
        start_line=1,
        end_line=1,
    )


class TestDiversityConfig:
    """Test DiversityConfig validation."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        config = DiversityConfig()
        assert config.max_chunks_per_file == 2
        assert config.preserve_top_n == 1

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        config = DiversityConfig(max_chunks_per_file=3, preserve_top_n=2)
        assert config.max_chunks_per_file == 3
        assert config.preserve_top_n == 2

    def test_frozen_dataclass(self) -> None:
        """Should be immutable (frozen)."""
        config = DiversityConfig()
        with pytest.raises(Exception):  # FrozenInstanceError
            config.max_chunks_per_file = 5  # type: ignore[misc]

    def test_validates_max_chunks_per_file(self) -> None:
        """Should validate max_chunks_per_file >= 1."""
        with pytest.raises(ValueError, match="max_chunks_per_file must be >= 1"):
            DiversityConfig(max_chunks_per_file=0)

    def test_validates_preserve_top_n(self) -> None:
        """Should validate preserve_top_n >= 0."""
        with pytest.raises(ValueError, match="preserve_top_n must be >= 0"):
            DiversityConfig(preserve_top_n=-1)


class TestFileDiversityFilterInplace:
    """Test in-place filtering."""

    def test_empty_list(self) -> None:
        """Should handle empty list."""
        config = DiversityConfig()
        filter_obj = FileDiversityFilter(config)
        results: list[SearchResult] = []

        filter_obj.apply_inplace(results)

        assert results == []

    def test_single_result(self) -> None:
        """Should preserve single result."""
        config = DiversityConfig()
        filter_obj = FileDiversityFilter(config)
        results = [make_result("1", "a.py")]

        filter_obj.apply_inplace(results)

        assert len(results) == 1

    def test_different_files_all_preserved(self) -> None:
        """Should preserve results from different files."""
        config = DiversityConfig(max_chunks_per_file=2)
        filter_obj = FileDiversityFilter(config)
        results = [
            make_result("1", "a.py", 1.0),
            make_result("2", "b.py", 0.9),
            make_result("3", "c.py", 0.8),
        ]

        filter_obj.apply_inplace(results)

        assert len(results) == 3
        assert str(results[0].file_path) == "a.py"
        assert str(results[1].file_path) == "b.py"
        assert str(results[2].file_path) == "c.py"

    def test_limits_chunks_per_file(self) -> None:
        """Should limit chunks per file to max_chunks_per_file."""
        config = DiversityConfig(max_chunks_per_file=2, preserve_top_n=0)
        filter_obj = FileDiversityFilter(config)
        results = [
            make_result("1", "a.py", 1.0),
            make_result("2", "a.py", 0.9),
            make_result("3", "a.py", 0.8),
            make_result("4", "b.py", 0.7),
        ]

        filter_obj.apply_inplace(results)

        # Should keep first 2 from a.py + 1 from b.py
        assert len(results) == 3
        assert results[0].chunk_id == "1"
        assert results[1].chunk_id == "2"
        assert results[2].chunk_id == "4"

    def test_preserves_top_n(self) -> None:
        """Should always preserve top N results."""
        config = DiversityConfig(max_chunks_per_file=1, preserve_top_n=2)
        filter_obj = FileDiversityFilter(config)
        results = [
            make_result("1", "a.py", 1.0),
            make_result("2", "a.py", 0.9),
            make_result("3", "a.py", 0.8),
        ]

        filter_obj.apply_inplace(results)

        # Top 2 preserved despite max_chunks_per_file=1
        assert len(results) == 2
        assert results[0].chunk_id == "1"
        assert results[1].chunk_id == "2"

    def test_real_world_scenario(self) -> None:
        """Should handle real-world scenario (payment-gateway.md duplication)."""
        config = DiversityConfig(max_chunks_per_file=2, preserve_top_n=1)
        filter_obj = FileDiversityFilter(config)

        # Simulate Q002 results: 6 chunks from payment-gateway.md
        results = [
            make_result(f"payment-{i}", "payment-gateway.md", 1.0 - i * 0.1) for i in range(6)
        ] + [make_result("code-1", "PaymentGatewayProvider.py", 0.5)]

        filter_obj.apply_inplace(results)

        # Should keep: top 1 (preserved) + 1 more from payment-gateway.md + code file
        assert len(results) == 3
        assert results[0].chunk_id == "payment-0"  # Top 1 preserved
        assert results[1].chunk_id == "payment-1"  # Within limit
        assert results[2].chunk_id == "code-1"  # Different file


class TestFileDiversityFilterCopy:
    """Test non-destructive apply()."""

    def test_returns_new_list(self) -> None:
        """Should return new list without modifying original."""
        config = DiversityConfig(max_chunks_per_file=1)
        filter_obj = FileDiversityFilter(config)
        original = [
            make_result("1", "a.py", 1.0),
            make_result("2", "a.py", 0.9),
        ]

        filtered = filter_obj.apply(original)

        # Original unchanged
        assert len(original) == 2
        # Filtered has diversity applied
        assert len(filtered) == 1
        assert filtered[0].chunk_id == "1"


class TestFileDiversityFilterEdgeCases:
    """Test edge cases."""

    def test_max_chunks_1(self) -> None:
        """Should work with max_chunks_per_file=1."""
        config = DiversityConfig(max_chunks_per_file=1, preserve_top_n=0)
        filter_obj = FileDiversityFilter(config)
        results = [make_result(f"{i}", f"file{i % 2}.py", 1.0 - i * 0.1) for i in range(6)]

        filter_obj.apply_inplace(results)

        # 6 results alternating between 2 files, max 1 per file = 2 results
        assert len(results) == 2

    def test_preserve_top_n_zero(self) -> None:
        """Should work with preserve_top_n=0."""
        config = DiversityConfig(max_chunks_per_file=2, preserve_top_n=0)
        filter_obj = FileDiversityFilter(config)
        results = [make_result(f"{i}", "a.py", 1.0) for i in range(5)]

        filter_obj.apply_inplace(results)

        # No top preservation, strict limit=2
        assert len(results) == 2

    def test_large_preserve_top_n(self) -> None:
        """Should handle preserve_top_n larger than list."""
        config = DiversityConfig(max_chunks_per_file=1, preserve_top_n=100)
        filter_obj = FileDiversityFilter(config)
        results = [make_result(f"{i}", "a.py", 1.0) for i in range(5)]

        filter_obj.apply_inplace(results)

        # All preserved (preserve_top_n > len)
        assert len(results) == 5
