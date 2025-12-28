"""Retry policy and utilities for orchestrator agent execution."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger("themis.orchestrator.retry")

T = TypeVar("T")


class BackoffStrategy(Enum):
    """Backoff strategy for retry delays."""

    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


@dataclass(slots=True)
class RetryPolicy:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of attempts (1 = no retries).
        base_delay_seconds: Base delay between retries.
        max_delay_seconds: Maximum delay cap.
        backoff_strategy: How delay increases between retries.
        jitter: Random jitter factor (0-1) to prevent thundering herd.
        retryable_exceptions: Exception types that trigger retry.
    """

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter: float = 0.1
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )

    def compute_delay(self, attempt: int) -> float:
        """Compute delay for a given attempt number (1-indexed).

        Args:
            attempt: The current attempt number (1 for first retry).

        Returns:
            Delay in seconds with optional jitter.
        """
        if self.backoff_strategy == BackoffStrategy.CONSTANT:
            delay = self.base_delay_seconds
        elif self.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay_seconds * attempt
        else:  # EXPONENTIAL
            delay = self.base_delay_seconds * (2 ** (attempt - 1))

        # Apply max cap
        delay = min(delay, self.max_delay_seconds)

        # Apply jitter
        if self.jitter > 0:
            jitter_amount = delay * self.jitter * random.random()
            delay += jitter_amount

        return delay

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an exception should trigger a retry.

        Args:
            exception: The exception that was raised.
            attempt: Current attempt number (1-indexed).

        Returns:
            True if should retry, False otherwise.
        """
        if attempt >= self.max_attempts:
            return False
        return isinstance(exception, self.retryable_exceptions)


@dataclass(slots=True)
class RetryResult:
    """Result of a retry operation.

    Attributes:
        success: Whether the operation ultimately succeeded.
        result: The result value if successful.
        attempts: Number of attempts made.
        last_exception: The last exception if failed.
        exceptions: All exceptions encountered.
    """

    success: bool
    result: Any = None
    attempts: int = 1
    last_exception: Exception | None = None
    exceptions: list[Exception] = field(default_factory=list)


async def retry_async(
    operation: Callable[[], Any],
    policy: RetryPolicy,
    operation_name: str = "operation",
) -> RetryResult:
    """Execute an async operation with retry logic.

    Args:
        operation: The async callable to execute.
        policy: The retry policy to apply.
        operation_name: Name for logging purposes.

    Returns:
        RetryResult with success status and result or exceptions.
    """
    exceptions: list[Exception] = []
    last_exception: Exception | None = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = await operation()
            if attempt > 1:
                logger.info(
                    "%s succeeded on attempt %d/%d",
                    operation_name,
                    attempt,
                    policy.max_attempts,
                )
            return RetryResult(
                success=True,
                result=result,
                attempts=attempt,
                exceptions=exceptions,
            )
        except Exception as exc:
            last_exception = exc
            exceptions.append(exc)

            if policy.should_retry(exc, attempt):
                delay = policy.compute_delay(attempt)
                logger.warning(
                    "%s failed on attempt %d/%d: %s. Retrying in %.2fs...",
                    operation_name,
                    attempt,
                    policy.max_attempts,
                    str(exc),
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "%s failed on attempt %d/%d: %s. No more retries.",
                    operation_name,
                    attempt,
                    policy.max_attempts,
                    str(exc),
                )
                break

    return RetryResult(
        success=False,
        attempts=len(exceptions),
        last_exception=last_exception,
        exceptions=exceptions,
    )


# Default policies for different use cases
DEFAULT_AGENT_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay_seconds=1.0,
    max_delay_seconds=30.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    jitter=0.1,
)

AGGRESSIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    base_delay_seconds=0.5,
    max_delay_seconds=60.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    jitter=0.2,
)

NO_RETRY_POLICY = RetryPolicy(
    max_attempts=1,
)
