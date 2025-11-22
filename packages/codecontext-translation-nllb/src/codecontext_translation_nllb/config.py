"""NLLB configuration."""

from typing import Literal

from pydantic import BaseModel, Field


class NLLBConfig(BaseModel):
    """NLLB translation provider configuration."""

    model_name: str = Field(default="facebook/nllb-200-distilled-600M")
    cache_dir: str | None = Field(default=None)
    device: Literal["cpu", "cuda", "mps"] = Field(default="cpu")
    device_threads: int = Field(default=0, ge=0, le=32)
    device_memory_fraction: float = Field(default=0.8, ge=0.1, le=1.0)
    batch_size: int = Field(default=16)
    use_fp16: bool = Field(default=False)
    cleanup_interval: int = Field(default=5, ge=1, le=100)
    max_length: int = Field(default=512, ge=128, le=1024)
