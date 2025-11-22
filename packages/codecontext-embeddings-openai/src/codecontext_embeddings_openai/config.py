"""Configuration for OpenAI embedding provider."""

from pydantic import BaseModel, ConfigDict, Field


class OpenAIConfig(BaseModel):
    """Configuration for OpenAI embedding provider."""

    model_config = ConfigDict(extra="forbid")

    api_key: str = Field(
        description="OpenAI API key",
        default="",
        repr=False,  # Don't expose in logs
    )
    model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model name",
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=2048,
        description="Batch size for embedding generation",
    )
    max_retries: int = Field(
        default=6,
        ge=1,
        le=10,
        description="Maximum number of retry attempts",
    )
    rate_limit_rpm: int = Field(
        default=3000,
        ge=1,
        description="Rate limit in requests per minute",
    )
    rate_limit_tpm: int = Field(
        default=1000000,
        ge=1,
        description="Rate limit in tokens per minute",
    )
    timeout: int = Field(
        default=60,
        ge=1,
        description="Request timeout in seconds",
    )
    organization: str | None = Field(
        default=None,
        description="OpenAI organization ID (optional)",
    )
