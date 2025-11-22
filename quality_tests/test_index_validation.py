from typing import Any

import pytest

pytestmark = [pytest.mark.quality]


class TestIndexValidation:
    def test_index_exists(self, indexed_samples: dict[str, Any]) -> None:
        count = indexed_samples["count"]
        assert count > 0
        print(f"\n✅ Index contains {count:,} objects")

    def test_index_size(self, indexed_samples: dict[str, Any]) -> None:
        count = indexed_samples["count"]
        min_expected = 100
        max_expected = 1000

        assert min_expected <= count <= max_expected, (
            f"Index size {count:,} outside expected range [{min_expected:,}, {max_expected:,}]"
        )
        print(f"\n✅ Index size: {count:,} objects")

    def test_index_minimum(self, indexed_samples: dict[str, Any]) -> None:
        count = indexed_samples["count"]
        min_objects = 50

        assert count >= min_objects, f"Index has only {count:,} objects, expected ≥{min_objects:,}"
        print(f"\n✅ Index has {count:,} objects (minimum: {min_objects:,})")
