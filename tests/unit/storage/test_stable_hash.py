"""Tests for deterministic hash function in sparse vector encoding."""

import subprocess
import sys

from codecontext_core.bm25 import _stable_hash


def test_stable_hash_deterministic():
    """Hash must be deterministic within same process."""
    token = "OrderService"
    hash1 = _stable_hash(token)
    hash2 = _stable_hash(token)
    assert hash1 == hash2


def test_stable_hash_across_processes():
    """Hash must be deterministic across different processes."""
    test_code = """
from codecontext_core.bm25 import _stable_hash
print(_stable_hash("OrderService"))
"""

    results = []
    for _ in range(3):
        result = subprocess.run(
            [sys.executable, "-c", test_code],
            capture_output=True,
            text=True,
            check=True,
        )
        results.append(result.stdout.strip())

    assert len(set(results)) == 1, f"Hash not deterministic across processes: {set(results)}"


def test_stable_hash_different_tokens():
    """Different tokens must produce different hashes."""
    hash1 = _stable_hash("order")
    hash2 = _stable_hash("process")
    hash3 = _stable_hash("OrderService")

    assert hash1 != hash2
    assert hash1 != hash3
    assert hash2 != hash3


def test_stable_hash_positive_integer():
    """Hash must be positive 32-bit integer."""
    hash_val = _stable_hash("test")
    assert isinstance(hash_val, int)
    assert 0 <= hash_val < 2**32
