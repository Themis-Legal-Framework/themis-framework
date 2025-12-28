"""Agent protocol definitions for Themis."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable
from time import perf_counter
from typing import TYPE_CHECKING, Any, Protocol

from tools.metrics import metrics_registry

from .tooling import ToolSpec

if TYPE_CHECKING:  # pragma: no cover - typing only
    from orchestrator.tracing import TraceRecorder


logger = logging.getLogger("themis.agents")

_RUN_DURATION = metrics_registry.histogram(
    "themis_agent_run_seconds",
    "Wall clock duration for agent run executions.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
_TOOL_INVOCATIONS = metrics_registry.counter(
    "themis_agent_tool_invocations_total",
    "Number of tool invocations performed by an agent.",
)
_RUN_ERRORS = metrics_registry.counter(
    "themis_agent_run_errors_total",
    "Count of agent runs that raised an exception.",
)


class AgentProtocol(Protocol):
    """Minimal interface that all orchestrated agents must satisfy."""

    name: str

    async def run(self, matter: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent given the current matter context."""


class BaseAgent(ABC):
    """Helper base class implementing shared plumbing for agents."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name
        self._tools: dict[str, ToolSpec] = {}
        self._tool_invocations = 0
        self._trace: TraceRecorder | None = None
        self._active_node_id: str | None = None

    # ---------------------------------------------------------------------
    # Tool registration
    # ---------------------------------------------------------------------
    def register_tool(self, spec: ToolSpec | tuple[str, Any]) -> None:
        """Register a tool specification or backwards-compatible tuple."""

        if isinstance(spec, tuple):
            name, callable_ = spec
            tool_spec = ToolSpec.ensure(name, callable_)
        else:
            tool_spec = spec
        self._tools[tool_spec.name] = tool_spec

    def register_tools(self, specs: Iterable[ToolSpec | tuple[str, Any]]) -> None:
        for spec in specs:
            self.register_tool(spec)

    def require_tools(self, required: Iterable[str]) -> None:
        missing = [tool for tool in required if tool not in self._tools]
        if missing:
            missing_csv = ", ".join(missing)
            raise ValueError(f"Missing required tools for {self.name} agent: {missing_csv}")

    @property
    def tools(self) -> dict[str, ToolSpec]:
        return dict(self._tools)

    @tools.setter
    def tools(self, mapping: dict[str, Any]) -> None:
        self._tools = {}
        if mapping:
            for name, candidate in mapping.items():
                self._tools[name] = ToolSpec.ensure(name, candidate)

    # ------------------------------------------------------------------
    # Tracing support
    # ------------------------------------------------------------------
    def attach_tracer(self, tracer: TraceRecorder | None, node_id: str | None = None) -> None:
        self._trace = tracer
        self._active_node_id = node_id

    async def run(self, matter: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent logic with structured logging and metrics."""

        logger.info(
            "agent_run_start",
            extra={"event": "agent_run_start", "agent": self.name},
        )

        start = perf_counter()
        self._tool_invocations = 0
        if self._trace:
            self._trace.record(
                "agent_run_start",
                agent=self.name,
                node_id=self._active_node_id,
            )
        try:
            result = await self._run(matter)
        except Exception:
            _RUN_ERRORS.inc(agent=self.name)
            logger.exception(
                "agent_run_error",
                extra={"event": "agent_run_error", "agent": self.name},
            )
            if self._trace:
                self._trace.record(
                    "agent_run_error",
                    agent=self.name,
                    node_id=self._active_node_id,
                )
            raise
        else:
            if self._trace:
                self._trace.record(
                    "agent_run_complete",
                    agent=self.name,
                    node_id=self._active_node_id,
                )
            return result
        finally:
            duration = perf_counter() - start
            _RUN_DURATION.observe(duration, agent=self.name)
            _TOOL_INVOCATIONS.inc(value=self._tool_invocations, agent=self.name)
            logger.info(
                "agent_run_complete",
                extra={
                    "event": "agent_run_complete",
                    "agent": self.name,
                    "duration": duration,
                    "tool_invocations": self._tool_invocations,
                },
            )

    @abstractmethod
    async def _run(self, matter: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent logic."""
        raise NotImplementedError

    async def _call_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke a named tool while recording structured telemetry.

        Supports both synchronous and asynchronous tools.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered for agent {self.name}.")

        logger.info(
            "agent_tool_invocation",
            extra={"event": "agent_tool_invocation", "agent": self.name, "tool": name},
        )
        if self._trace:
            self._trace.record(
                "agent_tool_invocation",
                agent=self.name,
                node_id=self._active_node_id,
                tool=name,
            )
        self._tool_invocations += 1
        tool = self._tools[name]
        result = tool.invoke(*args, **kwargs)

        # Support both sync and async tools
        if asyncio.iscoroutine(result):
            return await result
        return result

    def _build_response(
        self,
        *,
        core: dict[str, Any],
        provenance: dict[str, Any],
        unresolved_issues: list[str],
    ) -> dict[str, Any]:
        """Merge common response fields with validation safeguards.

        Every agent response must expose provenance information describing
        the materials or tools used as well as an explicit list of
        unresolved issues.  The unresolved list may be empty when the agent
        has nothing to escalate, but it must always be present to ensure the
        orchestrator can reason about follow-up work.
        """

        if not isinstance(provenance, dict) or not provenance:
            raise ValueError(
                f"{self.name} agent requires non-empty provenance metadata",
            )
        if not isinstance(unresolved_issues, list):
            raise ValueError(
                f"{self.name} agent must provide a list of unresolved issues",
            )

        return {
            "agent": self.name,
            **core,
            "provenance": provenance,
            "unresolved_issues": unresolved_issues,
        }
