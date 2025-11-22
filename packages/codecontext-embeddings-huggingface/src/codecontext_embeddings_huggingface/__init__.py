"""HuggingFace embedding provider."""

__version__ = "0.7.0"

from codecontext_embeddings_huggingface.config import HuggingFaceConfig
from codecontext_embeddings_huggingface.provider import HuggingFaceEmbeddingProvider

__all__ = [
    "HuggingFaceEmbeddingProvider",
    "HuggingFaceConfig",
]
