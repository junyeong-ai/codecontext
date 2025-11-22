"""OpenAI embedding provider for CodeContext."""

from codecontext_embeddings_openai.config import OpenAIConfig
from codecontext_embeddings_openai.cost_tracker import CostTracker
from codecontext_embeddings_openai.provider import OpenAIEmbeddingProvider
from codecontext_embeddings_openai.rate_limiter import (
    AdaptiveRateLimiter,
    TokenBucketRateLimiter,
)

__version__ = "0.2.0"

__all__ = [
    "AdaptiveRateLimiter",
    "CostTracker",
    "OpenAIConfig",
    "OpenAIEmbeddingProvider",
    "TokenBucketRateLimiter",
]
