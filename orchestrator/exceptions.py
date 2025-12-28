"""Custom exceptions for the Themis orchestrator.

Provides a hierarchy of exceptions for better error handling and reporting.
"""

from __future__ import annotations

from typing import Any


class ThemisError(Exception):
    """Base exception for all Themis errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to a dictionary for JSON responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(ThemisError):
    """Raised when input validation fails.

    Used for matter payload validation, parameter validation, etc.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.field = field
        self.value = value
        if field:
            self.details["field"] = field
        if value is not None:
            self.details["value"] = str(value)[:100]  # Truncate for safety


class PlanNotFoundError(ThemisError):
    """Raised when a referenced plan does not exist."""

    def __init__(self, plan_id: str) -> None:
        super().__init__(f"Plan '{plan_id}' does not exist", {"plan_id": plan_id})
        self.plan_id = plan_id


class ExecutionNotFoundError(ThemisError):
    """Raised when a referenced execution does not exist."""

    def __init__(self, plan_id: str) -> None:
        super().__init__(
            f"Execution for plan '{plan_id}' does not exist",
            {"plan_id": plan_id},
        )
        self.plan_id = plan_id


class AgentNotFoundError(ThemisError):
    """Raised when a referenced agent is not registered."""

    def __init__(self, agent_name: str) -> None:
        super().__init__(
            f"Agent '{agent_name}' is not registered",
            {"agent_name": agent_name},
        )
        self.agent_name = agent_name


class AgentExecutionError(ThemisError):
    """Raised when an agent fails during execution."""

    def __init__(
        self,
        agent_name: str,
        original_error: Exception,
        step_id: str | None = None,
    ) -> None:
        super().__init__(
            f"Agent '{agent_name}' failed: {original_error!s}",
            {
                "agent_name": agent_name,
                "original_error": str(original_error),
                "original_error_type": type(original_error).__name__,
            },
        )
        self.agent_name = agent_name
        self.original_error = original_error
        if step_id:
            self.details["step_id"] = step_id


class ConnectorError(ThemisError):
    """Raised when a connector fails or is unavailable."""

    def __init__(self, connector_name: str, message: str) -> None:
        super().__init__(
            f"Connector '{connector_name}' error: {message}",
            {"connector_name": connector_name},
        )
        self.connector_name = connector_name


class DocumentGenerationError(ThemisError):
    """Raised when document generation fails."""

    def __init__(
        self,
        document_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            f"Failed to generate {document_type}: {message}",
            {"document_type": document_type, **(details or {})},
        )
        self.document_type = document_type


class LLMError(ThemisError):
    """Raised when LLM operations fail."""

    def __init__(
        self,
        operation: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            f"LLM {operation} failed: {message}",
            {"operation": operation, **(details or {})},
        )
        self.operation = operation
