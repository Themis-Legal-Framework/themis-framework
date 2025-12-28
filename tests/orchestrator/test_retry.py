"""Tests for orchestrator retry functionality."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from orchestrator.retry import (
    DEFAULT_AGENT_RETRY_POLICY,
    NO_RETRY_POLICY,
    BackoffStrategy,
    RetryPolicy,
    retry_async,
)


class TestRetryPolicy:
    """Tests for RetryPolicy configuration."""

    def test_default_policy_values(self) -> None:
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.base_delay_seconds == 1.0
        assert policy.max_delay_seconds == 30.0
        assert policy.backoff_strategy == BackoffStrategy.EXPONENTIAL

    def test_compute_delay_constant(self) -> None:
        policy = RetryPolicy(
            base_delay_seconds=2.0,
            backoff_strategy=BackoffStrategy.CONSTANT,
            jitter=0,
        )
        assert policy.compute_delay(1) == 2.0
        assert policy.compute_delay(2) == 2.0
        assert policy.compute_delay(3) == 2.0

    def test_compute_delay_linear(self) -> None:
        policy = RetryPolicy(
            base_delay_seconds=1.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            jitter=0,
        )
        assert policy.compute_delay(1) == 1.0
        assert policy.compute_delay(2) == 2.0
        assert policy.compute_delay(3) == 3.0

    def test_compute_delay_exponential(self) -> None:
        policy = RetryPolicy(
            base_delay_seconds=1.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            jitter=0,
        )
        assert policy.compute_delay(1) == 1.0
        assert policy.compute_delay(2) == 2.0
        assert policy.compute_delay(3) == 4.0
        assert policy.compute_delay(4) == 8.0

    def test_compute_delay_respects_max(self) -> None:
        policy = RetryPolicy(
            base_delay_seconds=10.0,
            max_delay_seconds=15.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            jitter=0,
        )
        assert policy.compute_delay(1) == 10.0
        assert policy.compute_delay(2) == 15.0  # capped at max
        assert policy.compute_delay(3) == 15.0  # capped at max

    def test_compute_delay_with_jitter(self) -> None:
        policy = RetryPolicy(
            base_delay_seconds=1.0,
            backoff_strategy=BackoffStrategy.CONSTANT,
            jitter=0.5,
        )
        # With jitter, delay should be between 1.0 and 1.5
        for _ in range(10):
            delay = policy.compute_delay(1)
            assert 1.0 <= delay <= 1.5

    def test_should_retry_within_max_attempts(self) -> None:
        policy = RetryPolicy(max_attempts=3)
        assert policy.should_retry(Exception("test"), 1) is True
        assert policy.should_retry(Exception("test"), 2) is True
        assert policy.should_retry(Exception("test"), 3) is False

    def test_should_retry_respects_exception_types(self) -> None:
        policy = RetryPolicy(
            max_attempts=3,
            retryable_exceptions=(ValueError,),
        )
        assert policy.should_retry(ValueError("test"), 1) is True
        assert policy.should_retry(TypeError("test"), 1) is False


class TestRetryAsync:
    """Tests for retry_async function."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self) -> None:
        mock_op = AsyncMock(return_value="success")
        result = await retry_async(mock_op, NO_RETRY_POLICY, "test_op")

        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 1
        assert result.last_exception is None
        assert mock_op.call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retry(self) -> None:
        mock_op = AsyncMock(side_effect=[ValueError("fail"), "success"])
        policy = RetryPolicy(max_attempts=3, base_delay_seconds=0.01, jitter=0)
        result = await retry_async(mock_op, policy, "test_op")

        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 2
        assert len(result.exceptions) == 1
        assert mock_op.call_count == 2

    @pytest.mark.asyncio
    async def test_failure_after_max_attempts(self) -> None:
        mock_op = AsyncMock(side_effect=ValueError("always fails"))
        policy = RetryPolicy(max_attempts=3, base_delay_seconds=0.01, jitter=0)
        result = await retry_async(mock_op, policy, "test_op")

        assert result.success is False
        assert result.result is None
        assert result.attempts == 3
        assert len(result.exceptions) == 3
        assert isinstance(result.last_exception, ValueError)
        assert mock_op.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_exception(self) -> None:
        mock_op = AsyncMock(side_effect=TypeError("not retryable"))
        policy = RetryPolicy(
            max_attempts=3,
            base_delay_seconds=0.01,
            retryable_exceptions=(ValueError,),
        )
        result = await retry_async(mock_op, policy, "test_op")

        assert result.success is False
        assert result.attempts == 1
        assert mock_op.call_count == 1


class TestDefaultPolicies:
    """Tests for pre-defined retry policies."""

    def test_default_agent_policy(self) -> None:
        policy = DEFAULT_AGENT_RETRY_POLICY
        assert policy.max_attempts == 3
        assert policy.backoff_strategy == BackoffStrategy.EXPONENTIAL

    def test_no_retry_policy(self) -> None:
        policy = NO_RETRY_POLICY
        assert policy.max_attempts == 1
        assert policy.should_retry(Exception("test"), 1) is False
