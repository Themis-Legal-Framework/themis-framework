"""Tests for circuit breaker functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from orchestrator.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitBreakerRegistry,
    CircuitState,
    get_circuit_breaker,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_values(self) -> None:
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout_seconds == 30.0
        assert config.excluded_exceptions == ()

    def test_custom_values(self) -> None:
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=1,
            timeout_seconds=10.0,
            excluded_exceptions=(ValueError,),
        )
        assert config.failure_threshold == 3
        assert config.success_threshold == 1
        assert config.timeout_seconds == 10.0
        assert config.excluded_exceptions == (ValueError,)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.fixture
    def breaker(self) -> CircuitBreaker:
        return CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=1.0,
            ),
        )

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, breaker: CircuitBreaker) -> None:
        assert breaker.is_closed
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call_passes_through(
        self, breaker: CircuitBreaker
    ) -> None:
        mock_func = AsyncMock(return_value="success")
        result = await breaker.call(mock_func)

        assert result == "success"
        assert mock_func.call_count == 1
        assert breaker.stats.successful_calls == 1
        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_failed_call_increments_failure_count(
        self, breaker: CircuitBreaker
    ) -> None:
        mock_func = AsyncMock(side_effect=RuntimeError("fail"))

        with pytest.raises(RuntimeError):
            await breaker.call(mock_func)

        assert breaker.stats.failed_calls == 1
        assert breaker.stats.consecutive_failures == 1
        assert breaker.is_closed  # Still closed after 1 failure

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold_failures(
        self, breaker: CircuitBreaker
    ) -> None:
        mock_func = AsyncMock(side_effect=RuntimeError("fail"))

        for _ in range(3):  # failure_threshold = 3
            with pytest.raises(RuntimeError):
                await breaker.call(mock_func)

        assert breaker.is_open
        assert breaker.stats.consecutive_failures == 3

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(
        self, breaker: CircuitBreaker
    ) -> None:
        mock_func = AsyncMock(side_effect=RuntimeError("fail"))

        # Trigger circuit to open
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(mock_func)

        assert breaker.is_open

        # Next call should be rejected
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await breaker.call(AsyncMock())

        assert exc_info.value.name == "test"
        assert breaker.stats.rejected_calls == 1

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open_after_timeout(
        self, breaker: CircuitBreaker
    ) -> None:
        import time

        mock_func = AsyncMock(side_effect=RuntimeError("fail"))

        # Trigger circuit to open
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(mock_func)

        assert breaker.is_open

        # Simulate timeout by manipulating _opened_at
        breaker._opened_at = time.time() - 2.0  # 2 seconds ago (timeout is 1.0)

        # This call should trigger half-open transition
        mock_success = AsyncMock(return_value="recovered")
        result = await breaker.call(mock_success)

        assert result == "recovered"
        # After one success in half-open, still need one more
        assert breaker.is_half_open or breaker.is_closed

    @pytest.mark.asyncio
    async def test_circuit_closes_after_success_threshold_in_half_open(
        self, breaker: CircuitBreaker
    ) -> None:
        import time

        mock_fail = AsyncMock(side_effect=RuntimeError("fail"))

        # Trigger circuit to open
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(mock_fail)

        # Simulate timeout
        breaker._opened_at = time.time() - 2.0

        # Success calls in half-open
        mock_success = AsyncMock(return_value="success")
        for _ in range(2):  # success_threshold = 2
            await breaker.call(mock_success)

        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_excluded_exceptions_dont_count_as_failures(
        self, breaker: CircuitBreaker
    ) -> None:
        breaker.config = CircuitBreakerConfig(
            failure_threshold=3,
            excluded_exceptions=(ValueError,),
        )

        mock_func = AsyncMock(side_effect=ValueError("not a failure"))

        for _ in range(5):
            with pytest.raises(ValueError):
                await breaker.call(mock_func)

        # Should still be closed because ValueError is excluded
        assert breaker.is_closed
        assert breaker.stats.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_success_resets_consecutive_failures(
        self, breaker: CircuitBreaker
    ) -> None:
        mock_fail = AsyncMock(side_effect=RuntimeError("fail"))
        mock_success = AsyncMock(return_value="success")

        # Two failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(mock_fail)

        assert breaker.stats.consecutive_failures == 2

        # One success resets count
        await breaker.call(mock_success)

        assert breaker.stats.consecutive_failures == 0
        assert breaker.is_closed

    def test_reset_restores_initial_state(self, breaker: CircuitBreaker) -> None:
        breaker._state = CircuitState.OPEN
        breaker._stats.failed_calls = 10

        breaker.reset()

        assert breaker.is_closed
        assert breaker.stats.failed_calls == 0


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""

    def test_get_or_create_returns_same_instance(self) -> None:
        registry = CircuitBreakerRegistry()

        breaker1 = registry.get_or_create("test")
        breaker2 = registry.get_or_create("test")

        assert breaker1 is breaker2

    def test_get_or_create_uses_custom_config(self) -> None:
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=10)

        breaker = registry.get_or_create("test", config)

        assert breaker.config.failure_threshold == 10

    def test_get_returns_none_for_unknown(self) -> None:
        registry = CircuitBreakerRegistry()

        assert registry.get("unknown") is None

    def test_get_returns_existing_breaker(self) -> None:
        registry = CircuitBreakerRegistry()
        created = registry.get_or_create("test")

        fetched = registry.get("test")

        assert fetched is created

    def test_get_all_stats(self) -> None:
        registry = CircuitBreakerRegistry()
        registry.get_or_create("api1")
        registry.get_or_create("api2")

        stats = registry.get_all_stats()

        assert "api1" in stats
        assert "api2" in stats
        assert stats["api1"]["state"] == "closed"

    def test_reset_all(self) -> None:
        registry = CircuitBreakerRegistry()
        breaker1 = registry.get_or_create("api1")
        breaker2 = registry.get_or_create("api2")

        breaker1._state = CircuitState.OPEN
        breaker2._state = CircuitState.OPEN

        registry.reset_all()

        assert breaker1.is_closed
        assert breaker2.is_closed


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""

    def test_get_circuit_breaker(self) -> None:
        breaker = get_circuit_breaker("global_test")
        assert isinstance(breaker, CircuitBreaker)
        assert breaker.name == "global_test"

    def test_get_circuit_breaker_returns_same_instance(self) -> None:
        breaker1 = get_circuit_breaker("same_test")
        breaker2 = get_circuit_breaker("same_test")
        assert breaker1 is breaker2
