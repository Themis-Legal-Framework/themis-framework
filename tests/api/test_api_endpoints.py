from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from orchestrator import router


from collections.abc import AsyncGenerator


class StubOrchestratorService:
    def __init__(self) -> None:
        self.plans: dict[str, dict[str, object]] = {}
        self.artifacts: dict[str, dict[str, object]] = {}
        self.plan_invocations: list[dict[str, object]] = []
        self.execute_invocations: list[dict[str, object | None]] = []

    async def plan(self, matter: dict[str, object]) -> dict[str, object]:
        plan_id = f"plan-{len(self.plans) + 1}"
        payload = {"plan_id": plan_id, "status": "planned", "matter": matter}
        self.plans[plan_id] = payload
        self.plan_invocations.append(matter)
        return payload

    async def execute(
        self, *, plan_id: str | None = None, matter: dict[str, object] | None = None
    ) -> dict[str, object]:
        self.execute_invocations.append({"plan_id": plan_id, "matter": matter})
        if plan_id and plan_id not in self.plans:
            raise ValueError("Plan not found")
        chosen_plan_id = plan_id or f"plan-{len(self.plans) + 1}"
        result = {
            "plan_id": chosen_plan_id,
            "status": "completed",
            "artifacts": {"documents": []},
        }
        self.artifacts[chosen_plan_id] = result["artifacts"]
        return result

    async def execute_stream(
        self, *, plan_id: str | None = None, matter: dict[str, object] | None = None
    ) -> AsyncGenerator[dict[str, object], None]:
        """Stream execution progress events."""
        self.execute_invocations.append({"plan_id": plan_id, "matter": matter})
        if plan_id and plan_id not in self.plans:
            raise ValueError("Plan not found")
        chosen_plan_id = plan_id or f"plan-{len(self.plans) + 1}"

        # Yield progress events
        yield {"stage": "plan_created", "plan_id": chosen_plan_id}
        yield {"stage": "agent_started", "agent": "lda", "step": 1, "total_steps": 2}
        yield {"stage": "agent_completed", "agent": "lda", "step": 1, "total_steps": 2}
        yield {"stage": "agent_started", "agent": "dda", "step": 2, "total_steps": 2}
        yield {"stage": "agent_completed", "agent": "dda", "step": 2, "total_steps": 2}
        yield {
            "stage": "execution_complete",
            "status": "complete",
            "plan_id": chosen_plan_id,
            "artifacts_count": 2,
        }

        self.artifacts[chosen_plan_id] = {"documents": []}

    async def get_plan(self, plan_id: str) -> dict[str, object]:
        if plan_id not in self.plans:
            raise ValueError("Plan not found")
        return self.plans[plan_id]

    async def get_artifacts(self, plan_id: str) -> dict[str, object]:
        if plan_id not in self.artifacts:
            raise ValueError("Artifacts not found")
        return self.artifacts[plan_id]


@pytest.fixture
def stub_service(monkeypatch: pytest.MonkeyPatch) -> StubOrchestratorService:
    service = StubOrchestratorService()
    monkeypatch.setattr("api.main.OrchestratorService", lambda: service)
    monkeypatch.setattr("orchestrator.router.OrchestratorService", lambda: service)
    router.configure_service(service)
    return service


@pytest.fixture
def api_client(stub_service: StubOrchestratorService) -> TestClient:
    with TestClient(app) as client:
        yield client


def test_health_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_liveness_probe(api_client: TestClient) -> None:
    response = api_client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_probe(api_client: TestClient) -> None:
    response = api_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "uptime_seconds" in data
    assert "checks" in data
    assert data["checks"]["orchestrator"] is True


def test_metrics_endpoint_returns_prometheus_payload(api_client: TestClient) -> None:
    response = api_client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# HELP" in response.text


def test_plan_endpoint_sanitises_payload(api_client: TestClient, stub_service: StubOrchestratorService) -> None:
    payload = {
        "matter": {
            "summary": "Valid <script>alert('x')</script> matter",
            "parties": ["Alice", "Bob"],
            "documents": [
                {
                    "title": "Complaint",
                    "summary": "Complaint summary",
                    "date": "2024-01-01",
                }
            ],
        }
    }

    response = api_client.post("/orchestrator/plan", json=payload)
    assert response.status_code == 200
    recorded = stub_service.plan_invocations[-1]
    assert "<script" not in recorded["summary"]
    assert "alert" not in recorded["summary"]


def test_execute_endpoint_requires_payload(api_client: TestClient) -> None:
    response = api_client.post("/orchestrator/execute", json={})
    assert response.status_code == 400


def test_execute_endpoint_returns_results(api_client: TestClient, stub_service: StubOrchestratorService) -> None:
    plan_payload = {
        "matter": {
            "summary": "Another valid summary",
            "parties": ["Alice", "Bob"],
            "documents": [
                {
                    "title": "Complaint",
                    "summary": "Complaint summary",
                    "date": "2024-01-01",
                }
            ],
        }
    }
    plan_response = api_client.post("/orchestrator/plan", json=plan_payload)
    plan_id = plan_response.json()["plan_id"]

    exec_response = api_client.post("/orchestrator/execute", json={"plan_id": plan_id})
    assert exec_response.status_code == 200
    assert exec_response.json()["status"] == "completed"

    artifacts_response = api_client.get(f"/orchestrator/artifacts/{plan_id}")
    assert artifacts_response.status_code == 200


def test_get_plan_handles_missing_plan(api_client: TestClient) -> None:
    response = api_client.get("/orchestrator/plans/unknown")
    assert response.status_code == 404


def test_execute_stream_returns_sse_events(api_client: TestClient, stub_service: StubOrchestratorService) -> None:
    """Test that streaming endpoint returns SSE-formatted events."""
    # First create a plan
    plan_payload = {
        "matter": {
            "summary": "Streaming test matter",
            "parties": ["Alice", "Bob"],
            "documents": [
                {
                    "title": "Complaint",
                    "summary": "Complaint summary",
                    "date": "2024-01-01",
                }
            ],
        }
    }
    plan_response = api_client.post("/orchestrator/plan", json=plan_payload)
    plan_id = plan_response.json()["plan_id"]

    # Execute with streaming
    with api_client.stream(
        "POST",
        "/orchestrator/execute/stream",
        json={"plan_id": plan_id}
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Collect all events
        events = []
        for line in response.iter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())

        # Verify we got the expected event types
        assert "start" in events
        assert "agent_started" in events
        assert "agent_completed" in events
        assert "complete" in events


def test_execute_stream_requires_payload(api_client: TestClient) -> None:
    """Test that streaming endpoint requires plan_id or matter."""
    response = api_client.post("/orchestrator/execute/stream", json={})
    assert response.status_code == 400


def test_execute_stream_with_matter_payload(api_client: TestClient, stub_service: StubOrchestratorService) -> None:
    """Test streaming with inline matter payload (no prior plan)."""
    payload = {
        "matter": {
            "summary": "Direct streaming matter",
            "parties": ["Client", "Defendant"],
            "documents": [
                {
                    "title": "Contract",
                    "summary": "Contract summary",
                    "date": "2024-01-15",
                }
            ],
        }
    }

    with api_client.stream(
        "POST",
        "/orchestrator/execute/stream",
        json=payload
    ) as response:
        assert response.status_code == 200
        content = response.read().decode()
        assert "event: start" in content
        assert "event: complete" in content
