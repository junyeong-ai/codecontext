"""Search utility functions for safe type conversions and common operations.

This module provides utilities for safely converting between numpy types and Python
types, which is critical when working with BM25 libraries that return numpy arrays.

Best Practices:
- Always use safe_int_index() for array indices from BM25 results
- Always use safe_float_score() for scores from BM25 results
- Never assume numeric types from external libraries
"""

from typing import Any

import numpy as np


def safe_int_index(value: Any) -> int:
    """Safely convert numpy scalar or python number to int for indexing.

    BM25 libraries (like bm25s) return numpy arrays with float32 or int64 dtypes.
    Python list indexing requires native Python int type. This function provides
    safe conversion with clear error messages.

    Args:
        value: Numpy scalar (float32, int64, etc.) or Python number

    Returns:
        Integer suitable for list/array indexing

    Raises:
        ValueError: If value cannot be safely converted to int

    Examples:
        >>> safe_int_index(np.float32(3.0))
        3
        >>> safe_int_index(np.int64(5))
        5
        >>> safe_int_index(3)
        3
        >>> safe_int_index(3.0)
        3

    Notes:
        - Handles numpy scalars by calling .item() to extract Python value
        - Truncates float values (3.9 → 3)
        - Validates result is non-negative for indexing safety
    """
    try:
        # Handle numpy scalars (np.float32, np.int64, etc.)
        if isinstance(value, (np.integer, np.floating)):
            py_value = value.item()  # Extract Python scalar
        else:
            py_value = value

        # Convert to int
        result = int(py_value)

        # Validate for indexing (must be non-negative)
        if result < 0:
            raise ValueError(f"Index must be non-negative, got: {result}")

        return result

    except (ValueError, TypeError, AttributeError) as e:
        raise ValueError(
            f"Cannot convert {type(value).__name__} to int for indexing: {value!r}"
        ) from e


def safe_float_score(value: Any) -> float:
    """Safely convert numpy scalar or python number to float for scoring.

    BM25 and embedding similarity scores are often returned as numpy scalars.
    This function ensures consistent conversion to Python float for downstream
    processing and serialization.

    Args:
        value: Numpy scalar (float32, float64) or Python number

    Returns:
        Float suitable for scoring and serialization

    Raises:
        ValueError: If value cannot be safely converted to float

    Examples:
        >>> safe_float_score(np.float32(0.85))
        0.85
        >>> safe_float_score(np.float64(0.9123456789))
        0.9123456789
        >>> safe_float_score(0.75)
        0.75

    Notes:
        - Preserves precision from float64
        - Handles numpy scalars via .item()
        - No validation (negative scores are allowed for some algorithms)
    """
    try:
        # Handle numpy scalars
        if isinstance(value, (np.integer, np.floating)):
            return float(value.item())

        # Handle Python numbers
        return float(value)

    except (ValueError, TypeError, AttributeError) as e:
        raise ValueError(
            f"Cannot convert {type(value).__name__} to float for scoring: {value!r}"
        ) from e


def validate_bm25_results(
    indices: np.ndarray, scores: np.ndarray, max_index: int
) -> tuple[list[int], list[float]]:
    """Validate and convert BM25 search results to Python types.

    This is a convenience function that combines safe conversion and validation
    for typical BM25 result processing. It ensures indices are valid for the
    corpus size and converts both indices and scores to Python types.

    Args:
        indices: Numpy array of document indices from BM25 (shape: [1, k])
        scores: Numpy array of BM25 scores (shape: [1, k])
        max_index: Maximum valid index (usually len(corpus))

    Returns:
        Tuple of (valid_indices, valid_scores) as Python lists

    Raises:
        ValueError: If results have mismatched shapes or invalid indices

    Examples:
        >>> indices = np.array([[0, 2, 5]], dtype=np.float32)
        >>> scores = np.array([[0.9, 0.7, 0.5]], dtype=np.float32)
        >>> validate_bm25_results(indices, scores, max_index=10)
        ([0, 2, 5], [0.9, 0.7, 0.5])

    Notes:
        - Expects BM25 batch format (2D arrays with batch_size=1)
        - Filters out invalid indices (>= max_index)
        - Returns parallel lists for easy iteration
    """
    # Validate shapes
    if indices.shape != scores.shape:
        raise ValueError(
            f"BM25 results shape mismatch: indices {indices.shape} vs scores {scores.shape}"
        )

    if len(indices.shape) != 2 or indices.shape[0] != 1:
        raise ValueError(f"Expected BM25 batch format [1, k], got shape: {indices.shape}")

    # Extract first batch (BM25 typically returns [1, k] for single query)
    batch_indices = indices[0]
    batch_scores = scores[0]

    # Convert and validate
    valid_indices: list[int] = []
    valid_scores: list[float] = []

    for idx, score in zip(batch_indices, batch_scores):
        try:
            int_idx = safe_int_index(idx)

            # Skip if index is out of bounds
            if int_idx >= max_index:
                continue

            valid_indices.append(int_idx)
            valid_scores.append(safe_float_score(score))

        except ValueError:
            # Skip invalid values
            continue

    return valid_indices, valid_scores
