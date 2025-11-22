"""HuggingFace configuration."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class InstructionConfig(BaseModel):
    """Instruction-based embedding configuration.

    Based on Jina Code Embeddings official instruction framework.
    Enables asymmetric query/passage encoding and task-specific prompts.
    """

    enabled: bool = Field(default=True, description="Enable instruction-based embeddings")

    nl2code_query: str = Field(
        default="Find the most relevant code snippet given the following query:\n",
        description="Instruction prefix for natural language to code queries",
    )
    nl2code_passage: str = Field(
        default="Candidate code snippet:\n",
        description="Instruction prefix for code passages",
    )

    code2code_query: str = Field(
        default="Find an equivalent code snippet given the following code snippet:\n",
        description="Instruction prefix for code similarity queries",
    )
    code2code_passage: str = Field(
        default="Candidate code snippet:\n",
        description="Instruction prefix for code similarity passages",
    )

    qa_query: str = Field(
        default="Find the most relevant answer given the following question:\n",
        description="Instruction prefix for QA queries",
    )
    qa_passage: str = Field(
        default="Candidate answer:\n", description="Instruction prefix for answers/docstrings"
    )

    document_passage: str = Field(
        default="Candidate documentation:\n",
        description="Instruction prefix for documentation passages",
    )


class HuggingFaceConfig(BaseModel):
    """HuggingFace embedding provider configuration."""

    model_name: str = Field(
        default="jinaai/jina-code-embeddings-0.5b", description="Model identifier or path"
    )
    cache_dir: str | None = Field(default=None, description="Model cache directory")

    # LoRA adapter support
    lora_adapter_path: str | None = Field(
        default=None, description="Path to LoRA adapter directory (optional, requires PEFT library)"
    )

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
    # NOTE: Detection only - actual loading requires LD_PRELOAD by user
    # For ARM64 + Qdrant embedded: Use remote Qdrant mode (Docker) instead
    use_jemalloc: bool = Field(default=True)

    # Instruction-based embeddings
    instructions: InstructionConfig = Field(
        default_factory=InstructionConfig,
        description="Instruction configuration for asymmetric query/passage encoding",
    )

    @field_validator("lora_adapter_path")
    @classmethod
    def validate_lora_path(cls, v: str | None) -> str | None:
        """Validate LoRA adapter path exists and contains required files."""
        if v is None:
            return None

        path = Path(v).expanduser().resolve()

        if not path.exists():
            raise ValueError(f"LoRA adapter path does not exist: {path}")

        if not path.is_dir():
            raise ValueError(f"LoRA adapter path must be a directory: {path}")

        config_file = path / "adapter_config.json"
        if not config_file.exists():
            raise ValueError(f"Invalid LoRA adapter: missing adapter_config.json in {path}")

        return str(path)
