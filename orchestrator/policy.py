"""Routing policy for dynamic agent orchestration with legal phases."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from orchestrator.task_graph import TaskGraph, TaskNode


class Phase(str, Enum):
    """Enumerates the high-level orchestration phases."""

    INTAKE_FACTS = "intake_facts"
    ISSUE_FRAMING = "issue_framing"
    RESEARCH_RETRIEVAL = "research_retrieval"
    APPLICATION_ANALYSIS = "application_analysis"
    DRAFT_REVIEW = "draft_review"
    DOCUMENT_ASSEMBLY = "document_assembly"


@dataclass(slots=True)
class SupportingAgent:
    """Metadata describing a supporting agent for a phase."""

    agent: str
    role: str
    description: str
    expected_artifacts: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Serialize the supporting agent configuration."""

        payload = {
            "agent": self.agent,
            "role": self.role,
            "description": self.description,
        }
        if self.expected_artifacts:
            payload["expected_artifacts"] = self.expected_artifacts
        return payload


@dataclass(slots=True)
class PhaseDefinition:
    """Configuration for a single orchestration phase."""

    phase: Phase
    description: str
    default_primary_agent: str
    expected_artifacts: list[dict[str, Any]] = field(default_factory=list)
    exit_signals: list[str] = field(default_factory=list)
    entry_signals: list[str] = field(default_factory=list)
    supporting_agents: list[SupportingAgent] = field(default_factory=list)
    required_connectors: list[str] = field(default_factory=list)

    def as_plan_step(
        self,
        index: int,
        primary_agent: str,
        matter: dict[str, Any],
        dependencies: list[str],
    ) -> dict[str, Any]:
        """Produce the serialized plan step for this phase."""

        supporting = [s for s in self.supporting_agents if s.agent != primary_agent]
        step_id = f"phase-{index}"
        step = {
            "id": step_id,
            "phase": self.phase.value,
            "agent": primary_agent,
            "description": self.description,
            "status": "pending",
            "inputs": {
                "matter": matter,
                "phase": self.phase.value,
                "dependencies": dependencies,
            },
            "dependencies": dependencies,
            "expected_artifacts": self.expected_artifacts,
        }
        if supporting:
            step["supporting_agents"] = [support.as_dict() for support in supporting]
        if self.exit_signals:
            step["exit_signals"] = self.exit_signals
        if self.entry_signals:
            step["entry_signals"] = self.entry_signals
        if self.required_connectors:
            step["required_connectors"] = self.required_connectors
        return step


class RoutingPolicy:
    """Encapsulates routing rules for the orchestrator."""

    def __init__(self) -> None:
        self._phase_definitions = self._build_phase_definitions()
        self._signal_aliases: dict[str, list[str]] = {
            "facts": ["fact_pattern", "fact_pattern_summary"],
            "issues": ["legal_issues"],
            "controlling_authority": ["controlling_authorities", "authorities"],
            "contrary_authority": ["contrary_authorities", "negative_authority"],
            "application": ["analysis", "application"],
            "draft": ["strategy", "draft"],
            "client_safe_summary": ["client_safe", "client_summary"],
            "document": ["full_text", "formal_document", "legal_document"],
        }

    @property
    def phase_definitions(self) -> list[PhaseDefinition]:
        """Return the configured phase definitions."""

        return list(self._phase_definitions)

    def build_graph(self, matter: dict[str, Any]) -> TaskGraph:
        """Construct a DAG representation of the orchestration plan."""

        graph = TaskGraph()
        previous_id: str | None = None
        for index, definition in enumerate(self._phase_definitions, start=1):
            primary_agent = self.determine_primary_agent(definition.phase, matter)
            dependencies: list[str] = [previous_id] if previous_id else []
            step_payload = definition.as_plan_step(index, primary_agent, matter, dependencies)
            node = TaskNode(
                id=step_payload["id"],
                agent=step_payload["agent"],
                phase=step_payload.get("phase"),
                description=step_payload.get("description"),
                dependencies=list(step_payload.get("dependencies", [])),
                expected_artifacts=list(step_payload.get("expected_artifacts", [])),
                supporting_agents=list(step_payload.get("supporting_agents", [])),
                exit_signals=list(step_payload.get("exit_signals", [])),
                entry_signals=list(step_payload.get("entry_signals", [])),
                required_connectors=list(step_payload.get("required_connectors", [])),
                metadata={"phase_index": index},
            )
            graph.add_node(node)
            if previous_id:
                graph.add_edge(previous_id, node.id)
            previous_id = node.id
        return graph

    def build_plan(self, matter: dict[str, Any]) -> list[dict[str, Any]]:
        """Construct the ordered plan steps for a matter."""

        return self.build_graph(matter).to_linear_steps()

    def determine_primary_agent(self, phase: Phase, matter: dict[str, Any]) -> str:
        """Pick the primary agent for the given phase and matter."""

        intent = self._infer_intent(matter)
        if phase is Phase.INTAKE_FACTS:
            return "lda"
        if phase is Phase.ISSUE_FRAMING:
            if "damages" in intent or "timeline" in intent:
                return "lda"
            return "dea"
        if phase is Phase.RESEARCH_RETRIEVAL:
            return "dea"
        if phase is Phase.APPLICATION_ANALYSIS:
            if "damages" in intent or "valuation" in intent:
                return "lda"
            return "dea"
        if phase is Phase.DRAFT_REVIEW:
            if "settlement" in intent or "demand" in intent or "negotiat" in intent:
                return "lsa"
            return "lsa"
        if phase is Phase.DOCUMENT_ASSEMBLY:
            return "dda"
        return "dea"

    def evaluate_exit_conditions(
        self, step: dict[str, Any], aggregated: dict[str, Any]
    ) -> list[str]:
        """Return any exit signals that are missing for the step."""

        signals = step.get("exit_signals", [])
        if not signals:
            return []
        missing: list[str] = []
        for signal in signals:
            if not self._signal_present(signal, aggregated):
                missing.append(signal)
        return missing

    def _infer_intent(self, matter: dict[str, Any]) -> str:
        """Infer an intent string from the matter payload."""

        intent_fields = (
            "intent",
            "objective",
            "question",
            "goal",
            "ask",
            "requested_output",
        )
        snippets: list[str] = []
        for field_name in intent_fields:
            value = matter.get(field_name)
            if isinstance(value, str):
                snippets.append(value.lower())
        return " ".join(snippets)

    def _signal_present(self, signal: str, aggregated: dict[str, Any]) -> bool:
        """Check if a signal is satisfied in the aggregated data."""

        keys_to_check = [signal]
        keys_to_check.extend(self._signal_aliases.get(signal, []))
        for candidate in keys_to_check:
            if "." in candidate and self._path_exists(aggregated, candidate.split(".")):
                return True
            if candidate in aggregated and self._is_truthy(aggregated[candidate]):
                return True
            if self._scan_nested(candidate, aggregated):
                return True
        return False

    def _scan_nested(self, candidate: str, payload: dict[str, Any]) -> bool:
        for value in payload.values():
            if isinstance(value, dict):
                if candidate in value and self._is_truthy(value[candidate]):
                    return True
                if self._scan_nested(candidate, value):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and self._scan_nested(candidate, item):
                        return True
        return False

    def _path_exists(self, payload: dict[str, Any], path: Iterable[str]) -> bool:
        current: Any = payload
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        return self._is_truthy(current)

    def _is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, (str, bytes)):
            return bool(value.strip()) if isinstance(value, str) else bool(value)
        if isinstance(value, (list, tuple, set)):
            return bool(value)
        if isinstance(value, dict):
            return bool(value)
        return True

    def _build_phase_definitions(self) -> list[PhaseDefinition]:
        """Create the ordered set of phases for the controller."""

        return [
            PhaseDefinition(
                phase=Phase.INTAKE_FACTS,
                description="Collect structured facts, parties, and timelines from the matter payload.",
                default_primary_agent="lda",
                expected_artifacts=[
                    {
                        "name": "facts",
                        "description": "Structured fact pattern including parties, timeline, and damages data.",
                    },
                ],
                exit_signals=["facts"],
                supporting_agents=[
                    SupportingAgent(
                        agent="dea",
                        role="reflection",
                        description="Identify legal issues that may require additional facts.",
                    ),
                    SupportingAgent(
                        agent="lsa",
                        role="synthesis",
                        description="Capture client tone considerations emerging from intake.",
                    ),
                ],
            ),
            PhaseDefinition(
                phase=Phase.ISSUE_FRAMING,
                description="Frame doctrinal issues grounded in the gathered facts.",
                default_primary_agent="dea",
                expected_artifacts=[
                    {
                        "name": "legal_analysis",
                        "description": "Issue list with corresponding elements and initial authorities.",
                    },
                ],
                exit_signals=["issues"],
                entry_signals=["facts"],
                supporting_agents=[
                    SupportingAgent(
                        agent="lda",
                        role="data_validation",
                        description="Ensure facts and damages data cover the framed issues.",
                    ),
                    SupportingAgent(
                        agent="lsa",
                        role="synthesis",
                        description="Track communication requirements for framed issues.",
                    ),
                ],
            ),
            PhaseDefinition(
                phase=Phase.RESEARCH_RETRIEVAL,
                description="Retrieve controlling and contrary authority, including pin-cites.",
                default_primary_agent="dea",
                expected_artifacts=[
                    {
                        "name": "authorities",
                        "description": "Controlling and contrary authority with Bluebook-compliant cites.",
                    },
                ],
                exit_signals=["controlling_authority", "contrary_authority"],
                entry_signals=["issues"],
                supporting_agents=[
                    SupportingAgent(
                        agent="lda",
                        role="quant_validation",
                        description="Cross-check damages/timeline data referenced in authorities.",
                    ),
                ],
            ),
            PhaseDefinition(
                phase=Phase.APPLICATION_ANALYSIS,
                description="Apply doctrine to the facts and quantify exposure or damages.",
                default_primary_agent="dea",
                expected_artifacts=[
                    {
                        "name": "analysis",
                        "description": "Application of law to facts with damages or exposure modeling.",
                    },
                ],
                exit_signals=["analysis"],
                entry_signals=["controlling_authority"],
                supporting_agents=[
                    SupportingAgent(
                        agent="lda",
                        role="model_validation",
                        description="Validate computations and timelines referenced in the analysis.",
                    ),
                    SupportingAgent(
                        agent="lsa",
                        role="synthesis",
                        description="Translate analysis into negotiation-ready insights.",
                    ),
                ],
            ),
            PhaseDefinition(
                phase=Phase.DRAFT_REVIEW,
                description="Draft and review client-ready outputs with guardrails and tone checks.",
                default_primary_agent="lsa",
                expected_artifacts=[
                    {
                        "name": "draft",
                        "description": "Client-safe narrative, negotiation posture, and next steps.",
                    },
                ],
                exit_signals=["draft", "client_safe_summary"],
                entry_signals=["analysis"],
                supporting_agents=[
                    SupportingAgent(
                        agent="dea",
                        role="citation_review",
                        description="Validate authorities, pin-cites, and risk disclosures.",
                    ),
                    SupportingAgent(
                        agent="lda",
                        role="numerical_review",
                        description="Reconcile damages figures and timelines embedded in the draft.",
                    ),
                ],
            ),
            PhaseDefinition(
                phase=Phase.DOCUMENT_ASSEMBLY,
                description="Generate formal legal documents with proper formatting and citations.",
                default_primary_agent="dda",
                expected_artifacts=[
                    {
                        "name": "document",
                        "description": "Court-ready legal document (complaint, motion, demand letter, etc.).",
                    },
                ],
                exit_signals=["document"],
                entry_signals=["draft"],
                supporting_agents=[
                    SupportingAgent(
                        agent="dea",
                        role="citation_validation",
                        description="Verify all legal citations are properly formatted.",
                    ),
                    SupportingAgent(
                        agent="lsa",
                        role="tone_review",
                        description="Ensure document tone is appropriate for the document type.",
                    ),
                ],
            ),
        ]
