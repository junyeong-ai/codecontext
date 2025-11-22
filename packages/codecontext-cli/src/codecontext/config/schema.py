"""Configuration schema for CodeContext."""

from enum import Enum
from typing import Literal

from codecontext_embeddings_huggingface.config import HuggingFaceConfig
from codecontext_embeddings_openai.config import OpenAIConfig
from codecontext_translation_nllb.config import NLLBConfig
from pydantic import BaseModel, Field, field_validator, ValidationInfo


class FusionMethod(str, Enum):
    """Hybrid search fusion methods (Qdrant native)."""

    RRF = "rrf"
    DBSF = "dbsf"


class TranslationConfig(BaseModel):
    enabled: bool = True
    provider: Literal["nllb"] = "nllb"
    nllb: NLLBConfig = Field(default_factory=NLLBConfig)


class EmbeddingConfig(BaseModel):
    provider: Literal["huggingface", "openai"] = "huggingface"
    huggingface: HuggingFaceConfig = Field(default_factory=HuggingFaceConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)


class QdrantConfig(BaseModel):
    """Qdrant storage configuration."""

    mode: Literal["embedded", "remote"] = "embedded"
    path: str = Field(default="~/.codecontext/data")
    url: str | None = None
    api_key: str | None = None

    fusion_method: FusionMethod = Field(default=FusionMethod.RRF)

    prefetch_ratio_dense: float = Field(default=7.0, ge=1.0, le=10.0)
    prefetch_ratio_sparse: float = Field(default=3.0, ge=0.5, le=10.0)

    upsert_batch_size: int = Field(default=100, ge=10, le=1000)
    enable_performance_logging: bool = False

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None, info: ValidationInfo) -> str | None:
        if info.data.get("mode") == "remote" and not v:
            raise ValueError("url required when mode=remote")
        return v


class StorageConfig(BaseModel):
    provider: Literal["qdrant"] = "qdrant"
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)


class MemoryConfig(BaseModel):
    force_gc_after_chunk: bool = True
    clear_gpu_cache: bool = True
    gpu_sync_before_clear: bool = True


class ParsingConfig(BaseModel):
    timeout_micros: int = Field(default=5_000_000, ge=100_000, le=30_000_000)
    enable_error_recovery: bool = True
    partial_parse_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    enable_chunking: bool = True
    chunking_threshold_lines: int = Field(default=1000, ge=100, le=10000)
    chunking_threshold_bytes: int = Field(default=50_000, ge=10_000, le=1_000_000)
    language_overrides: dict[str, dict[str, int]] = Field(
        default_factory=lambda: {
            "kotlin": {"timeout_micros": 10_000_000},
            "typescript": {"timeout_micros": 7_000_000},
        }
    )


class FieldWeights(BaseModel):
    """BM25F field weights.

    Note: 'title' excluded - duplicates 'name' for documents.
    """

    name: int = 15
    qualified_name: int = 12
    signature: int = 10
    docstring: int = 8
    content: int = 6
    filename: int = 4
    file_path: int = 2

    k1: float = Field(default=1.2, ge=0.0, le=3.0)
    b: float = Field(default=0.75, ge=0.0, le=1.0)
    avg_dl: float = Field(default=100.0, ge=1.0, le=10000.0)


class IndexingConfig(BaseModel):
    file_chunk_size: int = Field(default=30, ge=10, le=500)
    batch_size: int = Field(default=64, ge=32, le=512)
    languages: list[str] = Field(
        default_factory=lambda: [
            "python",
            "kotlin",
            "java",
            "javascript",
            "typescript",
            "markdown",
            "json",
            "yaml",
            "properties",
        ]
    )
    max_file_size_mb: int = Field(default=10, ge=1, le=100)
    parallel_workers: int = Field(default=0, ge=0, le=16)
    field_weights: FieldWeights = Field(default_factory=FieldWeights)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    parsing: ParsingConfig = Field(default_factory=ParsingConfig)

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str]) -> list[str]:
        supported = {
            "python",
            "kotlin",
            "java",
            "javascript",
            "typescript",
            "markdown",
            "json",
            "yaml",
            "properties",
        }
        invalid = set(v) - supported
        if invalid:
            raise ValueError(f"Unsupported languages: {invalid}")
        return v


class TypeBoosting(BaseModel):
    """Type-specific boost values (code-centric)."""

    class_: float = Field(default=0.12, alias="class", ge=0.0, le=0.5)
    method: float = Field(default=0.10, alias="method", ge=0.0, le=0.5)
    function: float = Field(default=0.10, alias="function", ge=0.0, le=0.5)
    enum: float = Field(default=0.08, alias="enum", ge=0.0, le=0.5)
    interface: float = Field(default=0.06, alias="interface", ge=0.0, le=0.5)
    markdown: float = Field(default=0.07, alias="markdown", ge=0.0, le=0.5)
    config: float = Field(default=0.05, alias="config", ge=0.0, le=0.5)
    type: float = Field(default=0.04, alias="type", ge=0.0, le=0.5)
    field: float = Field(default=0.02, alias="field", ge=0.0, le=0.5)
    variable: float = Field(default=0.0, alias="variable", ge=0.0, le=0.5)


class SearchConfig(BaseModel):
    default_limit: int = Field(default=10, ge=1, le=100)
    enable_graph_expansion: bool = True
    graph_max_hops: int = Field(default=1, ge=1, le=3)
    graph_ppr_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    graph_score_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    max_chunks_per_file: int = Field(default=2, ge=1, le=10)
    diversity_preserve_top_n: int = Field(default=1, ge=0, le=10)
    type_boosting: TypeBoosting = Field(default_factory=TypeBoosting)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "text"
    file: str | None = None

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()


class ProjectConfig(BaseModel):
    name: str | None = None
    include: list[str] = Field(default_factory=lambda: ["**"])
    exclude: list[str] = Field(
        default_factory=lambda: [
            "**/.git/**",
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/build/**",
            "**/dist/**",
            "**/pnpm-lock.yaml",
            "**/package-lock.json",
            "**/yarn.lock",
            "**/Cargo.lock",
            "**/poetry.lock",
            "**/Gemfile.lock",
        ]
    )


class Config(BaseModel):
    embeddings: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    indexing: IndexingConfig = Field(default_factory=IndexingConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)
