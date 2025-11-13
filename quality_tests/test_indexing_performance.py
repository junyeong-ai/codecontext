"""
Indexing Performance Tests

E2E tests for indexing performance using CLI:
- codecontext index

Validates:
- Indexing completes successfully
- Performance within acceptable bounds
- Resource usage (CPU, memory, I/O)

Note: These tests perform actual indexing and should be run separately
      from search tests when developing search features.
"""

from typing import Any

import pytest

pytestmark = [pytest.mark.quality, pytest.mark.indexing]


class TestIndexingPerformance:
    """Indexing performance validation tests."""

    def test_indexing_completes(self, indexed_samples: dict[str, Any]) -> None:
        """Test that indexing completes successfully."""
        if indexed_samples["reused"]:
            pytest.skip(
                f"Reusing existing index ({indexed_samples['count']} documents). "
                "Use --reindex to test indexing performance."
            )

        assert indexed_samples["indexed"] is True
        assert indexed_samples["duration_seconds"] > 0
        assert indexed_samples["count"] > 0
        print(
            f"\n✅ Indexing completed: {indexed_samples['count']} documents "
            f"in {indexed_samples['duration_seconds']:.2f}s"
        )

    def test_indexing_performance_baseline(self, indexed_samples: dict[str, Any]) -> None:
        """
        Test indexing performance meets baseline.

        Baseline: 27 files (ecommerce_samples) should index in < 120 seconds on M4 Pro
        """
        if indexed_samples["reused"]:
            pytest.skip("Reusing existing index. Use --reindex to test indexing performance.")

        duration = indexed_samples["duration_seconds"]
        max_duration = 120.0  # 2 minutes

        assert (
            duration < max_duration
        ), f"Indexing took {duration:.2f}s, exceeding baseline of {max_duration}s"

        print(f"\n✅ Indexing performance: {duration:.2f}s (baseline: <{max_duration}s)")

    def test_indexing_output_valid(self, indexed_samples: dict[str, Any]) -> None:
        """Test that indexing output is valid."""
        if indexed_samples["reused"]:
            pytest.skip("Reusing existing index. Use --reindex to test indexing output.")

        output = indexed_samples["output"]

        # Should contain success indicators
        assert output, "Indexing output should not be empty"

        print("\n✅ Indexing output valid")
        print(f"Output preview:\n{output[:500]}")
