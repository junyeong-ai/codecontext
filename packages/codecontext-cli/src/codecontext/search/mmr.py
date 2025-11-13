"""Maximal Marginal Relevance (MMR) re-ranking for search results."""

import logging
import time
from typing import Any

import numpy as np

from codecontext_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class MMRReranker:
    """Maximal Marginal Relevance re-ranker for diversity-aware search results.

    λ=1.0 (pure relevance), λ=0.7 (70% relevance + 30% diversity, recommended)
    Based on Carbonell & Goldstein (1998).
    """

    def __init__(
        self,
        lambda_param: float = 0.7,
        max_iterations: int = 100,
        timeout_seconds: float = 3.0,
    ) -> None:
        """
        Initialize MMR re-ranker.

        Args:
            lambda_param: Trade-off between relevance (1.0) and diversity (0.0)
                         Default 0.7 = 70% relevance + 30% diversity
            max_iterations: Maximum iterations to prevent infinite loops
                           Default 100 iterations (reduced from 1000 for safety)
            timeout_seconds: Maximum time in seconds (default 3.0)
        """
        if not 0.0 <= lambda_param <= 1.0:
            raise InvalidParameterError("lambda_param", lambda_param, "must be in [0.0, 1.0]")

        if max_iterations <= 0:
            raise InvalidParameterError("max_iterations", max_iterations, "must be positive")

        self.lambda_param = lambda_param
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds

    def rerank(
        self,
        query_embedding: list[float],
        results: list[dict[str, Any]],
        embeddings_dict: dict[str, list[float]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        Re-rank results using MMR algorithm with actual embedding vectors.

        Args:
            query_embedding: Query embedding vector
            results: Search results sorted by relevance score
            embeddings_dict: Map of result IDs to embedding vectors
            top_k: Number of results to return

        Returns:
            Re-ranked results balancing relevance and diversity
        """
        if not results:
            return []

        if top_k <= 0:
            return []

        # Already sorted by relevance, take top candidates
        candidates = results[: min(len(results), top_k * 3)]

        # Convert query embedding to numpy array for faster computation
        query_vec = np.array(query_embedding, dtype=np.float32)

        selected = []
        remaining = list(candidates)

        # First result is always the most relevant
        if remaining:
            selected.append(remaining.pop(0))

        # Iteratively select remaining results with iteration and timeout guards
        start_time = time.time()
        iterations = 0

        while remaining and len(selected) < top_k:
            iterations += 1

            # Guard against infinite loops
            if iterations > self.max_iterations:
                logger.warning(
                    f"MMR reranking exceeded max iterations ({self.max_iterations}), "
                    f"returning {len(selected)} results"
                )
                break

            # Timeout guard
            elapsed = time.time() - start_time
            if elapsed > self.timeout_seconds:
                logger.warning(
                    f"MMR reranking timeout ({elapsed:.2f}s > {self.timeout_seconds}s), "
                    f"returning {len(selected)} results after {iterations} iterations"
                )
                break

            best_score = -float("inf")
            best_idx = -1

            for idx, candidate in enumerate(remaining):
                # MMR score = λ * Relevance - (1-λ) * MaxSimilarity
                mmr_score = self._compute_mmr_score(candidate, selected, query_vec, embeddings_dict)

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx >= 0:
                selected.append(remaining.pop(best_idx))
            else:
                break

        return selected

    def _compute_mmr_score(
        self,
        candidate: dict[str, Any],
        selected: list[dict[str, Any]],
        query_vec: np.ndarray,
        embeddings_dict: dict[str, list[float]],
    ) -> float:
        """
        Compute MMR score for a candidate using actual embedding vectors.

        Args:
            candidate: Candidate result
            selected: Already selected results
            query_vec: Query embedding vector (numpy array)
            embeddings_dict: Map of result IDs to embedding vectors

        Returns:
            MMR score
        """
        # Get candidate embedding
        candidate_id = candidate.get("id", "")
        candidate_emb = embeddings_dict.get(candidate_id)

        if candidate_emb is None:
            # Fallback: use fusion score only if embedding not available
            return candidate.get("score", 0.0)

        candidate_vec = np.array(candidate_emb, dtype=np.float32)

        # Relevance: cosine similarity to query
        relevance = self._cosine_similarity(query_vec, candidate_vec)

        # Diversity penalty: maximum cosine similarity to selected items
        max_similarity = 0.0
        for selected_item in selected:
            selected_id = selected_item.get("id", "")
            selected_emb = embeddings_dict.get(selected_id)

            if selected_emb is not None:
                selected_vec = np.array(selected_emb, dtype=np.float32)
                similarity = self._cosine_similarity(candidate_vec, selected_vec)
                max_similarity = max(max_similarity, similarity)

        # MMR formula
        mmr_score: float = self.lambda_param * relevance - (1 - self.lambda_param) * max_similarity

        return mmr_score

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector (numpy array)
            vec2: Second vector (numpy array)

        Returns:
            Cosine similarity [0.0, 1.0]
        """
        # Normalize to [0, 1] range (cosine similarity is in [-1, 1])
        dot_product = float(np.dot(vec1, vec2))
        norm1 = float(np.linalg.norm(vec1))
        norm2 = float(np.linalg.norm(vec2))

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        cosine_sim = dot_product / (norm1 * norm2)

        # Normalize to [0, 1]: (cosine + 1) / 2
        return (cosine_sim + 1.0) / 2.0
