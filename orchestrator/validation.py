"""Input validation utilities for the Themis orchestrator.

Provides validation functions that use Pydantic models and raise
custom exceptions on failure.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from orchestrator.exceptions import ValidationError
from orchestrator.models import Matter

logger = logging.getLogger("themis.orchestrator.validation")


def validate_matter(matter: dict[str, Any] | None, require_documents: bool = True) -> dict[str, Any]:
    """Validate a matter payload using Pydantic models.

    Args:
        matter: The matter payload to validate.
        require_documents: Whether documents are required (default True).

    Returns:
        The validated and normalized matter payload.

    Raises:
        ValidationError: If the matter is invalid.
    """
    if matter is None:
        raise ValidationError(
            "Matter payload is required",
            field="matter",
        )

    if not isinstance(matter, dict):
        raise ValidationError(
            f"Matter must be a dictionary, got {type(matter).__name__}",
            field="matter",
            value=type(matter).__name__,
        )

    # Check for minimum required fields
    if "summary" not in matter:
        raise ValidationError(
            "Matter must include a 'summary' field",
            field="summary",
        )

    if "parties" not in matter:
        raise ValidationError(
            "Matter must include a 'parties' field",
            field="parties",
        )

    if require_documents and "documents" not in matter:
        raise ValidationError(
            "Matter must include a 'documents' field",
            field="documents",
        )

    # Use Pydantic for detailed validation
    try:
        validated = Matter.model_validate(matter)
        # Convert back to dict for compatibility with existing code
        return validated.model_dump(mode="python", exclude_unset=True)
    except PydanticValidationError as e:
        # Extract the first error for the message
        errors = e.errors()
        if errors:
            first_error = errors[0]
            field_path = ".".join(str(loc) for loc in first_error.get("loc", []))
            message = first_error.get("msg", "Validation failed")
            raise ValidationError(
                f"Invalid matter: {message}",
                field=field_path,
                details={"pydantic_errors": list(errors[:5])},  # Limit errors
            ) from e
        raise ValidationError("Invalid matter payload") from e


def validate_plan_id(plan_id: str | None) -> str:
    """Validate a plan ID.

    Args:
        plan_id: The plan ID to validate.

    Returns:
        The validated plan ID.

    Raises:
        ValidationError: If the plan ID is invalid.
    """
    if plan_id is None:
        raise ValidationError(
            "Plan ID is required",
            field="plan_id",
        )

    if not isinstance(plan_id, str):
        raise ValidationError(
            f"Plan ID must be a string, got {type(plan_id).__name__}",
            field="plan_id",
            value=type(plan_id).__name__,
        )

    plan_id = plan_id.strip()
    if not plan_id:
        raise ValidationError(
            "Plan ID cannot be empty",
            field="plan_id",
        )

    return plan_id


def validate_document_type(document_type: str | None) -> str:
    """Validate a document type.

    Args:
        document_type: The document type to validate.

    Returns:
        The validated and normalized document type.

    Raises:
        ValidationError: If the document type is invalid.
    """
    valid_types = {"complaint", "motion", "memorandum", "demand_letter", "brief", "answer"}

    if document_type is None:
        return "memorandum"  # Default

    if not isinstance(document_type, str):
        raise ValidationError(
            f"Document type must be a string, got {type(document_type).__name__}",
            field="document_type",
            value=type(document_type).__name__,
        )

    normalized = document_type.strip().lower().replace(" ", "_")

    if normalized not in valid_types:
        logger.warning(
            f"Unknown document type '{document_type}', using as-is. "
            f"Known types: {', '.join(sorted(valid_types))}"
        )

    return normalized


def validate_jurisdiction(jurisdiction: str | None) -> str:
    """Validate a jurisdiction.

    Args:
        jurisdiction: The jurisdiction to validate.

    Returns:
        The validated jurisdiction.

    Raises:
        ValidationError: If the jurisdiction is invalid.
    """
    if jurisdiction is None:
        return "federal"  # Default

    if not isinstance(jurisdiction, str):
        raise ValidationError(
            f"Jurisdiction must be a string, got {type(jurisdiction).__name__}",
            field="jurisdiction",
            value=type(jurisdiction).__name__,
        )

    jurisdiction = jurisdiction.strip()
    if not jurisdiction:
        return "federal"  # Default if empty

    return jurisdiction


def validate_execute_params(
    matter: dict[str, Any] | None,
    plan_id: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate parameters for the execute method.

    Args:
        matter: Optional matter payload.
        plan_id: Optional plan ID.

    Returns:
        Tuple of (validated_matter, validated_plan_id).

    Raises:
        ValidationError: If the parameters are invalid.
    """
    # At least one must be provided
    if matter is None and plan_id is None:
        raise ValidationError(
            "Either 'matter' or 'plan_id' must be provided",
            details={"matter": None, "plan_id": None},
        )

    validated_matter = None
    validated_plan_id = None

    if plan_id is not None:
        validated_plan_id = validate_plan_id(plan_id)

    if matter is not None:
        validated_matter = validate_matter(matter, require_documents=True)

    return validated_matter, validated_plan_id
