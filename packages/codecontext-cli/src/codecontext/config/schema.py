"""Pydantic configuration schema models for CodeContext."""

from pathlib import Path
from typing import Literal

from codecontext_embeddings_huggingface.config import HuggingFaceConfig
from codecontext_embeddings_openai.config import OpenAIConfig
from codecontext_translation_nllb.config import NLLBConfig
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TranslationConfig(BaseModel):
    """Configuration for translation providers."""

    enabled: bool = Field(default=True, description="Enable multilingual search")
    provider: Literal["nllb"] = Field(default="nllb", description="Translation provider")
    nllb: NLLBConfig = Field(default_factory=NLLBConfig)


class EmbeddingConfig(BaseModel):
    """Configuration for embedding providers."""

    provider: Literal["huggingface", "openai"] = Field(
        default="huggingface",
        description="Embedding provider",
    )
    huggingface: HuggingFaceConfig = Field(default_factory=HuggingFaceConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)


class ProjectConfig(BaseModel):
    """Project-specific configuration."""

    name: str | None = Field(default=None, description="Project name (auto-detected if None)")
    type: str | None = Field(default=None, description="Project type (simple, multi-module)")

    # Indexing patterns (glob)
    include: list[str] = Field(
        default_factory=lambda: ["**"],
        description="Glob patterns for files to include",
    )
    exclude: list[str] = Field(
        default_factory=lambda: [
            "**/.git/**",
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/build/**",
            "**/dist/**",
        ],
        description="Glob patterns for files to exclude",
    )


class LocalStorageConfig(BaseModel):
    """Local ChromaDB configuration."""

    path: Path = Field(
        default=Path(".codecontext/chroma"),
        description="Local data path",
    )
    port: int = Field(
        default=8000,
        description="Local server port",
        ge=1,
        le=65535,
    )
    auto_start: bool = Field(
        default=True,
        description="Auto-start local server if not running",
    )


class RemoteStorageConfig(BaseModel):
    """Remote ChromaDB configuration."""

    host: str = Field(description="Remote server host")
    port: int = Field(default=8000, ge=1, le=65535)


class ChromaDBConfig(BaseModel):
    """Configuration for ChromaDB storage provider."""

    host: str = Field(
        default="localhost",
        description="ChromaDB server host",
    )
    port: int = Field(
        default=8000,
        description="ChromaDB server port",
        ge=1,
        le=65535,
    )
    collection_prefix: str = Field(
        default="codecontext",
        description="Prefix for collection names",
    )

    def get_collection_name(self, project_id: str, collection_type: str) -> str:
        """Generate collection name."""
        name = f"{self.collection_prefix}_{project_id}_{collection_type}"
        return name.lower().replace("-", "_")[:63]


class StorageConfig(BaseModel):
    """Configuration for storage providers."""

    mode: Literal["local", "remote"] = Field(
        default="local",
        description="Storage mode",
    )
    provider: str = Field(
        default="chromadb",
        description="Storage provider",
    )
    chromadb: ChromaDBConfig = Field(
        default_factory=ChromaDBConfig,
        description="ChromaDB configuration",
    )
    local: LocalStorageConfig = Field(
        default_factory=LocalStorageConfig,
        description="Local ChromaDB configuration",
    )
    remote: RemoteStorageConfig | None = Field(
        default=None,
        description="Remote ChromaDB configuration",
    )


class MemoryManagementConfig(BaseModel):
    """Memory management during indexing."""

    force_gc_after_chunk: bool = Field(default=True)
    clear_gpu_cache: bool = Field(default=True)
    gpu_sync_before_clear: bool = Field(default=True)


class ParsingConfig(BaseModel):
    """Tree-sitter parsing optimization configuration."""

    # Default 5s, prevent infinite loops on complex files
    timeout_micros: int = Field(default=5_000_000, ge=100_000, le=30_000_000)

    # Partial AST recovery on syntax errors
    enable_error_recovery: bool = Field(default=True)
    partial_parse_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    # Auto-chunk large files using cAST algorithm
    enable_chunking: bool = Field(default=True)
    chunking_threshold_lines: int = Field(default=1000, ge=100, le=10000)
    chunking_threshold_bytes: int = Field(default=50_000, ge=10_000, le=1_000_000)

    enable_incremental_parsing: bool = Field(default=False)
    enable_performance_monitoring: bool = Field(default=False)

    # Kotlin/TypeScript need longer timeouts for complex DSL/types
    language_overrides: dict[str, dict[str, int]] = Field(
        default_factory=lambda: {
            "kotlin": {"timeout_micros": 10_000_000},
            "typescript": {"timeout_micros": 7_000_000},
        }
    )


class IndexingConfig(BaseModel):
    """Configuration for indexing behavior."""

    # Memory control: lower = stable memory, higher = less overhead
    file_chunk_size: int = Field(default=30, ge=10, le=500)

    # Embedding batch size (GPU memory dependent)
    batch_size: int = Field(default=64, ge=32, le=512)

    languages: list[str] = Field(default=["python", "kotlin", "java", "javascript", "typescript"])
    max_file_size_mb: int = Field(default=10, ge=1, le=100)
    memory_management: MemoryManagementConfig = Field(default_factory=MemoryManagementConfig)

    # 0 = auto (cpu_count//2, max 8)
    parallel_workers: int = Field(default=0, ge=0, le=16)

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
            msg = f"Unsupported languages: {invalid}. Supported: {supported}"
            raise ValueError(msg)
        return v


class SearchConfig(BaseModel):
    """Hybrid search configuration (BM25 + Vector + GraphRAG + MMR)."""

    default_limit: int = Field(default=10, ge=1, le=100)

    # Fusion: 0.4 = 40% keyword + 60% semantic
    bm25_weight: float = Field(default=0.4, ge=0.0, le=1.0)

    # MMR: 0.75 = 75% relevance + 25% diversity
    mmr_lambda: float = Field(default=0.75, ge=0.0, le=1.0)

    # GraphRAG: 1-hop traversal with PPR scoring
    enable_graph_expansion: bool = Field(default=True)
    graph_max_hops: int = Field(default=1, ge=1, le=3)
    graph_ppr_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    graph_score_weight: float = Field(default=0.3, ge=0.0, le=1.0)

    # Over-retrieval for fusion (5x = retrieve 50 for top-10)
    bm25_retrieval_multiplier: int = Field(default=5, ge=1, le=20)
    vector_retrieval_multiplier: int = Field(default=5, ge=1, le=20)

    # Diversity: max 2 chunks per file
    max_chunks_per_file: int = Field(default=2, ge=1, le=10)
    diversity_preserve_top_n: int = Field(default=1, ge=0, le=10)


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = Field(
        default="INFO",
        description="Logging level",
    )
    format: str = Field(
        default="text",
        description="Log format (text or json)",
    )
    file: str | None = Field(
        default=None,
        description="Optional log file path",
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            msg = f"Invalid log level: {v}. Valid levels: {valid_levels}"
            raise ValueError(msg)
        return v.upper()

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate log format."""
        if v not in ["text", "json"]:
            msg = "format must be 'text' or 'json'"
            raise ValueError(msg)
        return v


class CodeContextConfig(BaseModel):
    """Main CodeContext configuration."""

    schema_version: str = Field(
        default="1.0.0",
        description="Config schema version for migration support",
    )
    project: ProjectConfig = Field(
        default_factory=ProjectConfig,
        description="Project-specific configuration",
    )
    translation: TranslationConfig = Field(
        default_factory=TranslationConfig,
        description="Translation provider configuration",
    )
    embeddings: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding provider configuration",
    )
    storage: StorageConfig = Field(
        default_factory=StorageConfig,
        description="Storage provider configuration",
    )
    indexing: IndexingConfig = Field(
        default_factory=IndexingConfig,
        description="Indexing configuration",
    )
    search: SearchConfig = Field(
        default_factory=SearchConfig,
        description="Search configuration",
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )

    model_config = ConfigDict(
        extra="forbid",  # Raise error on unknown fields
        validate_assignment=True,  # Validate on assignment
    )

    @classmethod
    def from_file(cls, path: Path) -> "CodeContextConfig":
        import yaml

        from codecontext_core.exceptions import ConfigurationError

        if not path.exists():
            msg = f"Config file not found: {path}"
            raise ConfigurationError(msg)
        try:
            with path.open() as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except (yaml.YAMLError, TypeError) as e:
            msg = f"Failed to parse config file {path}: {e}"
            raise ConfigurationError(msg) from e
