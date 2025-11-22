"""Search result data models for hybrid search functionality."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class SearchStrategy(Enum):
    """Search strategy used for retrieval."""

    BM25 = "bm25"
    """Keyword-based search using BM25 algorithm."""

    BM25_ONLY = "bm25_only"
    """Keyword-only search using BM25."""

    VECTOR_CODE = "vector_code"
    """Vector similarity search on code embeddings."""

    VECTOR_DESC = "vector_desc"
    """Vector similarity search on description embeddings."""

    VECTOR_ONLY = "vector_only"
    """Vector-only search (no BM25)."""

    GRAPH = "graph"
    """Graph-based relationship search."""

    GRAPH_ENHANCED = "graph_enhanced"
    """Graph-enhanced hybrid search."""

    HYBRID = "hybrid"
    """Combined multi-strategy search."""


@dataclass
class SearchScoring:
    """Breakdown of search scores from different strategies."""

    bm25_score: Optional[float] = None
    """Score from BM25 keyword search."""

    vector_code_score: Optional[float] = None
    """Score from vector similarity on code."""

    vector_desc_score: Optional[float] = None
    """Score from vector similarity on descriptions."""

    graph_score: Optional[float] = None
    """Score from graph-based relevance."""

    final_score: float = 0.0
    """Final fused score combining all strategies."""

    def __post_init__(self) -> None:
        """Validate scoring data."""
        # BM25 scores are unbounded (can be > 1.0)
        # Vector scores are normalized (0.0-1.0)
        # Only validate vector and graph scores
        for score_name in ["vector_code_score", "vector_desc_score", "graph_score"]:
            score = getattr(self, score_name)
            if score is not None and not 0.0 <= score <= 1.0:
                raise ValueError(f"{score_name} must be between 0.0 and 1.0, got: {score}")

        # BM25 can be unbounded, just check non-negative
        if self.bm25_score is not None and self.bm25_score < 0.0:
            raise ValueError(f"bm25_score must be non-negative, got: {self.bm25_score}")

        if not 0.0 <= self.final_score <= 1.0:
            raise ValueError("final_score must be between 0.0 and 1.0")

    @property
    def has_bm25(self) -> bool:
        """Check if BM25 score is available."""
        return self.bm25_score is not None

    @property
    def has_vector(self) -> bool:
        """Check if any vector score is available."""
        return self.vector_code_score is not None or self.vector_desc_score is not None

    @property
    def has_graph(self) -> bool:
        """Check if graph score is available."""
        return self.graph_score is not None

    @property
    def strategy_count(self) -> int:
        """Count how many search strategies contributed scores."""
        count = 0
        if self.has_bm25:
            count += 1
        if self.vector_code_score is not None:
            count += 1
        if self.vector_desc_score is not None:
            count += 1
        if self.has_graph:
            count += 1
        return count


@dataclass
class SearchResult:
    """Search result with hybrid scoring and full context."""

    # Identity
    chunk_id: str
    """Unique identifier of the matched chunk."""

    file_path: Path
    """Path to the file containing the match."""

    # Content
    content: str
    """The matched code snippet."""

    nl_description: str = ""
    """Natural language description of the code."""

    # Scoring
    scoring: SearchScoring = field(default_factory=SearchScoring)
    """Detailed scoring breakdown from all strategies."""

    # Metadata
    language: str = ""
    """Programming language of the result."""

    node_type: str = ""
    """Type of code entity (function, class, etc.)."""

    start_line: int = 0
    """Starting line number in the file."""

    end_line: int = 0
    """Ending line number in the file."""

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional result-specific metadata."""

    result_type: str = "code"
    """Type of result: 'code' or 'document'."""

    def __post_init__(self) -> None:
        """Validate search result data."""
        if not isinstance(self.file_path, Path):
            self.file_path = Path(self.file_path)

        if self.start_line < 0:
            raise ValueError("start_line must be non-negative")

        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")

    # Backward compatibility properties
    @property
    def result_id(self) -> str:
        """Alias for chunk_id (backward compatibility)."""
        return self.chunk_id

    @property
    def score(self) -> float:
        """Alias for final_score (backward compatibility)."""
        return self.scoring.final_score

    @property
    def rank(self) -> int:
        """Ranking position (derived from metadata, backward compatibility)."""
        return int(self.metadata.get("rank", 0))

    # Core properties
    @property
    def final_score(self) -> float:
        """Get the final fused score."""
        return self.scoring.final_score

    @property
    def line_count(self) -> int:
        """Get the number of lines in this result."""
        return self.end_line - self.start_line + 1 if self.end_line > 0 else 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "chunk_id": self.chunk_id,
            "file_path": str(self.file_path),
            "content": self.content,
            "nl_description": self.nl_description,
            "final_score": self.final_score,
            "language": self.language,
            "node_type": self.node_type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "metadata": self.metadata,
        }

        # Add scoring breakdown
        if self.scoring:
            result["scoring"] = {
                "bm25_score": self.scoring.bm25_score,
                "vector_code_score": self.scoring.vector_code_score,
                "vector_desc_score": self.scoring.vector_desc_score,
                "graph_score": self.scoring.graph_score,
                "final_score": self.scoring.final_score,
            }

        return result


@dataclass
class SearchQuery:
    """Represents a search query with all parameters."""

    query_text: str
    """The search query text."""

    strategy: SearchStrategy = SearchStrategy.HYBRID
    """Search strategy to use."""

    limit: int = 10
    """Maximum number of results to return."""

    language_filter: Optional[str] = None
    """Filter results by programming language."""

    file_filter: Optional[str] = None
    """Filter results by file path pattern."""

    min_score: float = 0.0
    """Minimum score threshold for results."""

    query_embedding: Optional[list[float]] = None
    """Pre-computed embedding vector for the query text (for vector search)."""

    def __post_init__(self) -> None:
        """Validate query parameters."""
        if not self.query_text:
            raise ValueError("query_text cannot be empty")

        if self.limit <= 0:
            raise ValueError("limit must be positive")

        if not 0.0 <= self.min_score <= 1.0:
            raise ValueError("min_score must be between 0.0 and 1.0")
