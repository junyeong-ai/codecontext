"""OpenAI embedding provider implementation."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any, cast

import tiktoken
from codecontext_core.exceptions import EmbeddingError
from codecontext_core.interfaces import EmbeddingProvider, InstructionType
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from tiktoken import Encoding
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from codecontext_embeddings_openai.config import OpenAIConfig
from codecontext_embeddings_openai.cost_tracker import CostTracker
from codecontext_embeddings_openai.rate_limiter import AdaptiveRateLimiter

logger = logging.getLogger(__name__)


def _apply_nest_asyncio() -> None:
    """Enable nested event loops using nest_asyncio (no type stubs available)."""
    import nest_asyncio

    # Cast to Any since nest_asyncio has no type stubs
    apply_fn = cast(Any, nest_asyncio.apply)
    apply_fn()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider with rate limiting and cost tracking.

    Features:
    - Exponential backoff retry
    - Adaptive rate limiting (RPM/TPM)
    - Cost tracking
    - Batch processing with token counting
    """

    def __init__(self, config: OpenAIConfig) -> None:
        """Initialize OpenAI provider.

        Args:
            config: OpenAI configuration
        """
        self.config = config
        self.client: AsyncOpenAI | None = None
        self.rate_limiter: AdaptiveRateLimiter | None = None
        self.cost_tracker: CostTracker | None = None
        self.tokenizer: Encoding | None = None
        self._dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

    async def initialize(self) -> None:
        """Initialize OpenAI client and resources."""
        if self.client:
            return

        # Initialize client
        try:
            self.client = AsyncOpenAI(
                api_key=self.config.api_key,
                organization=self.config.organization,
                timeout=self.config.timeout,
            )
        except (ValueError, TypeError) as e:
            msg = f"Failed to initialize OpenAI client: {e}"
            raise EmbeddingError(msg) from e

        # Initialize rate limiter
        self.rate_limiter = AdaptiveRateLimiter(
            requests_per_minute=self.config.rate_limit_rpm,
            tokens_per_minute=self.config.rate_limit_tpm,
        )

        # Initialize cost tracker
        self.cost_tracker = CostTracker(model=self.config.model)

        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.config.model)
        except (KeyError, ValueError):
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not self.tokenizer:
            # Fallback: rough estimate
            return int(len(text.split()) * 1.3)
        try:
            return len(self.tokenizer.encode(text))
        except (UnicodeDecodeError, ValueError):
            # Fallback: rough estimate (encoding failure)
            return int(len(text.split()) * 1.3)

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _embed_with_retry(self, texts: list[str]) -> tuple[list[list[float]], int]:
        """
        Generate embeddings with exponential backoff retry.

        Args:
            texts: List of texts to embed

        Returns:
            Tuple of (embeddings, tokens_used)

        Raises:
            EmbeddingError: If embedding generation fails after retries
        """
        if not self.rate_limiter or not self.client:
            raise RuntimeError("Provider not initialized")

        try:
            # Count tokens for rate limiting
            total_tokens = sum(self._count_tokens(text) for text in texts)

            # Acquire rate limit tokens
            await self.rate_limiter.acquire(request_count=1, token_count=total_tokens)

            # Call OpenAI API
            response = await self.client.embeddings.create(
                model=self.config.model,
                input=texts,
            )

            # Extract embeddings
            embeddings = [item.embedding for item in response.data]

            # Get actual token usage
            actual_tokens = response.usage.total_tokens

            # Report success to rate limiter
            self.rate_limiter.report_success()

        except RateLimitError as e:
            # Report rate limit error to adaptive rate limiter
            self.rate_limiter.report_rate_limit_error()
            logger.warning(f"Rate limit hit, backing off: {e}")
            raise  # tenacity will retry

        except (APIConnectionError, APITimeoutError) as e:
            logger.warning(f"Transient API error, retrying: {e}")
            raise  # tenacity will retry

        except (ValueError, RuntimeError, OSError) as e:
            # User-friendly error message with context (intentionally detailed)
            msg = f"Failed to generate embeddings with OpenAI: {e}"
            raise EmbeddingError(msg) from e

        else:
            return embeddings, actual_tokens

    def embed_text(
        self, text: str, instruction_type: InstructionType = InstructionType.NL2CODE_QUERY
    ) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            instruction_type: Not used (OpenAI embeddings don't support instruction types)

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        # Run async method in sync context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, enable nested event loops
            _apply_nest_asyncio()

        try:
            embeddings, tokens = loop.run_until_complete(self._embed_with_retry([text]))

            # Track cost
            if self.cost_tracker:
                self.cost_tracker.record(tokens)

            return embeddings[0]

        except (RuntimeError, ValueError, OSError) as e:
            msg = f"Failed to embed text: {e}"
            raise EmbeddingError(msg) from e

    async def embed_stream(
        self,
        chunks: AsyncGenerator[list[str], None],
        *,
        progress: object = None,
    ) -> AsyncGenerator[list[list[float]], None]:
        """Stream embeddings for chunks of texts.

        Args:
            chunks: Async generator yielding batches of texts
            progress: Optional progress callback

        Yields:
            Embedding vectors for each batch

        Raises:
            EmbeddingError: If embedding generation fails
        """
        batch_idx = 0
        async for batch in chunks:
            if not batch:
                yield []
                continue

            try:
                if progress and hasattr(progress, "on_batch_start"):
                    progress.on_batch_start(batch_idx, len(batch))

                # Calculate token count for rate limiting
                total_tokens = sum(self._count_tokens(text) for text in batch)
                if self.rate_limiter:
                    await self.rate_limiter.acquire(request_count=1, token_count=total_tokens)

                embeddings, tokens = await self._embed_with_retry(batch)
                if self.cost_tracker:
                    self.cost_tracker.record(tokens)

                if progress and hasattr(progress, "on_batch_complete"):
                    progress.on_batch_complete(batch_idx, len(embeddings))

                batch_idx += 1
                yield embeddings

            except (RuntimeError, ValueError, OSError) as e:
                logger.exception("OpenAI API error")
                msg = f"Failed to generate embeddings: {e}"
                raise EmbeddingError(msg) from e

    def get_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            Embedding dimension
        """
        return self._dimensions.get(self.config.model, 1536)

    def get_batch_size(self) -> int:
        """
        Get the optimal batch size for this provider.

        Returns:
            Configured batch size from OpenAIConfig
        """
        return self.config.batch_size

    def get_cost_summary(self) -> dict[str, Any]:
        """
        Get cost tracking summary.

        Returns:
            Dictionary with cost statistics
        """
        if not self.cost_tracker:
            return {}
        return self.cost_tracker.get_summary()

    def get_rate_limit_stats(self) -> dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with rate limit statistics
        """
        if not self.rate_limiter:
            return {}
        return self.rate_limiter.get_stats()

    def estimate_cost(self, texts: list[str]) -> tuple[int, float]:
        """
        Estimate cost for embedding texts.

        Args:
            texts: List of texts to estimate

        Returns:
            Tuple of (estimated_tokens, estimated_cost_usd)
        """
        if not self.cost_tracker:
            return (0, 0.0)
        return self.cost_tracker.estimate_cost(texts, model=self.config.model)

    async def cleanup(self) -> None:
        """Clean up resources (no-op for OpenAI)."""
        pass

    def __enter__(self) -> "OpenAIEmbeddingProvider":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        # Print final cost summary
        summary = self.get_cost_summary()
        logger.info(f"OpenAI Embedding Cost Summary: {summary}")
