#!/usr/bin/env python3
"""
Production-Grade Resilience Patterns
Implements retry logic, circuit breaker, rate limiting, and backoff strategies.
"""

import asyncio
import time
import random
from typing import Optional, Callable, Any, TypeVar, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from functools import wraps
import logging

from .exceptions import (
    RetryExhaustedError,
    CircuitBreakerError,
    RateLimitError,
    TimeoutError as KimiTimeoutError
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # failures before opening
    success_threshold: int = 2  # successes to close from half-open
    timeout: float = 60.0  # seconds before attempting half-open
    exclude_exceptions: tuple = ()  # exceptions that don't count as failures


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 100  # max requests
    time_window: float = 60.0  # time window in seconds
    burst_size: Optional[int] = None  # allow bursts


class ExponentialBackoff:
    """
    Implements exponential backoff with jitter.

    This prevents thundering herd problem where many clients retry simultaneously.
    """

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.attempt = 0

    def get_delay(self) -> float:
        """Calculate delay for current attempt."""
        delay = min(
            self.initial_delay * (self.exponential_base ** self.attempt),
            self.max_delay
        )

        if self.jitter:
            # Add randomness: delay * [0.5, 1.5)
            delay = delay * (0.5 + random.random())

        return delay

    def reset(self):
        """Reset attempt counter."""
        self.attempt = 0

    def increment(self):
        """Increment attempt counter."""
        self.attempt += 1


class CircuitBreaker:
    """
    Implements circuit breaker pattern.

    Prevents cascading failures by failing fast when a service is degraded.
    States: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.open_time: Optional[datetime] = None

        self._lock = asyncio.Lock()

    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self._lock:
            await self._update_state()

            if self.state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    service=self.name,
                    failure_count=self.failure_count,
                    threshold=self.config.failure_threshold
                )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result

        except Exception as e:
            if not isinstance(e, self.config.exclude_exceptions):
                await self._on_failure()
            raise

    async def _update_state(self):
        """Update circuit breaker state based on current conditions."""
        if self.state == CircuitState.OPEN and self.open_time:
            time_since_open = (datetime.now() - self.open_time).total_seconds()
            if time_since_open >= self.config.timeout:
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0

    async def _on_success(self):
        """Handle successful execution."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    logger.info(f"Circuit breaker '{self.name}' closing after {self.success_count} successes")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.open_time = None
            elif self.state == CircuitState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)

    async def _on_failure(self):
        """Handle failed execution."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker '{self.name}' reopening after failure in HALF_OPEN state")
                self.state = CircuitState.OPEN
                self.open_time = datetime.now()

            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    logger.error(
                        f"Circuit breaker '{self.name}' opening after {self.failure_count} failures "
                        f"(threshold: {self.config.failure_threshold})"
                    )
                    self.state = CircuitState.OPEN
                    self.open_time = datetime.now()

    def get_state(self) -> dict:
        """Get current circuit breaker state for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "open_time": self.open_time.isoformat() if self.open_time else None
        }


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for controlling request rates.

    Allows bursts while maintaining average rate limit.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.tokens = self.config.burst_size or self.config.max_requests
        self.max_tokens = self.config.burst_size or self.config.max_requests
        self.refill_rate = self.config.max_requests / self.config.time_window
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens, blocking if necessary.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False if rate limit exceeded
        """
        async with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate

            if wait_time <= 0:
                self.tokens -= tokens
                return True

            return False

    async def wait_for_tokens(self, tokens: int = 1):
        """
        Wait until tokens are available.

        Args:
            tokens: Number of tokens to acquire

        Raises:
            RateLimitError: If wait time exceeds reasonable limits
        """
        while True:
            if await self.acquire(tokens):
                return

            # Calculate wait time
            async with self._lock:
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.refill_rate

            if wait_time > 300:  # 5 minutes max wait
                raise RateLimitError(
                    provider="system",
                    retry_after=int(wait_time),
                    limit_type="token_bucket"
                )

            await asyncio.sleep(min(wait_time, 1.0))

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill

        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now

    def get_state(self) -> dict:
        """Get current rate limiter state."""
        return {
            "tokens_available": self.tokens,
            "max_tokens": self.max_tokens,
            "refill_rate": self.refill_rate,
            "last_refill": self.last_refill
        }


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for automatic retry with exponential backoff.

    Args:
        config: Retry configuration

    Example:
        @with_retry(RetryConfig(max_attempts=5))
        async def fetch_data():
            # Your async function
            pass
    """
    retry_config = config or RetryConfig()

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            backoff = ExponentialBackoff(
                initial_delay=retry_config.initial_delay,
                max_delay=retry_config.max_delay,
                exponential_base=retry_config.exponential_base,
                jitter=retry_config.jitter
            )

            last_exception: Optional[Exception] = None

            for attempt in range(retry_config.max_attempts):
                try:
                    return await func(*args, **kwargs)

                except retry_config.retryable_exceptions as e:
                    last_exception = e

                    if attempt == retry_config.max_attempts - 1:
                        logger.error(
                            f"Retry exhausted for {func.__name__} after {attempt + 1} attempts",
                            exc_info=True
                        )
                        raise RetryExhaustedError(
                            operation=func.__name__,
                            attempts=attempt + 1,
                            last_error=e
                        )

                    delay = backoff.get_delay()
                    logger.warning(
                        f"Attempt {attempt + 1}/{retry_config.max_attempts} failed for {func.__name__}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    await asyncio.sleep(delay)
                    backoff.increment()

            # Should never reach here
            raise RetryExhaustedError(
                operation=func.__name__,
                attempts=retry_config.max_attempts,
                last_error=last_exception or Exception("Unknown error")
            )

        return wrapper
    return decorator


def with_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator for circuit breaker pattern.

    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration

    Example:
        @with_circuit_breaker("openai_api")
        async def call_openai():
            # Your async function
            pass
    """
    breaker = CircuitBreaker(name, config)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await breaker.call(func, *args, **kwargs)

        wrapper.circuit_breaker = breaker  # Attach for monitoring
        return wrapper

    return decorator


def with_rate_limit(config: Optional[RateLimitConfig] = None):
    """
    Decorator for rate limiting.

    Args:
        config: Rate limit configuration

    Example:
        @with_rate_limit(RateLimitConfig(max_requests=100, time_window=60))
        async def api_call():
            # Your async function
            pass
    """
    limiter = TokenBucketRateLimiter(config)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            await limiter.wait_for_tokens()
            return await func(*args, **kwargs)

        wrapper.rate_limiter = limiter  # Attach for monitoring
        return wrapper

    return decorator


def with_timeout(seconds: float):
    """
    Decorator for timeout protection.

    Args:
        seconds: Timeout in seconds

    Example:
        @with_timeout(30.0)
        async def long_operation():
            # Your async function
            pass
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError as e:
                raise KimiTimeoutError(
                    timeout_seconds=seconds,
                    operation=func.__name__,
                    original_error=e
                )

        return wrapper
    return decorator


# Composite decorator for full resilience stack
def resilient(
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_name: Optional[str] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    rate_limit_config: Optional[RateLimitConfig] = None,
    timeout_seconds: Optional[float] = None
):
    """
    Composite decorator applying full resilience stack.

    Order: timeout -> rate_limit -> circuit_breaker -> retry -> function

    Example:
        @resilient(
            retry_config=RetryConfig(max_attempts=3),
            circuit_breaker_name="my_service",
            timeout_seconds=30.0
        )
        async def my_function():
            pass
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        wrapped = func

        # Apply in reverse order (innermost first)
        if retry_config:
            wrapped = with_retry(retry_config)(wrapped)

        if circuit_breaker_name:
            wrapped = with_circuit_breaker(circuit_breaker_name, circuit_breaker_config)(wrapped)

        if rate_limit_config:
            wrapped = with_rate_limit(rate_limit_config)(wrapped)

        if timeout_seconds:
            wrapped = with_timeout(timeout_seconds)(wrapped)

        return wrapped

    return decorator
