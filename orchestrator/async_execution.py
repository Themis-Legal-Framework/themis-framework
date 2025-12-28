"""Async execution support with webhooks and polling.

Enables long-running plan executions to be started asynchronously,
with status polling and optional webhook callbacks.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import httpx

logger = logging.getLogger("themis.orchestrator.async_execution")


class JobStatus(Enum):
    """Status of an async execution job."""

    PENDING = "pending"  # Queued but not started
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"  # Finished with error
    CANCELLED = "cancelled"  # Cancelled by user


@dataclass
class WebhookConfig:
    """Configuration for webhook callbacks.

    Attributes:
        url: The URL to POST results to.
        headers: Optional headers to include (e.g., auth tokens).
        timeout_seconds: HTTP request timeout.
        retry_count: Number of retries on failure.
    """

    url: str
    headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    retry_count: int = 3


@dataclass
class AsyncJob:
    """Represents an async execution job.

    Attributes:
        job_id: Unique identifier for this job.
        plan_id: The plan being executed.
        status: Current job status.
        created_at: When the job was created.
        started_at: When execution started.
        completed_at: When execution finished.
        result: The execution result (if completed).
        error: Error message (if failed).
        webhook: Optional webhook configuration.
    """

    job_id: str
    plan_id: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    webhook: WebhookConfig | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "job_id": self.job_id,
            "plan_id": self.plan_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "has_result": self.result is not None,
        }


class AsyncExecutionManager:
    """Manages async execution jobs with webhook support.

    Usage:
        manager = AsyncExecutionManager(orchestrator_service)

        # Start async execution
        job = await manager.start_async(
            plan_id="plan-123",
            webhook=WebhookConfig(url="https://example.com/callback")
        )

        # Poll for status
        status = manager.get_job(job.job_id)

        # Get result when completed
        if status.status == JobStatus.COMPLETED:
            result = status.result
    """

    def __init__(
        self,
        orchestrator_service: Any,  # Avoid circular import
        max_concurrent_jobs: int = 10,
    ) -> None:
        self._service = orchestrator_service
        self._jobs: dict[str, AsyncJob] = {}
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._lock = asyncio.Lock()

    async def start_async(
        self,
        plan_id: str,
        webhook: WebhookConfig | None = None,
    ) -> AsyncJob:
        """Start an async execution of a plan.

        Args:
            plan_id: The plan to execute.
            webhook: Optional webhook for completion notification.

        Returns:
            The created AsyncJob.
        """
        job = AsyncJob(
            job_id=str(uuid4()),
            plan_id=plan_id,
            webhook=webhook,
        )

        async with self._lock:
            self._jobs[job.job_id] = job

        # Start execution in background
        task = asyncio.create_task(self._execute_job(job))
        self._running_tasks[job.job_id] = task

        logger.info("Started async job %s for plan %s", job.job_id, plan_id)
        return job

    async def _execute_job(self, job: AsyncJob) -> None:
        """Execute a job in the background."""
        async with self._semaphore:
            try:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(UTC)
                logger.info("Executing job %s", job.job_id)

                result = await self._service.execute(plan_id=job.plan_id)

                job.status = JobStatus.COMPLETED
                job.result = result
                job.completed_at = datetime.now(UTC)
                logger.info("Job %s completed successfully", job.job_id)

            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                job.completed_at = datetime.now(UTC)
                logger.error("Job %s failed: %s", job.job_id, exc)

            finally:
                # Send webhook if configured
                if job.webhook:
                    await self._send_webhook(job)

                # Clean up task reference
                self._running_tasks.pop(job.job_id, None)

    async def _send_webhook(self, job: AsyncJob) -> None:
        """Send webhook notification for job completion."""
        if job.webhook is None:
            return

        payload = {
            "event": "execution_complete",
            "job_id": job.job_id,
            "plan_id": job.plan_id,
            "status": job.status.value,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
            "result": job.result if job.status == JobStatus.COMPLETED else None,
        }

        for attempt in range(job.webhook.retry_count):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        job.webhook.url,
                        json=payload,
                        headers=job.webhook.headers,
                        timeout=job.webhook.timeout_seconds,
                    )
                    response.raise_for_status()
                    logger.info(
                        "Webhook sent for job %s (attempt %d)",
                        job.job_id,
                        attempt + 1,
                    )
                    return
            except Exception as exc:
                logger.warning(
                    "Webhook failed for job %s (attempt %d/%d): %s",
                    job.job_id,
                    attempt + 1,
                    job.webhook.retry_count,
                    exc,
                )
                if attempt < job.webhook.retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        logger.error(
            "Webhook exhausted retries for job %s", job.job_id
        )

    def get_job(self, job_id: str) -> AsyncJob | None:
        """Get a job by ID.

        Args:
            job_id: The job ID to look up.

        Returns:
            The AsyncJob if found, None otherwise.
        """
        return self._jobs.get(job_id)

    def get_job_result(self, job_id: str) -> dict[str, Any] | None:
        """Get the result of a completed job.

        Args:
            job_id: The job ID to look up.

        Returns:
            The execution result if job completed, None otherwise.
        """
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.COMPLETED:
            return job.result
        return None

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job.

        Args:
            job_id: The job ID to cancel.

        Returns:
            True if cancelled, False if not found or already complete.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return False

        if job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
            return False

        task = self._running_tasks.get(job_id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(UTC)
        logger.info("Job %s cancelled", job_id)
        return True

    def list_jobs(
        self,
        status: JobStatus | None = None,
        limit: int = 100,
    ) -> list[AsyncJob]:
        """List jobs, optionally filtered by status.

        Args:
            status: Optional status filter.
            limit: Maximum number of jobs to return.

        Returns:
            List of matching jobs.
        """
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by created_at descending (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return jobs[:limit]

    def cleanup_old_jobs(self, max_age_seconds: float = 3600) -> int:
        """Remove completed jobs older than max_age.

        Args:
            max_age_seconds: Maximum age of jobs to keep.

        Returns:
            Number of jobs removed.
        """
        now = datetime.now(UTC)
        to_remove = []

        for job_id, job in self._jobs.items():
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                if job.completed_at:
                    age = (now - job.completed_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(job_id)

        for job_id in to_remove:
            del self._jobs[job_id]

        if to_remove:
            logger.info("Cleaned up %d old jobs", len(to_remove))

        return len(to_remove)

    def get_stats(self) -> dict[str, int]:
        """Get job statistics.

        Returns:
            Dictionary with counts by status.
        """
        stats = {status.value: 0 for status in JobStatus}
        for job in self._jobs.values():
            stats[job.status.value] += 1
        stats["total"] = len(self._jobs)
        return stats
