"""Cost tracking for OpenAI API usage."""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, ClassVar


@dataclass
class CostRecord:
    """Record of a single API call cost."""

    timestamp: float
    model: str
    tokens: int
    cost_usd: float
    request_id: str | None = None


class CostTracker:
    """
    Tracks costs for OpenAI API usage.

    Maintains running totals and supports cost estimation before making calls.
    """

    # Pricing as of 2024 (USD per 1K tokens)
    PRICING: ClassVar[dict[str, float]] = {
        "text-embedding-3-small": 0.00002,
        "text-embedding-3-large": 0.00013,
        "text-embedding-ada-002": 0.00010,
    }

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        """
        Initialize the cost tracker.

        Args:
            model: OpenAI embedding model name
        """
        self.model = model
        self.total_tokens = 0
        self.total_cost_usd = 0.0
        self.request_count = 0
        self.records: list[CostRecord] = []

    def get_cost_per_token(self, model: str | None = None) -> float:
        """
        Get cost per token for a model.

        Args:
            model: Model name (uses default if not specified)

        Returns:
            Cost in USD per token
        """
        model_name = model or self.model
        cost_per_1k = self.PRICING.get(model_name, 0.0)
        return cost_per_1k / 1000.0

    def estimate_cost(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> tuple[int, float]:
        """
        Estimate cost for embedding a list of texts.

        Uses rough heuristic: ~1.3 tokens per word.

        Args:
            texts: List of texts to embed
            model: Model name (uses default if not specified)

        Returns:
            Tuple of (estimated_tokens, estimated_cost_usd)
        """
        # Rough estimate: split by whitespace and multiply by 1.3
        total_words = sum(len(text.split()) for text in texts)
        estimated_tokens = int(total_words * 1.3)

        cost_per_token = self.get_cost_per_token(model)
        estimated_cost = estimated_tokens * cost_per_token

        return estimated_tokens, estimated_cost

    def record(
        self,
        tokens: int,
        model: str | None = None,
        request_id: str | None = None,
    ) -> float:
        """
        Record actual usage and cost.

        Args:
            tokens: Number of tokens used
            model: Model name (uses default if not specified)
            request_id: Optional request identifier

        Returns:
            Cost in USD for this request
        """
        model_name = model or self.model
        cost_per_token = self.get_cost_per_token(model_name)
        cost = tokens * cost_per_token

        # Update totals
        self.total_tokens += tokens
        self.total_cost_usd += cost
        self.request_count += 1

        # Record
        record = CostRecord(
            timestamp=time.time(),
            model=model_name,
            tokens=tokens,
            cost_usd=cost,
            request_id=request_id,
        )
        self.records.append(record)

        return cost

    def get_summary(self) -> dict[str, Any]:
        """
        Get cost summary.

        Returns:
            Dictionary with total tokens, cost, and statistics
        """
        return {
            "model": self.model,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "request_count": self.request_count,
            "average_tokens_per_request": (
                self.total_tokens / self.request_count if self.request_count > 0 else 0
            ),
            "average_cost_per_request": (
                self.total_cost_usd / self.request_count if self.request_count > 0 else 0.0
            ),
        }

    def get_recent_records(self, count: int = 10) -> list[dict[str, Any]]:
        """
        Get recent cost records.

        Args:
            count: Number of recent records to return

        Returns:
            List of cost records as dictionaries
        """
        recent = self.records[-count:] if self.records else []
        return [asdict(r) for r in recent]

    def save(self, path: Path) -> None:
        """
        Save cost tracking data to JSON file.

        Args:
            path: Path to save file
        """
        data = {
            "summary": self.get_summary(),
            "records": [asdict(r) for r in self.records],
        }

        with Path(path).open("w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: Path) -> None:
        """
        Load cost tracking data from JSON file.

        Args:
            path: Path to load file from
        """
        if not path.exists():
            return

        with path.open() as f:
            data = json.load(f)

        summary = data.get("summary", {})
        self.model = summary.get("model", self.model)
        self.total_tokens = summary.get("total_tokens", 0)
        self.total_cost_usd = summary.get("total_cost_usd", 0.0)
        self.request_count = summary.get("request_count", 0)

        self.records = [CostRecord(**record) for record in data.get("records", [])]

    def reset(self) -> None:
        """Reset all tracking data."""
        self.total_tokens = 0
        self.total_cost_usd = 0.0
        self.request_count = 0
        self.records = []
