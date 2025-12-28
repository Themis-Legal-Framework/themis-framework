"""Circuit breaker pattern for API resilience.

Prevents cascading failures by monitoring service health and temporarily
stopping requests when a service is unhealthy.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger("themis.orchestrator.circuit_breaker")

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures before opening circuit.
        success_threshold: Number of successes in half-open to close circuit.
        timeout_seconds: How long circuit stays open before half-open.
        excluded_exceptions: Exception types that don't count as failures.
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 30.0
    excluded_exceptions: tuple[type[Exception], ...] = ()


@dataclass
class CircuitStats:
    """Statistics for circuit breaker monitoring.

    Attributes:
        total_calls: Total number of calls made.
        successful_calls: Number of successful calls.
        failed_calls: Number of failed calls.
        rejected_calls: Number of calls rejected due to open circuit.
        last_failure_time: Timestamp of last failure.
        last_success_time: Timestamp of last success.
        consecutive_failures: Current count of consecutive failures.
        consecutive_successes: Current count of consecutive successes.
    """

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreakerOpen(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, name: str, remaining_seconds: float) -> None:
        self.name = name
        self.remaining_seconds = remaining_seconds
        super().__init__(
            f"Circuit breaker '{name}' is open. Retry in {remaining_seconds:.1f}s"
        )


@dataclass
class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    Usage:
        breaker = CircuitBreaker("my_service")

        try:
            result = await breaker.call(my_async_function, arg1, arg2)
        except CircuitBreakerOpen:
            # Handle circuit open (e.g., return cached data, fail fast)
            pass
    """

    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _stats: CircuitStats = field(default_factory=CircuitStats, init=False)
    _opened_at: float | None = field(default=None, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Circuit breaker statistics."""
        return self._stats

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function through the circuit breaker.

        Args:
            func: The async function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The function's return value.

        Raises:
            CircuitBreakerOpen: If the circuit is open.
            Exception: Any exception from the wrapped function.
        """
        async with self._lock:
            self._maybe_transition_to_half_open()

            if self._state == CircuitState.OPEN:
                self._stats.rejected_calls += 1
                remaining = self._time_until_half_open()
                raise CircuitBreakerOpen(self.name, remaining)

        self._stats.total_calls += 1

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as exc:
            if not isinstance(exc, self.config.excluded_exceptions):
                await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            self._stats.successful_calls += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    self._close()

    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self._stats.failed_calls += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._open()
            elif self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self.config.failure_threshold:
                    self._open()

    def _maybe_transition_to_half_open(self) -> None:
        """Check if circuit should transition from open to half-open."""
        if self._state != CircuitState.OPEN:
            return

        if self._opened_at is None:
            return

        elapsed = time.time() - self._opened_at
        if elapsed >= self.config.timeout_seconds:
            self._half_open()

    def _time_until_half_open(self) -> float:
        """Calculate time remaining until circuit transitions to half-open."""
        if self._opened_at is None:
            return 0.0
        elapsed = time.time() - self._opened_at
        remaining = self.config.timeout_seconds - elapsed
        return max(0.0, remaining)

    def _open(self) -> None:
        """Open the circuit."""
        previous = self._state
        self._state = CircuitState.OPEN
        self._opened_at = time.time()
        self._stats.consecutive_successes = 0
        logger.warning(
            "Circuit breaker '%s' opened (was %s, failures=%d)",
            self.name,
            previous.value,
            self._stats.consecutive_failures,
        )

    def _half_open(self) -> None:
        """Transition to half-open state."""
        self._state = CircuitState.HALF_OPEN
        self._stats.consecutive_successes = 0
        self._stats.consecutive_failures = 0
        logger.info("Circuit breaker '%s' half-opened for testing", self.name)

    def _close(self) -> None:
        """Close the circuit."""
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._stats.consecutive_failures = 0
        logger.info(
            "Circuit breaker '%s' closed (service recovered)", self.name
        )

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._stats = CircuitStats()
        logger.info("Circuit breaker '%s' reset", self.name)


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers.

    Usage:
        registry = CircuitBreakerRegistry()
        breaker = registry.get_or_create("llm_api")
        result = await breaker.call(api_call)
    """

    def __init__(self, default_config: CircuitBreakerConfig | None = None) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}
        self._default_config = default_config or CircuitBreakerConfig()
        self._lock = asyncio.Lock()

    def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get an existing circuit breaker or create a new one.

        Args:
            name: Unique identifier for the circuit breaker.
            config: Optional custom configuration.

        Returns:
            The circuit breaker instance.
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                config=config or self._default_config,
            )
        return self._breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        """Get an existing circuit breaker by name."""
        return self._breakers.get(name)

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {
            name: {
                "state": breaker.state.value,
                "total_calls": breaker.stats.total_calls,
                "successful_calls": breaker.stats.successful_calls,
                "failed_calls": breaker.stats.failed_calls,
                "rejected_calls": breaker.stats.rejected_calls,
                "consecutive_failures": breaker.stats.consecutive_failures,
            }
            for name, breaker in self._breakers.items()
        }

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Default registry instance
_default_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
) -> CircuitBreaker:
    """Get or create a circuit breaker from the default registry.

    Args:
        name: Unique identifier for the circuit breaker.
        config: Optional custom configuration.

    Returns:
        The circuit breaker instance.
    """
    return _default_registry.get_or_create(name, config)


def get_all_circuit_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all circuit breakers in the default registry."""
    return _default_registry.get_all_stats()
