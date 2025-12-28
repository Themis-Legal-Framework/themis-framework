from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from orchestrator import router


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
