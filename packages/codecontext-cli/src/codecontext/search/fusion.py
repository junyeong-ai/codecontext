"""Fusion methods for combining search results.

Implements Normalized Linear Fusion and Adaptive Fusion for hybrid search.

References:
- Elasticsearch 2023: Score-based weighted fusion
- Qdrant 2024: Normalized linear combination
- Pinecone 2024: Adaptive alpha for hybrid search
"""

import logging

logger = logging.getLogger(__name__)


class NormalizedLinearFusion:
    """Score-based weighted fusion with min-max normalization.

    Algorithm: Normalize to [0,1], then combine: fused = w1*norm1 + w2*norm2

    Based on Elasticsearch 2023, Qdrant 2024 hybrid search.
    """

    def fuse(
        self,
        result_lists: dict[str, list[tuple[str, float]]],
        weights: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Fuse multiple result lists using normalized linear combination.

        Args:
            result_lists: Dictionary mapping strategy name to (doc_id, score) lists
            weights: Optional weights for each strategy (default: equal)

        Returns:
            Dictionary mapping doc_id to fused score
        """
        # Set default weights if not provided
        if weights is None:
            weights = {name: 1.0 for name in result_lists}

        # Normalize each result list
        normalized_lists = {}
        for name, results in result_lists.items():
            if results:
                normalized_lists[name] = self._normalize_scores(results)
            else:
                normalized_lists[name] = []

        # Collect all document IDs
        all_doc_ids: set[str] = set()
        for results in normalized_lists.values():
            all_doc_ids.update(doc_id for doc_id, _ in results)

        # Create score lookup for fast access
        score_dicts: dict[str, dict[str, float]] = {}
        for name, results in normalized_lists.items():
            score_dicts[name] = {doc_id: score for doc_id, score in results}

        # Compute weighted linear combination
        fused_scores: dict[str, float] = {}
        for doc_id in all_doc_ids:
            fused_score = 0.0
            for name, weight in weights.items():
                if name in score_dicts:
                    fused_score += weight * score_dicts[name].get(doc_id, 0.0)
            fused_scores[doc_id] = fused_score

        return fused_scores

    def _normalize_scores(self, results: list[tuple[str, float]]) -> list[tuple[str, float]]:
        """Normalize scores to [0, 1] using min-max normalization."""
        if not results:
            return []

        scores = [score for _, score in results]
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score

        # Handle edge case: all scores are the same
        if score_range < 1e-10:
            return [(doc_id, 1.0) for doc_id, _ in results]

        # Min-max normalization: (x - min) / (max - min)
        normalized = []
        for doc_id, score in results:
            norm_score = (score - min_score) / score_range
            normalized.append((doc_id, norm_score))

        return normalized


class AdaptiveFusion:
    """Adaptive fusion with cross-lingual detection.

    Uses base weights from config, with pure vector fallback for cross-lingual queries.
    """

    def __init__(self, base_bm25_weight: float = 0.4):
        self.bm25_weight = base_bm25_weight
        self.vector_weight = 1.0 - base_bm25_weight
        self.fusion = NormalizedLinearFusion()

    def fuse(
        self,
        bm25_results: list[tuple[str, float]],
        vector_results: list[tuple[str, float]],
        bm25_boost: float | None = None,
    ) -> dict[str, float]:
        """Fuse BM25 and vector results.

        Args:
            bm25_results: List of (doc_id, score) tuples from BM25
            vector_results: List of (doc_id, score) tuples from vector search
            bm25_boost: Optional BM25 weight override (e.g., 0.75 for CODE_NAVIGATION)

        Returns:
            Dictionary mapping doc_id to fused score
        """
        if self._is_cross_lingual(bm25_results):
            bm25_w, vec_w = 0.0, 1.0
        elif bm25_boost is not None:
            bm25_w, vec_w = bm25_boost, 1.0 - bm25_boost
        else:
            bm25_w, vec_w = self.bm25_weight, self.vector_weight

        logger.debug(f"Fusion weights: BM25={bm25_w:.2f}, Vector={vec_w:.2f}")

        return self.fusion.fuse(
            {"bm25": bm25_results, "vector": vector_results},
            {"bm25": bm25_w, "vector": vec_w},
        )

    def _is_cross_lingual(self, bm25_results: list[tuple[str, float]]) -> bool:
        """Check if query is cross-lingual (BM25 scores near zero)."""
        if not bm25_results:
            return True
        return max(score for _, score in bm25_results) < 0.01
