"""BM25F encoder for sparse vector generation."""

import hashlib
from functools import lru_cache

from codecontext_core.tokenizer import CodeTokenizer


@lru_cache(maxsize=10000)
def _stable_hash(token: str) -> int:
    """SHA-256 hash for sparse vector index."""
    return int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)


class BM25FEncoder:
    """BM25F encoder with field weights and length normalization."""

    def __init__(
        self,
        field_weights: dict[str, float],
        k1: float = 1.2,
        b: float = 0.75,
        avg_dl: float = 100.0,
    ):
        self.field_weights = field_weights
        self.k1 = k1
        self.b = b
        self.avg_dl = avg_dl

    def encode(self, document: dict[str, str | None]) -> tuple[list[int], list[float]]:
        """Encode document to sparse vector with BM25F scoring."""
        token_scores: dict[str, float] = {}

        # Tokenize all fields
        field_tokens: dict[str, list[str]] = {}
        total_tokens = 0

        for field_name, weight in self.field_weights.items():
            text = document.get(field_name)
            if text:
                tokens = CodeTokenizer.tokenize_text(text)
                field_tokens[field_name] = tokens
                total_tokens += len(tokens)

        dl = max(1, total_tokens)

        # Calculate BM25F scores
        for field_name, weight in self.field_weights.items():
            tokens = field_tokens.get(field_name, [])
            if not tokens:
                continue

            tf_map: dict[str, int] = {}
            for token in tokens:
                tf_map[token] = tf_map.get(token, 0) + 1

            for token, tf in tf_map.items():
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
                bm25_tf = numerator / denominator

                weighted_score = weight * bm25_tf
                token_scores[token] = token_scores.get(token, 0) + weighted_score

        indices = [_stable_hash(token) for token in token_scores]
        values = list(token_scores.values())

        return indices, values

    def encode_query(self, query: str) -> tuple[list[int], list[float]]:
        """Encode query to sparse vector."""
        tokens = CodeTokenizer.tokenize_text(query)

        tf_map: dict[str, int] = {}
        for token in tokens:
            tf_map[token] = tf_map.get(token, 0) + 1

        indices = [_stable_hash(token) for token in tf_map]
        values = [float(tf) for tf in tf_map.values()]

        return indices, values
