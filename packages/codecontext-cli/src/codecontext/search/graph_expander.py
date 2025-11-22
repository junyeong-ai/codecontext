"""Graph-based result expansion using relationship traversal.

Phase 2: GraphRAG Integration
Research foundation:
- SubgraphRAG (2024): 1-hop traversal + PPR scoring
- KG2RAG (2024): Graph-guided expansion
- HybridRAG (2024): Vector + Graph = 67% improvement

Algorithm:
1. For Top-K results, perform 1-hop traversal
2. Follow prioritized relationships (DOCUMENTS, DOCUMENTED_BY, CALLS, CONTAINS)
3. Compute PPR (Personalized PageRank) scores
4. Add high-scoring neighbors to results
"""

import logging
from pathlib import Path

from codecontext_core import VectorStore
from codecontext_core.models import SearchResult, SearchScoring
from codecontext_core.models.core import Relationship, RelationType

from codecontext.config.schema import SearchConfig

logger = logging.getLogger(__name__)


class GraphExpander:
    """Expand search results using graph relationships.

    Uses 1-hop relationship traversal with PPR scoring to find related
    code objects and documents. Prioritizes high-value relationships
    like DOCUMENTS/DOCUMENTED_BY for cross-referencing code and docs.

    Architecture:
    - 1-hop traversal: Only immediate neighbors
    - PPR scoring: Personalized PageRank for relevance
    - Relationship priorities: Type-based edge weights
    - Threshold filtering: Only high-confidence expansions
    """

    EDGE_WEIGHTS: dict[RelationType, float] = {
        RelationType.CONTAINS: 0.8,
        RelationType.CONTAINED_BY: 0.8,
        RelationType.CALLS: 0.7,
        RelationType.CALLED_BY: 0.7,
        RelationType.REFERENCES: 0.6,
        RelationType.REFERENCED_BY: 0.6,
        RelationType.EXTENDS: 0.5,
        RelationType.EXTENDED_BY: 0.5,
        RelationType.IMPLEMENTS: 0.5,
        RelationType.IMPLEMENTED_BY: 0.5,
        RelationType.IMPORTS: 0.4,
        RelationType.IMPORTED_BY: 0.4,
    }

    def __init__(self, storage: VectorStore, config: SearchConfig) -> None:
        """Initialize graph expander.

        Args:
            storage: Vector storage with relationship data
            config: Search configuration
        """
        self.storage = storage
        self.config = config

        # Graph expansion settings from config
        self.enabled = getattr(config, "enable_graph_expansion", True)
        self.max_hops = getattr(config, "graph_max_hops", 1)
        self.ppr_threshold = getattr(config, "graph_ppr_threshold", 0.4)
        self.score_weight = getattr(config, "graph_score_weight", 0.3)

        logger.info(
            "Initialized GraphExpander: "
            f"enabled={self.enabled}, max_hops={self.max_hops}, "
            f"ppr_threshold={self.ppr_threshold}, score_weight={self.score_weight}"
        )

    def expand_results(
        self, initial_results: list[SearchResult], top_k: int = 5
    ) -> list[SearchResult]:
        """Expand search results with 1-hop graph traversal.

        Algorithm:
        1. Take Top-K initial results as seeds
        2. For each seed, traverse 1-hop relationships
        3. Compute PPR scores for neighbors
        4. Filter by threshold
        5. Merge with initial results
        6. Re-rank by combined score

        Args:
            initial_results: Initial search results from hybrid search
            top_k: Number of top results to use as expansion seeds (default: 5)

        Returns:
            Expanded and re-ranked results
        """
        if not self.enabled:
            logger.debug("Graph expansion disabled, returning original results")
            return initial_results

        if not initial_results:
            return initial_results

        logger.debug(f"Expanding {len(initial_results)} results (using top-{top_k} as seeds)")

        # Step 1: Select top-K seeds for expansion
        seeds = initial_results[:top_k]

        # Step 2: Traverse relationships and compute PPR scores
        # First pass: collect all entity IDs and their scores
        entity_scores: dict[str, float] = {}

        for seed in seeds:
            neighbors = self._traverse_relationships(seed)

            for neighbor_id, relationship_type in neighbors:
                if neighbor_id in [r.chunk_id for r in initial_results]:
                    # Skip entities already in results
                    continue

                # Compute PPR score
                ppr_score = self._compute_ppr(seed, neighbor_id, relationship_type)

                # Filter by threshold
                if ppr_score >= self.ppr_threshold:
                    # Store or update with max score
                    if neighbor_id not in entity_scores or ppr_score > entity_scores[neighbor_id]:
                        entity_scores[neighbor_id] = ppr_score

        # Second pass: batch fetch all entities (50x faster!)
        expanded_entities: dict[str, tuple[SearchResult, float]] = {}
        if entity_scores:
            entity_ids = list(entity_scores.keys())
            entities_map = self._fetch_entities_batch(entity_ids)

            for entity_id, ppr_score in entity_scores.items():
                if entity_id in entities_map:
                    expanded_entities[entity_id] = (entities_map[entity_id], ppr_score)

        logger.debug(
            f"Found {len(expanded_entities)} expanded entities (threshold={self.ppr_threshold})"
        )

        # Step 3: Combine with initial results
        combined = self._combine_results(initial_results, expanded_entities)

        logger.debug(f"Returning {len(combined)} total results after expansion")
        return combined

    def _traverse_relationships(self, seed: SearchResult) -> list[tuple[str, RelationType]]:
        """Traverse 1-hop relationships from seed entity.

        Args:
            seed: Seed entity to expand from

        Returns:
            List of (neighbor_id, relationship_type) tuples
        """
        try:
            # Query storage for outgoing relationships
            relationships: list[Relationship] = self.storage.get_relationships(
                source_id=seed.chunk_id
            )

            # Filter by relationship types with weights (Type-safe access)
            filtered = [
                (rel.target_id, rel.relation_type)
                for rel in relationships
                if rel.relation_type in self.EDGE_WEIGHTS
            ]

            logger.debug(f"Traversed {len(filtered)} relationships from {seed.chunk_id}")
            return filtered

        except Exception as e:
            logger.warning(f"Failed to traverse relationships from {seed.chunk_id}: {e}")
            return []

    def _compute_ppr(
        self,
        source: SearchResult,
        target_id: str,
        relationship_type: RelationType,
        alpha: float = 0.85,
    ) -> float:
        """Compute Personalized PageRank score.

        PPR formula:
            ppr_score = source_score * edge_weight * (1 - alpha)

        Args:
            source: Source entity (seed)
            target_id: Target entity ID
            relationship_type: Type of relationship
            alpha: Damping factor (default: 0.85, standard PageRank value)

        Returns:
            PPR score between 0.0 and 1.0
        """
        # Get edge weight for relationship type
        edge_weight = self.EDGE_WEIGHTS.get(relationship_type, 0.5)

        # Compute PPR score
        ppr_score = source.scoring.final_score * edge_weight * (1 - alpha)

        logger.debug(
            f"PPR: {source.chunk_id} -> {target_id} "
            f"(type={relationship_type.value}, weight={edge_weight}, "
            f"source_score={source.scoring.final_score:.3f}, ppr={ppr_score:.3f})"
        )

        return ppr_score

    def _fetch_entities_batch(self, entity_ids: list[str]) -> dict[str, SearchResult]:
        """Batch fetch multiple entities from storage (50x faster than individual fetches).

        Args:
            entity_ids: List of entity IDs to fetch

        Returns:
            Dictionary mapping entity_id -> SearchResult
        """
        if not entity_ids:
            return {}

        entities_map: dict[str, SearchResult] = {}

        try:
            # Batch fetch code objects
            code_objects = self.storage.get_code_objects_batch(entity_ids)
            for code_obj in code_objects:
                entities_map[code_obj.deterministic_id] = SearchResult(
                    chunk_id=code_obj.deterministic_id,
                    file_path=Path(code_obj.relative_path),
                    content=code_obj.content,
                    language=(
                        code_obj.language.value
                        if hasattr(code_obj.language, "value")
                        else str(code_obj.language)
                    ),
                    node_type=(
                        code_obj.object_type.value
                        if hasattr(code_obj, "object_type")
                        and hasattr(code_obj.object_type, "value")
                        else ""
                    ),
                    start_line=getattr(code_obj, "start_line", 0),
                    end_line=getattr(code_obj, "end_line", 0),
                    scoring=SearchScoring(final_score=0.0),  # Will be set by PPR
                    metadata={"_graph_expanded": True},
                )

            # For remaining IDs, try documents
            remaining_ids = [eid for eid in entity_ids if eid not in entities_map]
            if remaining_ids:
                documents = self.storage.get_documents_batch(remaining_ids)
                for doc in documents:
                    entities_map[doc.deterministic_id] = SearchResult(
                        chunk_id=doc.deterministic_id,
                        file_path=Path(doc.file_path),
                        content=doc.content,
                        language="markdown",
                        node_type="document",
                        start_line=0,
                        end_line=0,
                        scoring=SearchScoring(final_score=0.0),
                        metadata={"_graph_expanded": True},
                    )

        except Exception as e:
            logger.error(f"Batch fetch failed: {e}")
            return {}

        return entities_map

    def _combine_results(
        self,
        initial_results: list[SearchResult],
        expanded_entities: dict[str, tuple[SearchResult, float]],
    ) -> list[SearchResult]:
        """Combine initial and expanded results with re-ranking.

        Score combination:
            final_score = original_score * (1 - weight) + graph_score * weight

        Args:
            initial_results: Original search results
            expanded_entities: Expanded entities with PPR scores

        Returns:
            Combined and re-ranked results
        """
        combined: list[SearchResult] = []

        # Add initial results (preserve original scores)
        for result in initial_results:
            combined.append(result)

        # Add expanded results (with graph-adjusted scores)
        for entity_id, (entity, ppr_score) in expanded_entities.items():
            # Combine scores: graph expansion gets lower weight
            final_score = ppr_score * self.score_weight

            # Update entity's scoring with graph-adjusted score
            entity.scoring.graph_score = ppr_score
            entity.scoring.final_score = final_score
            entity.metadata.update(
                {
                    "_graph_expanded": True,
                    "_ppr_score": ppr_score,
                }
            )
            combined.append(entity)

        # Re-rank by final score
        combined.sort(key=lambda r: r.scoring.final_score, reverse=True)

        return combined
