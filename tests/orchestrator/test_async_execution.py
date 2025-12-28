"""Tests for async execution functionality."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.async_execution import (
    AsyncExecutionManager,
    AsyncJob,
    JobStatus,
    WebhookConfig,
)


class TestWebhookConfig:
    """Tests for WebhookConfig."""

    def test_default_values(self) -> None:
        config = WebhookConfig(url="https://example.com/webhook")
        assert config.url == "https://example.com/webhook"
        assert config.headers == {}
        assert config.timeout_seconds == 30.0
        assert config.retry_count == 3

    def test_custom_values(self) -> None:
        config = WebhookConfig(
            url="https://example.com/webhook",
            headers={"Authorization": "Bearer token"},
            timeout_seconds=10.0,
            retry_count=5,
        )
        assert config.headers == {"Authorization": "Bearer token"}
        assert config.timeout_seconds == 10.0
        assert config.retry_count == 5


class TestAsyncJob:
    """Tests for AsyncJob."""

    def test_default_values(self) -> None:
        job = AsyncJob(job_id="job-123", plan_id="plan-456")
        assert job.job_id == "job-123"
        assert job.plan_id == "plan-456"
        assert job.status == JobStatus.PENDING
        assert job.result is None
        assert job.error is None

    def test_to_dict(self) -> None:
        job = AsyncJob(
            job_id="job-123",
            plan_id="plan-456",
            status=JobStatus.COMPLETED,
            result={"artifacts": {}},
        )
        result = job.to_dict()

        assert result["job_id"] == "job-123"
        assert result["plan_id"] == "plan-456"
        assert result["status"] == "completed"
        assert result["has_result"] is True


class TestAsyncExecutionManager:
    """Tests for AsyncExecutionManager."""

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        service = MagicMock()
        service.execute = AsyncMock(return_value={"status": "complete", "artifacts": {}})
        return service

    @pytest.fixture
    def manager(self, mock_service: MagicMock) -> AsyncExecutionManager:
        return AsyncExecutionManager(mock_service, max_concurrent_jobs=5)

    @pytest.mark.asyncio
    async def test_start_async_creates_job(
        self, manager: AsyncExecutionManager
    ) -> None:
        job = await manager.start_async("plan-123")

        assert job.job_id is not None
        assert job.plan_id == "plan-123"
        assert job.status in (JobStatus.PENDING, JobStatus.RUNNING, JobStatus.COMPLETED)

        # Wait for job to complete
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_start_async_with_webhook(
        self, manager: AsyncExecutionManager
    ) -> None:
        webhook = WebhookConfig(url="https://example.com/callback")
        job = await manager.start_async("plan-123", webhook=webhook)

        assert job.webhook is not None
        assert job.webhook.url == "https://example.com/callback"

        # Wait for job to complete
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_job_completes_successfully(
        self, manager: AsyncExecutionManager, mock_service: MagicMock
    ) -> None:
        job = await manager.start_async("plan-123")

        # Wait for execution to complete
        await asyncio.sleep(0.1)

        # Refresh job status
        updated_job = manager.get_job(job.job_id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.result is not None
        assert updated_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_job_fails_on_error(
        self, manager: AsyncExecutionManager, mock_service: MagicMock
    ) -> None:
        mock_service.execute = AsyncMock(side_effect=RuntimeError("Execution failed"))

        job = await manager.start_async("plan-123")

        # Wait for execution to complete
        await asyncio.sleep(0.1)

        updated_job = manager.get_job(job.job_id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.FAILED
        assert updated_job.error == "Execution failed"

    @pytest.mark.asyncio
    async def test_get_job_returns_none_for_unknown(
        self, manager: AsyncExecutionManager
    ) -> None:
        job = manager.get_job("unknown-job-id")
        assert job is None

    @pytest.mark.asyncio
    async def test_get_job_result_returns_result_when_complete(
        self, manager: AsyncExecutionManager
    ) -> None:
        job = await manager.start_async("plan-123")

        # Wait for completion
        await asyncio.sleep(0.1)

        result = manager.get_job_result(job.job_id)
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_get_job_result_returns_none_when_pending(
        self, manager: AsyncExecutionManager, mock_service: MagicMock
    ) -> None:
        # Make execution take longer
        async def slow_execute(**kwargs: object) -> dict:
            await asyncio.sleep(1.0)
            return {"status": "complete"}

        mock_service.execute = slow_execute

        job = await manager.start_async("plan-123")

        # Immediately check (before completion)
        result = manager.get_job_result(job.job_id)
        assert result is None

        # Cancel to clean up
        await manager.cancel_job(job.job_id)

    @pytest.mark.asyncio
    async def test_cancel_job(
        self, manager: AsyncExecutionManager, mock_service: MagicMock
    ) -> None:
        # Make execution take longer
        async def slow_execute(**kwargs: object) -> dict:
            await asyncio.sleep(5.0)
            return {"status": "complete"}

        mock_service.execute = slow_execute

        job = await manager.start_async("plan-123")

        # Cancel immediately
        cancelled = await manager.cancel_job(job.job_id)
        assert cancelled is True

        updated_job = manager.get_job(job.job_id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_unknown_job_returns_false(
        self, manager: AsyncExecutionManager
    ) -> None:
        cancelled = await manager.cancel_job("unknown-job-id")
        assert cancelled is False

    @pytest.mark.asyncio
    async def test_list_jobs(self, manager: AsyncExecutionManager) -> None:
        await manager.start_async("plan-1")
        await manager.start_async("plan-2")
        await manager.start_async("plan-3")

        # Wait for completion
        await asyncio.sleep(0.1)

        jobs = manager.list_jobs()
        assert len(jobs) == 3

    @pytest.mark.asyncio
    async def test_list_jobs_with_status_filter(
        self, manager: AsyncExecutionManager, mock_service: MagicMock
    ) -> None:
        # Create a completed job
        await manager.start_async("plan-1")
        await asyncio.sleep(0.1)

        # Create a failing job
        mock_service.execute = AsyncMock(side_effect=RuntimeError("fail"))
        await manager.start_async("plan-2")
        await asyncio.sleep(0.1)

        completed_jobs = manager.list_jobs(status=JobStatus.COMPLETED)
        failed_jobs = manager.list_jobs(status=JobStatus.FAILED)

        assert len(completed_jobs) == 1
        assert len(failed_jobs) == 1

    @pytest.mark.asyncio
    async def test_cleanup_old_jobs(
        self, manager: AsyncExecutionManager
    ) -> None:
        job = await manager.start_async("plan-123")
        await asyncio.sleep(0.1)

        # Force job to be old
        updated_job = manager.get_job(job.job_id)
        if updated_job:
            updated_job.completed_at = datetime(2020, 1, 1, tzinfo=UTC)

        removed = manager.cleanup_old_jobs(max_age_seconds=1)
        assert removed == 1
        assert manager.get_job(job.job_id) is None

    @pytest.mark.asyncio
    async def test_get_stats(self, manager: AsyncExecutionManager) -> None:
        await manager.start_async("plan-1")
        await asyncio.sleep(0.1)

        stats = manager.get_stats()
        assert "total" in stats
        assert stats["total"] == 1
        assert stats["completed"] == 1

    @pytest.mark.asyncio
    async def test_webhook_called_on_completion(
        self, manager: AsyncExecutionManager
    ) -> None:
        webhook = WebhookConfig(url="https://example.com/callback")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            _job = await manager.start_async("plan-123", webhook=webhook)
            await asyncio.sleep(0.1)

            # Verify webhook was called
            mock_client.return_value.__aenter__.return_value.post.assert_called()

    @pytest.mark.asyncio
    async def test_concurrent_job_limit(
        self, mock_service: MagicMock
    ) -> None:
        manager = AsyncExecutionManager(mock_service, max_concurrent_jobs=2)

        # Make execution take some time
        async def slow_execute(**kwargs: object) -> dict:
            await asyncio.sleep(0.5)
            return {"status": "complete"}

        mock_service.execute = slow_execute

        # Start 5 jobs
        jobs = []
        for i in range(5):
            job = await manager.start_async(f"plan-{i}")
            jobs.append(job)

        await asyncio.sleep(0.1)

        # Check that only 2 are running at a time (others pending or completed)
        running = sum(1 for j in manager.list_jobs() if j.status == JobStatus.RUNNING)
        assert running <= 2

        # Cancel all to clean up
        for job in jobs:
            await manager.cancel_job(job.job_id)
