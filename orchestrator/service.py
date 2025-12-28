"""Application service coordinating registered legal agents."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from copy import deepcopy
from typing import Any
from uuid import uuid4

from agents.base import AgentProtocol
from agents.dda import DocumentDraftingAgent
from agents.dea import DEAAgent
from agents.lda import LDAAgent
from agents.lsa import LSAAgent
from connectors import ConnectorRegistry
from orchestrator.document_type_detector import determine_document_type
from orchestrator.exceptions import (
    ExecutionNotFoundError,
    PlanNotFoundError,
)
from orchestrator.policy import RoutingPolicy
from orchestrator.storage.sqlite_repository import SQLiteOrchestratorStateRepository
from orchestrator.task_graph import TaskGraph
from orchestrator.tracing import TraceRecorder
from orchestrator.validation import validate_execute_params, validate_matter

logger = logging.getLogger("themis.orchestrator")


class OrchestratorService:
    """Service responsible for planning and executing agent workflows.

    Implements in-memory caching with TTL to reduce database reads.
    """

    def __init__(
        self,
        agents: dict[str, AgentProtocol] | None = None,
        repository: SQLiteOrchestratorStateRepository | None = None,
        cache_ttl_seconds: int = 60,
        policy: RoutingPolicy | None = None,
        connectors: ConnectorRegistry | None = None,
        tracer_factory: Callable[[], TraceRecorder] | None = None,
    ) -> None:
        self.repository = repository or SQLiteOrchestratorStateRepository()
        self.agents = agents or {
            "lda": LDAAgent(),
            "dea": DEAAgent(),
            "lsa": LSAAgent(),
            "dda": DocumentDraftingAgent(),
        }
        self.policy = policy or RoutingPolicy()
        self.connectors = connectors or ConnectorRegistry()
        self._tracer_factory = tracer_factory or TraceRecorder

        # State caching with TTL
        self._state_cache = None
        self._cache_timestamp = None
        self._cache_ttl = cache_ttl_seconds
        self._dirty = False

        # Initialize cache
        self.state = self._load_state()

    def _load_state(self):
        """Load state from repository with caching logic.

        Uses in-memory cache with TTL to reduce database reads.
        Returns cached state if fresh, otherwise loads from database.
        """
        now = time.time()

        # Check if cache is valid
        if (
            self._state_cache is not None
            and self._cache_timestamp is not None
            and (now - self._cache_timestamp) < self._cache_ttl
        ):
            logger.debug("State cache hit (age: %.2fs)", now - self._cache_timestamp)
            return self._state_cache

        # Cache miss - load from database
        logger.debug("State cache miss - loading from database")
        self._state_cache = self.repository.load_state()
        self._cache_timestamp = now
        self._dirty = False
        return self._state_cache

    def _save_state(self):
        """Save state to repository and update cache.

        Uses write-through caching to keep cache synchronized.
        """
        logger.debug("Saving state to database")
        self.repository.save_state(self.state)
        self._state_cache = self.state
        self._cache_timestamp = time.time()
        self._dirty = False

    def _invalidate_cache(self):
        """Invalidate the state cache, forcing next read to hit database."""
        logger.debug("Cache invalidated")
        self._state_cache = None
        self._cache_timestamp = None
        self._dirty = False

    async def plan(self, matter: dict[str, Any]) -> dict[str, Any]:
        """Create an executable plan across the registered agents.

        Args:
            matter: The legal matter payload to plan for.

        Returns:
            The created plan with steps and metadata.

        Raises:
            ValidationError: If the matter payload is invalid.
        """
        # Validate input
        validated_matter = validate_matter(matter)

        self.state = self._load_state()
        plan_id = str(uuid4())
        graph = self.policy.build_graph(validated_matter)

        plan: dict[str, Any] = {
            "plan_id": plan_id,
            "status": "planned",
            "matter": validated_matter,
            "graph": graph.as_dict(),
            "steps": graph.to_linear_steps(),
            "connectors": self.connectors.catalogue(),
        }

        # Log planned phases
        phases = [step.get("phase") for step in plan["steps"]]
        logger.debug(f"Planned phases: {phases}")

        self.state.remember_plan(plan_id, deepcopy(plan))
        self._save_state()
        return plan

    async def execute(
        self,
        matter: dict[str, Any] | None = None,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute a plan by invoking each registered agent in order.

        Args:
            matter: Optional matter payload (required if no plan_id).
            plan_id: Optional plan ID to execute (if provided, uses existing plan).

        Returns:
            Execution record with status, steps, and artifacts.

        Raises:
            ValidationError: If parameters are invalid.
            PlanNotFoundError: If the specified plan does not exist.
        """
        # Validate inputs
        validated_matter, validated_plan_id = validate_execute_params(matter, plan_id)

        self.state = self._load_state()
        if validated_plan_id is not None:
            plan = self.state.recall_plan(validated_plan_id)
            if plan is None:
                raise PlanNotFoundError(validated_plan_id)
            if validated_matter is not None:
                plan["matter"] = validated_matter
                self.state.remember_plan(validated_plan_id, deepcopy(plan))
                self._save_state()
            plan_id = validated_plan_id
        else:
            plan = await self.plan(validated_matter)
            plan_id = plan["plan_id"]

        plan_matter = deepcopy(plan.get("matter", {}))
        steps_results: list[dict[str, Any]] = []
        artifacts: dict[str, Any] = {}
        propagated: dict[str, Any] = {}
        overall_status = "complete"
        needs_attention = False
        tracer = self._tracer_factory()

        graph_payload = plan.get("graph")
        if graph_payload:
            graph = TaskGraph.from_dict(graph_payload)
        else:
            graph = TaskGraph.from_linear_steps(plan.get("steps", []))

        plan_steps_map = {step["id"]: step for step in plan.get("steps", [])}
        if not plan_steps_map:
            plan["steps"] = graph.to_linear_steps()
            plan_steps_map = {step["id"]: step for step in plan["steps"]}

        for node in graph.topological_order():
            step = plan_steps_map.get(node.id, node.as_dict())
            agent_name = step["agent"]
            agent = self.agents.get(agent_name)
            step_result: dict[str, Any] = {
                "id": step["id"],
                "agent": agent_name,
                "dependencies": step.get("dependencies", []),
                "expected_artifacts": step.get("expected_artifacts", []),
                "phase": step.get("phase"),
            }

            if agent is None:
                step_result["status"] = "failed"
                step_result["error"] = f"Agent '{agent_name}' is not registered"
                overall_status = "failed"
                step["status"] = "failed"
                step["error"] = step_result["error"]
                steps_results.append(step_result)
                continue

            produced_artifacts: dict[str, Any] = {}
            tracer.record(
                "phase_start",
                node_id=step_result["id"],
                agent=agent_name,
                phase=step.get("phase"),
            )
            if agent and hasattr(agent, "attach_tracer"):
                agent.attach_tracer(tracer, step_result["id"])

            try:
                agent_input = deepcopy(plan_matter)
                agent_input.update(propagated)
                resolved_connectors = self.connectors.resolve(
                    step.get("required_connectors", [])
                )
                if resolved_connectors:
                    agent_input.setdefault("connectors", {}).update(resolved_connectors)

                # Auto-detect document type before DDA runs
                if agent_name == "dda" and "document_type" not in agent_input:
                    if "document_type" not in agent_input.get("metadata", {}):
                        logger.debug("Auto-detecting document type for DDA agent")
                        detected_type = await determine_document_type(agent_input)
                        logger.debug(f"Document type detected: {detected_type}")
                        agent_input["document_type"] = detected_type
                        if "metadata" not in agent_input:
                            agent_input["metadata"] = {}
                        agent_input["metadata"]["document_type"] = detected_type

                output = await agent.run(agent_input)
            except Exception as exc:  # pragma: no cover - defensive programming
                step_result["status"] = "failed"
                step_result["error"] = str(exc)
                overall_status = "failed"
                step["status"] = "failed"
                step["error"] = step_result["error"]
            else:
                step_result["status"] = "complete"
                step_result["output"] = output
                artifacts[agent_name] = output
                propagated[agent_name] = output

                # Log artifact storage for debugging
                if agent_name == "dda":
                    logger.debug(f"DDA output keys: {list(output.keys()) if isinstance(output, dict) else 'NOT A DICT'}")
                    if isinstance(output, dict) and 'document' in output:
                        doc = output['document']
                        if 'full_text' in doc:
                            logger.debug(f"DDA full_text length: {len(doc['full_text'])} chars")
                        else:
                            logger.warning("DDA document missing full_text")

                produced_artifacts = _collect_expected_artifacts(
                    output, step.get("expected_artifacts", [])
                )
                if produced_artifacts:
                    propagated.update(produced_artifacts)
                    plan_matter.update(produced_artifacts)
                    step_result["artifacts"] = produced_artifacts
                    step["artifacts"] = produced_artifacts
                step["status"] = "complete"
                step["output"] = output
            finally:
                tracer.record(
                    "phase_complete",
                    node_id=step_result["id"],
                    agent=agent_name,
                    status=step_result.get("status"),
                )

            if step_result.get("status") == "failed":
                steps_results.append(step_result)
                step["status"] = "failed"
                continue

            supporting_outputs: list[dict[str, Any]] = []
            support_failed = False
            for supporting in step.get("supporting_agents", []) or []:
                support_agent_name = supporting.get("agent")
                support_agent = self.agents.get(support_agent_name)
                support_result: dict[str, Any] = {
                    "agent": support_agent_name,
                    "role": supporting.get("role"),
                    "description": supporting.get("description"),
                }

                if support_agent is None:
                    support_result["status"] = "failed"
                    support_result["error"] = (
                        f"Supporting agent '{support_agent_name}' is not registered"
                    )
                    overall_status = "failed"
                    support_failed = True
                else:
                    if hasattr(support_agent, "attach_tracer"):
                        support_agent.attach_tracer(
                            tracer,
                            f"{step_result['id']}::support::{support_agent_name}",
                        )
                    support_input = deepcopy(plan_matter)
                    support_input.update(propagated)
                    support_input.update(
                        {
                            "primary_agent": agent_name,
                            "primary_output": step_result.get("output"),
                            "phase": step.get("phase"),
                            "support_role": supporting.get("role"),
                        }
                    )
                    try:
                        support_output = await support_agent.run(support_input)
                    except Exception as exc:  # pragma: no cover - defensive
                        support_result["status"] = "failed"
                        support_result["error"] = str(exc)
                        overall_status = "failed"
                        support_failed = True
                    else:
                        support_result["status"] = "complete"
                        support_result["output"] = support_output
                        propagated[support_agent_name] = support_output
                        produced_support_artifacts = _collect_expected_artifacts(
                            support_output, supporting.get("expected_artifacts", [])
                        )
                        if produced_support_artifacts:
                            propagated.update(produced_support_artifacts)
                            plan_matter.update(produced_support_artifacts)
                            support_result["artifacts"] = produced_support_artifacts
                supporting_outputs.append(support_result)

            if supporting_outputs:
                step_result["supporting_outputs"] = supporting_outputs
                step.setdefault("supporting_outputs", deepcopy(supporting_outputs))

            if support_failed:
                step_result["status"] = "failed"
                step["status"] = "failed"
                steps_results.append(step_result)
                continue

            if step_result.get("status") == "complete":
                missing_signals = self.policy.evaluate_exit_conditions(
                    step, {**plan_matter, **propagated}
                )
                if missing_signals:
                    step_result["status"] = "attention_required"
                    step_result["missing_signals"] = missing_signals
                    step["status"] = "attention_required"
                    step["missing_signals"] = missing_signals
                    needs_attention = True

            steps_results.append(step_result)

        execution_record = {
            "plan_id": plan_id,
            "status": overall_status,
            "steps": steps_results,
            "artifacts": artifacts,
            "trace": tracer.flush(),
        }

        if overall_status != "failed":
            overall_status = "attention_required" if needs_attention else "complete"
            execution_record["status"] = overall_status

        plan["status"] = overall_status
        self.state.remember_plan(plan_id, deepcopy(plan))
        self.state.remember_execution(plan_id, deepcopy(execution_record))
        self._save_state()

        return execution_record

    async def get_plan(self, plan_id: str) -> dict[str, Any]:
        """Retrieve a persisted plan by identifier.

        Args:
            plan_id: The plan ID to retrieve.

        Returns:
            The plan data.

        Raises:
            PlanNotFoundError: If the plan does not exist.
        """
        self.state = self._load_state()
        plan = self.state.recall_plan(plan_id)
        if plan is None:
            raise PlanNotFoundError(plan_id)
        return deepcopy(plan)

    async def get_artifacts(self, plan_id: str) -> dict[str, Any]:
        """Retrieve execution artifacts for a given plan identifier.

        Args:
            plan_id: The plan ID to get artifacts for.

        Returns:
            The execution artifacts.

        Raises:
            ExecutionNotFoundError: If the execution does not exist.
        """
        self.state = self._load_state()
        execution = self.state.recall_execution(plan_id)
        if execution is None:
            raise ExecutionNotFoundError(plan_id)
        return deepcopy(execution.get("artifacts", {}))


def _collect_expected_artifacts(
    payload: dict[str, Any], expected_artifacts: list[dict[str, Any]]
) -> dict[str, Any]:
    """Extract advertised artifacts from an agent payload."""

    collected: dict[str, Any] = {}
    for artifact in expected_artifacts or []:
        if not isinstance(artifact, dict):
            continue
        name = artifact.get("name")
        if not name:
            continue
        value = payload.get(name)
        if value is None:
            value = _find_nested_artifact(payload, name)
        if value is not None:
            collected[name] = value
    return collected


def _find_nested_artifact(payload: dict[str, Any], artifact_name: str) -> Any:
    """Locate a nested artifact within the payload."""

    for value in payload.values():
        if isinstance(value, dict):
            if artifact_name in value:
                return value[artifact_name]
            nested = _find_nested_artifact(value, artifact_name)
            if nested is not None:
                return nested
    return None
