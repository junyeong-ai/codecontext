"""HuggingFace configuration."""

from typing import Literal

from pydantic import BaseModel, Field


class HuggingFaceConfig(BaseModel):
    """HuggingFace embedding provider configuration."""

    model_name: str = Field(
        default="jinaai/jina-code-embeddings-0.5b", description="Model identifier or path"
    )
    cache_dir: str | None = Field(default=None, description="Model cache directory")

    device: Literal["auto", "cpu", "cuda", "mps"] = Field(default="auto")
    device_threads: int = Field(default=0, ge=0, le=32)
    device_memory_fraction: float = Field(default=0.8, ge=0.1, le=1.0)

    # None = auto (cpu:16, mps:64, cuda:128)
    batch_size: int | None = Field(default=None)

    # GPU/MPS only
    use_fp16: bool = Field(default=False)

    # 8bit = 50% memory, 4bit = 75% memory reduction
    quantization: Literal["none", "8bit", "4bit"] = Field(default="none")

    normalize_embeddings: bool = Field(default=True)
    max_length: int = Field(default=32768, ge=512, le=32768)

    # Cleanup every N batches (lower = more stable, slower)
    cleanup_interval: int = Field(default=5, ge=1, le=100)

    # Enable jemalloc detection (CPU: 2x faster, -50% memory)
    use_jemalloc: bool = Field(default=True)
