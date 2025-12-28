"""FastAPI surface for the Themis orchestrator."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.logging_config import configure_logging
from api.middleware import (
    AuditLoggingMiddleware,
    CostTrackingMiddleware,
    PayloadSizeLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from orchestrator.router import configure_service
from orchestrator.router import router as orchestrator_router
from orchestrator.service import OrchestratorService
from tools.metrics import metrics_registry

# Configure logging first
configure_logging()

logger = logging.getLogger("themis.api")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown).

    This replaces the deprecated @app.on_event decorators with
    a modern context manager approach.
    """
    # Startup: Initialize the orchestrator service
    logger.info("Starting Themis Orchestrator API")
    service = OrchestratorService()
    configure_service(service)
    app.state.orchestrator_service = service
    logger.info("Orchestrator service initialized successfully")

    yield

    # Shutdown: Clean up resources (if needed in the future)
    logger.info("Shutting down Themis Orchestrator API")


app = FastAPI(
    title="Themis Orchestration API",
    description="Multi-agent legal analysis workflow orchestration.",
    version="0.1.0",
    lifespan=lifespan,
)

# Store startup time for health checks
app.state.startup_time = time.time()

# Attach rate limiter to app state and add exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration (configurable via environment)
cors_origins = os.getenv("CORS_ORIGINS", "").split(",")
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
    )

# Add GZip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add middleware (order matters - last added is executed first)
app.add_middleware(SecurityHeadersMiddleware)  # Add security headers
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(CostTrackingMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PayloadSizeLimitMiddleware)  # Check payload size first


# Standardized error response handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Return standardized JSON error responses."""
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return standardized validation error responses."""
    request_id = getattr(request.state, "request_id", "unknown")
    errors = []
    for error in exc.errors():
        location = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({"field": location, "message": error["msg"]})

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "details": errors[:10],  # Limit to first 10 errors
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors gracefully."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled exception: {exc} | request_id={request_id}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "request_id": request_id,
            }
        },
    )


app.include_router(orchestrator_router, prefix="/orchestrator", tags=["orchestrator"])


@app.get("/", response_class=HTMLResponse, tags=["system"])
async def root() -> HTMLResponse:
    """Serve the landing page with document upload form."""
    static_dir = Path(__file__).parent / "static"
    index_path = static_dir / "index.html"

    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    else:
        return HTMLResponse(
            content="""
            <html>
                <body>
                    <h1>Themis Orchestration API</h1>
                    <p>Multi-agent legal analysis workflow orchestration.</p>
                    <p><a href="/docs">API Documentation</a></p>
                </body>
            </html>
            """
        )


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    """Basic health check for load balancers and monitoring."""
    return {"status": "healthy"}


@app.get("/health/live", tags=["system"])
async def liveness_probe() -> dict[str, str]:
    """Kubernetes liveness probe - is the process alive?"""
    return {"status": "alive"}


@app.get("/health/ready", tags=["system"])
async def readiness_probe(request: Request) -> dict:
    """Kubernetes readiness probe - is the service ready to accept traffic?

    Checks:
    - Orchestrator service is initialized
    - Database connection is working (if applicable)
    """
    checks: dict[str, bool] = {}

    # Check orchestrator service
    try:
        service = getattr(request.app.state, "orchestrator_service", None)
        checks["orchestrator"] = service is not None
    except Exception:
        checks["orchestrator"] = False

    # Calculate uptime
    startup_time = getattr(request.app.state, "startup_time", time.time())
    uptime_seconds = time.time() - startup_time

    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "not_ready",
        "uptime_seconds": round(uptime_seconds, 2),
        "checks": checks,
    }


@app.get("/metrics", tags=["system"], response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    """Expose collected metrics in Prometheus text format."""

    return PlainTextResponse(content=metrics_registry.render(), media_type="text/plain; version=0.0.4")
