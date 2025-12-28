"""Routing layer exposing orchestrator operations via FastAPI."""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.security import verify_api_key
from orchestrator.models import Matter, MatterWrapper
from orchestrator.service import OrchestratorService

logger = logging.getLogger("themis.orchestrator.router")

router = APIRouter()
_service: OrchestratorService | None = None

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SCRIPT_BLOCK = re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL)
_MAX_STRING_LENGTH = 10000


class PlanRequest(BaseModel):
    """Request payload for planning operations."""

    model_config = ConfigDict(extra="forbid")

    matter: dict[str, Any]


class ExecuteRequest(BaseModel):
    """Request payload for executing previously generated plans."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str | None = None
    matter: dict[str, Any] | None = None


def _sanitize_string(value: str) -> str:
    sanitized = _CONTROL_CHARACTERS.sub("", value)
    sanitized = _SCRIPT_BLOCK.sub("", sanitized)
    sanitized = sanitized.replace("\r", " ").replace("\n", " ").strip()
    if len(sanitized) > _MAX_STRING_LENGTH:
        sanitized = sanitized[:_MAX_STRING_LENGTH]
    return sanitized


def sanitize_matter_payload(payload: Any) -> Any:
    """Recursively sanitize user-provided matter payloads."""

    if isinstance(payload, str):
        return _sanitize_string(payload)
    if isinstance(payload, list):
        return [sanitize_matter_payload(item) for item in payload]
    if isinstance(payload, dict):
        return {key: sanitize_matter_payload(value) for key, value in payload.items()}
    return payload


def configure_service(service: OrchestratorService) -> None:
    """Register the orchestrator service instance used by the router."""

    global _service
    _service = service


def get_service() -> OrchestratorService:
    """Return the configured orchestrator service, creating one if missing."""

    global _service
    if _service is None:
        _service = OrchestratorService()
    return _service


def validate_and_extract_matter(matter_data: dict[str, Any]) -> dict[str, Any]:
    """Validate matter payload and extract data.

    Attempts to validate the matter payload using Pydantic models for type safety.
    Raises a 422 HTTP error if validation fails so the caller can correct payloads.

    Args:
        matter_data: Raw matter data (may be {"matter": {...}} or direct matter dict)

    Returns:
        Validated matter dict (always extracts inner "matter" key if present)

    Raises:
        HTTPException: If validation fails with helpful error messages
    """
    try:
        # Try to validate as wrapped matter first ({"matter": {...}})
        if "matter" in matter_data:
            wrapper = MatterWrapper.model_validate(matter_data)
            inner = wrapper.matter
            if isinstance(inner, Matter):
                return sanitize_matter_payload(inner.model_dump(exclude_none=True))
            validated_inner = Matter.model_validate(inner)
            return sanitize_matter_payload(validated_inner.model_dump(exclude_none=True))

        # Try to validate as direct matter
        validated = Matter.model_validate(matter_data)
        return sanitize_matter_payload(validated.model_dump(exclude_none=True))

    except ValidationError as exc:
        # Log validation errors for debugging
        logger.warning(f"Matter validation failed: {exc.error_count()} errors")
        for error in exc.errors():
            logger.debug(f"  - {error['loc']}: {error['msg']}")

        # Return helpful error message
        error_details = []
        for error in exc.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            error_details.append(f"{location}: {error['msg']}")

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Matter validation failed",
                "errors": error_details[:10],  # Limit to first 10 errors
                "total_errors": exc.error_count(),
            },
        ) from exc


@router.post("/plan", summary="Create an execution plan for a legal matter")
@limiter.limit("20/minute")  # 20 requests per minute per IP
async def plan(
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Generate a draft plan given a matter payload.

    Validates the matter payload for required fields and data types.
    Requires authentication via Bearer token if THEMIS_API_KEY is set.
    Rate limited to 20 requests per minute per IP address.
    """
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload provided.",
        ) from exc
    plan_request = PlanRequest.model_validate(payload)
    service = get_service()
    validated_matter = validate_and_extract_matter(plan_request.matter)
    return await service.plan(validated_matter)


@router.post("/execute", summary="Run a plan through registered agents")
@limiter.limit("10/minute")  # 10 requests per minute per IP (lower limit for expensive operations)
async def execute(
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Run a matter through the orchestrated workflow.

    Validates the matter payload if provided.
    Requires authentication via Bearer token if THEMIS_API_KEY is set.
    Rate limited to 10 requests per minute per IP address.
    """
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload provided.",
        ) from exc
    execute_request = ExecuteRequest.model_validate(payload)

    if execute_request.plan_id is None and execute_request.matter is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either an existing plan_id or a matter payload to execute.",
        )

    service = get_service()
    try:
        # Validate matter if provided
        validated_matter = None
        if execute_request.matter is not None:
            validated_matter = validate_and_extract_matter(execute_request.matter)

        result = await service.execute(plan_id=execute_request.plan_id, matter=validated_matter)

        # Log DDA response structure for debugging
        if 'artifacts' in result and 'dda' in result['artifacts']:
            dda_artifact = result['artifacts']['dda']
            if isinstance(dda_artifact, dict) and 'document' in dda_artifact:
                doc = dda_artifact['document']
                if 'full_text' in doc:
                    logger.debug(f"DDA full_text present: {len(doc['full_text'])} chars")
                else:
                    logger.warning("DDA document missing full_text")

        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/plans/{plan_id}", summary="Retrieve a previously generated plan")
@limiter.limit("60/minute")  # 60 requests per minute per IP (higher limit for read operations)
async def get_plan(
    plan_id: str,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Fetch a plan definition by identifier.

    Requires authentication via Bearer token if THEMIS_API_KEY is set.
    Rate limited to 60 requests per minute per IP address.
    """
    service = get_service()
    try:
        return await service.get_plan(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/artifacts/{plan_id}", summary="Retrieve execution artifacts for a plan")
@limiter.limit("60/minute")  # 60 requests per minute per IP (higher limit for read operations)
async def get_artifacts(
    plan_id: str,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Fetch artifacts generated during execution for a plan.

    Requires authentication via Bearer token if THEMIS_API_KEY is set.
    Rate limited to 60 requests per minute per IP address.
    """
    service = get_service()
    try:
        return await service.get_artifacts(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
