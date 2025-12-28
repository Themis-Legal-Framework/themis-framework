"""Integration tests for orchestrator service persistence."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from orchestrator.service import OrchestratorService
from orchestrator.storage.sqlite_repository import SQLiteOrchestratorStateRepository


class DummyAgent:
    """Minimal agent implementation for testing."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def run(self, matter: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {"agent": self.name}
        if self.name == "lda":
            payload["facts"] = {
                "fact_pattern_summary": ["Collision at Mission & 5th"],
                "timeline": [
                    {"date": "2024-03-14", "description": "Collision"},
                ],
            }
            payload["damages"] = {"medical": 12000}
        elif self.name == "dea":
            payload["legal_analysis"] = {
                "issues": ["Negligence"],
                "analysis": "Duty, breach, causation, damages satisfied.",
            }
            payload["authorities"] = {
                "controlling_authorities": ["Palsgraf v. Long Island R.R."],
                "contrary_authorities": ["Doe v. Transit Co."],
            }
        elif self.name == "lsa":
            payload["draft"] = {
                "client_safe_summary": "We have strong liability arguments.",
                "next_steps": ["Prepare demand letter"],
            }
        elif self.name == "dda":
            payload["document"] = {
                "full_text": "Sample legal document content.",
                "word_count": 100,
            }
            payload["metadata"] = {
                "document_type": "complaint",
                "jurisdiction": "federal",
            }
        return payload


class RecordingAgent:
    """Agent that records the received matter payload for assertions."""

    def __init__(self, name: str, producer: Callable[[dict[str, Any]], dict[str, Any]]):
        self.name = name
        self._producer = producer
        self.seen_inputs: list[dict[str, Any]] = []

    async def run(self, matter: dict[str, Any]) -> dict[str, Any]:
        self.seen_inputs.append(matter)
        payload = self._producer(matter) or {}
        payload.setdefault("agent", self.name)
        return payload


@pytest.fixture
def dummy_agents() -> dict[str, DummyAgent]:
    return {name: DummyAgent(name) for name in ("lda", "dea", "lsa", "dda")}


def test_plan_and_execution_are_persisted(tmp_path, dummy_agents):
    database_url = f"sqlite:///{tmp_path/'orchestrator.db'}"
    repository = SQLiteOrchestratorStateRepository(database_url=database_url)
    service = OrchestratorService(agents=dummy_agents, repository=repository)

    matter = {
        "summary": "Test case for persistence validation",
        "parties": ["Plaintiff", "Defendant"],
        "documents": [{"title": "Evidence", "content": "Test content", "date": "2024-01-01"}],
    }
    plan = asyncio.run(service.plan(matter))
    plan_id = plan["plan_id"]

    phases = [step["phase"] for step in plan["steps"]]
    assert phases == [
        "intake_facts",
        "issue_framing",
        "research_retrieval",
        "application_analysis",
        "draft_review",
        "document_assembly",
    ]
    assert any(step.get("supporting_agents") for step in plan["steps"])

    execution = asyncio.run(service.execute(plan_id=plan_id))
    assert execution["status"] == "complete"
    for step in execution["steps"]:
        assert "phase" in step
    assert set(execution["artifacts"]) == {"lda", "dea", "lsa", "dda"}

    reloaded_service = OrchestratorService(
        agents=dummy_agents,
        repository=SQLiteOrchestratorStateRepository(database_url=database_url),
    )

    stored_plan = asyncio.run(reloaded_service.get_plan(plan_id))
    assert stored_plan["plan_id"] == plan_id
    artifacts = asyncio.run(reloaded_service.get_artifacts(plan_id))
    assert set(artifacts) == set(execution["artifacts"])


def test_execute_passes_expected_artifacts_between_agents(tmp_path):
    database_url = f"sqlite:///{tmp_path/'orchestrator.db'}"

    lda_agent = RecordingAgent(
        "lda",
        lambda _: {
            "facts": {
                "fact_pattern_summary": ["Collision occurred at Mission & 5th"],
                "timeline": [
                    {"date": "2024-03-14", "description": "Collision"},
                ],
            }
        },
    )

    def dea_payload(matter: dict[str, Any]) -> dict[str, Any]:
        facts = matter.get("facts") if isinstance(matter.get("facts"), dict) else {}
        summary = facts.get("fact_pattern_summary", []) if isinstance(facts, dict) else []
        return {
            "legal_analysis": {
                "issues": summary,
                "analysis": "Negligence is supported by eyewitness statements.",
            },
            "authorities": {
                "controlling_authorities": ["Smith v. Main St."],
                "contrary_authorities": ["Johnson v. Main St."],
            },
        }

    dea_agent = RecordingAgent("dea", dea_payload)

    def lsa_payload(matter: dict[str, Any]) -> dict[str, Any]:
        analysis = (
            matter.get("legal_analysis")
            if isinstance(matter.get("legal_analysis"), dict)
            else {}
        )
        issues = analysis.get("issues", []) if isinstance(analysis, dict) else []
        return {
            "strategy": {
                "recommended_actions": ["Draft demand letter"],
                "negotiation_positions": {"opening": "$150,000"},
                "contingencies": ["File complaint"],
                "risk_assessment": {"unknowns": [], "issues_included": issues},
            },
            "draft": {
                "client_safe_summary": "We should open at $150,000 while citing Smith.",
                "next_steps": ["Confirm medical specials"],
            },
        }

    lsa_agent = RecordingAgent("lsa", lsa_payload)

    def dda_payload(matter: dict[str, Any]) -> dict[str, Any]:
        return {
            "document": {
                "full_text": "Sample legal document content.",
                "word_count": 100,
            },
            "metadata": {
                "document_type": "complaint",
                "jurisdiction": "federal",
            },
        }

    dda_agent = RecordingAgent("dda", dda_payload)

    service = OrchestratorService(
        agents={"lda": lda_agent, "dea": dea_agent, "lsa": lsa_agent, "dda": dda_agent},
        repository=SQLiteOrchestratorStateRepository(database_url=database_url),
    )

    matter = {
        "summary": "Test case for artifact propagation",
        "parties": ["Plaintiff", "Defendant"],
        "documents": [{"title": "Evidence", "content": "Test content", "date": "2024-01-01"}],
    }
    execution = asyncio.run(service.execute(matter=matter))

    assert execution["status"] == "complete"

    assert lda_agent.seen_inputs
    # LDA receives validated matter (may have normalized fields)
    assert lda_agent.seen_inputs[0]["summary"] == matter["summary"]

    assert dea_agent.seen_inputs, "DEA agent should have received input"
    dea_input = dea_agent.seen_inputs[0]
    assert "facts" in dea_input
    assert dea_input["facts"]["fact_pattern_summary"] == [
        "Collision occurred at Mission & 5th"
    ]

    assert lsa_agent.seen_inputs, "LSA agent should have received input"
    lsa_inputs = [payload for payload in lsa_agent.seen_inputs if "legal_analysis" in payload]
    assert lsa_inputs, "LSA agent should receive propagated legal analysis"
    assert lsa_inputs[0]["legal_analysis"]["issues"] == [
        "Collision occurred at Mission & 5th"
    ]

    # Artifacts should still be persisted under agent names for compatibility.
    assert set(execution["artifacts"].keys()) == {"lda", "dea", "lsa", "dda"}
    assert execution["artifacts"]["dea"]["legal_analysis"]["issues"] == [
        "Collision occurred at Mission & 5th"
    ]


def test_missing_plan_raises_error(tmp_path, dummy_agents):
    from orchestrator.exceptions import ExecutionNotFoundError, PlanNotFoundError

    database_url = f"sqlite:///{tmp_path/'orchestrator.db'}"
    service = OrchestratorService(
        agents=dummy_agents,
        repository=SQLiteOrchestratorStateRepository(database_url=database_url),
    )

    with pytest.raises(PlanNotFoundError):
        asyncio.run(service.get_plan("unknown-plan"))

    with pytest.raises(ExecutionNotFoundError):
        asyncio.run(service.get_artifacts("unknown-plan"))
