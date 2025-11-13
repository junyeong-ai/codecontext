"""Token bucket rate limiter for OpenAI API calls."""

import asyncio
import time
from typing import Any


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for OpenAI API requests.

    Implements dual rate limiting:
    - Requests per minute (RPM)
    - Tokens per minute (TPM)

    Uses token bucket algorithm with smooth refilling.
    """

    def __init__(
        self,
        requests_per_minute: int = 3000,
        tokens_per_minute: int = 1000000,
    ) -> None:
        """
        Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            tokens_per_minute: Maximum tokens per minute
        """
        # Request bucket
        self.request_capacity = requests_per_minute
        self.request_tokens = float(requests_per_minute)
        self.request_refill_rate = requests_per_minute / 60.0  # per second

        # Token bucket
        self.token_capacity = tokens_per_minute
        self.token_tokens = float(tokens_per_minute)
        self.token_refill_rate = tokens_per_minute / 60.0  # per second

        # Tracking
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        """Refill buckets based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Refill request bucket
        self.request_tokens = min(
            self.request_capacity,
            self.request_tokens + elapsed * self.request_refill_rate,
        )

        # Refill token bucket
        self.token_tokens = min(
            self.token_capacity,
            self.token_tokens + elapsed * self.token_refill_rate,
        )

        self.last_refill = now

    async def acquire(self, request_count: int = 1, token_count: int = 0) -> None:
        """
        Acquire tokens for a request.

        Blocks until sufficient tokens are available in both buckets.

        Args:
            request_count: Number of requests (usually 1)
            token_count: Number of tokens to consume
        """
        async with self._lock:
            while True:
                self._refill()

                # Check if we have enough tokens in both buckets
                has_request_tokens = self.request_tokens >= request_count
                has_token_tokens = self.token_tokens >= token_count

                if has_request_tokens and has_token_tokens:
                    # Consume tokens
                    self.request_tokens -= request_count
                    self.token_tokens -= token_count
                    return

                # Calculate wait time
                request_wait = 0.0
                token_wait = 0.0

                if not has_request_tokens:
                    needed = request_count - self.request_tokens
                    request_wait = needed / self.request_refill_rate

                if not has_token_tokens:
                    needed = token_count - self.token_tokens
                    token_wait = needed / self.token_refill_rate

                wait_time = max(request_wait, token_wait, 0.1)

                # Release lock while waiting
                await asyncio.sleep(wait_time)

    def get_stats(self) -> dict[str, Any]:
        """
        Get current rate limiter statistics.

        Returns:
            Dictionary with current token counts and capacities
        """
        self._refill()
        return {
            "request_tokens": self.request_tokens,
            "request_capacity": self.request_capacity,
            "token_tokens": self.token_tokens,
            "token_capacity": self.token_capacity,
            "request_utilization": 1.0 - (self.request_tokens / self.request_capacity),
            "token_utilization": 1.0 - (self.token_tokens / self.token_capacity),
        }


class AdaptiveRateLimiter(TokenBucketRateLimiter):
    """
    Adaptive rate limiter that adjusts limits based on API responses.

    Reduces limits when rate limit errors occur and gradually recovers.
    """

    def __init__(
        self,
        requests_per_minute: int = 3000,
        tokens_per_minute: int = 1000000,
        min_factor: float = 0.5,
    ) -> None:
        """
        Initialize the adaptive rate limiter.

        Args:
            requests_per_minute: Initial maximum requests per minute
            tokens_per_minute: Initial maximum tokens per minute
            min_factor: Minimum factor to reduce to (0.5 = 50% of original)
        """
        super().__init__(requests_per_minute, tokens_per_minute)
        self.base_request_capacity = requests_per_minute
        self.base_token_capacity = tokens_per_minute
        self.min_factor = min_factor
        self.current_factor = 1.0

    def report_rate_limit_error(self) -> None:
        """Report a rate limit error to trigger backoff."""
        # Reduce capacity by 50%
        self.current_factor = max(self.min_factor, self.current_factor * 0.5)
        self._update_capacities()

    def report_success(self) -> None:
        """Report a successful request to gradually recover."""
        # Gradually increase capacity by 10%
        self.current_factor = min(1.0, self.current_factor * 1.1)
        self._update_capacities()

    def _update_capacities(self) -> None:
        """Update bucket capacities based on current factor."""
        self.request_capacity = int(self.base_request_capacity * self.current_factor)
        self.token_capacity = int(self.base_token_capacity * self.current_factor)

        # Cap current tokens to new capacity
        self.request_tokens = min(self.request_tokens, self.request_capacity)
        self.token_tokens = min(self.token_tokens, self.token_capacity)
