"""
LLM-COUNSEL API Server

FastAPI server for the multi-model legal strategy deliberation system.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.config import API_HOST, API_PORT, COUNSEL_TEAM, LEAD_COUNSEL_MODEL, PRESETS
from backend.counsel import CounselDeliberation
from backend.openrouter import cleanup_client
from backend.prompts.personas import get_all_personas, get_persona_display_info
from backend.storage import get_storage
from backend.utils.jurisdiction import get_all_jurisdictions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown
    await cleanup_client()


app = FastAPI(
    title="LLM-COUNSEL",
    description="Multi-Model Legal Strategy Deliberation System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateMatterRequest(BaseModel):
    """Request to create a new matter."""
    matter_name: str | None = Field(None, description="Name of the matter")
    practice_area: str | None = Field(None, description="Practice area (e.g., 'employment')")
    jurisdiction: str | None = Field(None, description="Jurisdiction code (e.g., 'federal')")
    client: str | None = Field(None, description="Client name")


class UpdateMatterRequest(BaseModel):
    """Request to update matter metadata."""
    matter_name: str | None = None
    practice_area: str | None = None
    jurisdiction: str | None = None
    client: str | None = None


class SubmitQuestionRequest(BaseModel):
    """Request to submit a legal question for deliberation."""
    content: str = Field(..., description="The legal question")
    context: str | None = Field(None, description="Additional case context")
    practice_area: str | None = Field(None, description="Override practice area")
    jurisdiction: str | None = Field(None, description="Override jurisdiction")
    stream: bool = Field(False, description="Whether to stream the response")


class MatterSummary(BaseModel):
    """Summary of a matter for listing."""
    id: str
    created_at: str
    updated_at: str
    metadata: dict
    message_count: int


class TeamConfigResponse(BaseModel):
    """Current legal team configuration."""
    counsel_team: list[dict]
    lead_counsel_model: str
    available_personas: list[dict]
    available_jurisdictions: list[dict]
    presets: dict


# ============================================================================
# Health & Config Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "llm-counsel"}


@app.get("/api/config/team", response_model=TeamConfigResponse)
async def get_team_config():
    """Get current legal team configuration and available options."""
    return TeamConfigResponse(
        counsel_team=COUNSEL_TEAM,
        lead_counsel_model=LEAD_COUNSEL_MODEL,
        available_personas=get_persona_display_info(),
        available_jurisdictions=get_all_jurisdictions(),
        presets=PRESETS
    )


@app.get("/api/config/personas")
async def get_personas():
    """Get all available legal personas."""
    return {"personas": get_all_personas()}


@app.get("/api/config/jurisdictions")
async def get_jurisdictions():
    """Get all available jurisdictions."""
    return {"jurisdictions": get_all_jurisdictions()}


# ============================================================================
# Matter CRUD Endpoints
# ============================================================================

@app.get("/api/matters", response_model=list[MatterSummary])
async def list_matters():
    """List all matters."""
    storage = get_storage()
    return storage.list_matters()


@app.post("/api/matters")
async def create_matter(request: CreateMatterRequest):
    """Create a new matter."""
    storage = get_storage()
    matter = storage.create_matter(
        matter_name=request.matter_name,
        practice_area=request.practice_area,
        jurisdiction=request.jurisdiction,
        client=request.client
    )
    return matter


@app.get("/api/matters/{matter_id}")
async def get_matter(matter_id: str):
    """Get a specific matter by ID."""
    storage = get_storage()
    matter = storage.get_matter(matter_id)
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    return matter


@app.put("/api/matters/{matter_id}")
async def update_matter(matter_id: str, request: UpdateMatterRequest):
    """Update a matter's metadata."""
    storage = get_storage()
    updates = request.model_dump(exclude_none=True)
    matter = storage.update_matter(matter_id, updates)
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    return matter


@app.delete("/api/matters/{matter_id}")
async def delete_matter(matter_id: str):
    """Delete a matter."""
    storage = get_storage()
    deleted = storage.delete_matter(matter_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Matter not found")
    return {"status": "deleted", "id": matter_id}


# ============================================================================
# Deliberation Endpoints
# ============================================================================

@app.post("/api/matters/{matter_id}/messages")
async def submit_question(matter_id: str, request: SubmitQuestionRequest):
    """
    Submit a legal question for deliberation.

    This triggers the 3-stage deliberation process:
    1. Stage 1: Initial analyses from all counsel members
    2. Stage 2: Peer assessment and ranking
    3. Stage 3: Lead Counsel strategy synthesis
    """
    storage = get_storage()
    matter = storage.get_matter(matter_id)
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")

    # Use matter metadata as defaults, allow request to override
    practice_area = request.practice_area or matter["metadata"].get("practice_area")
    jurisdiction = request.jurisdiction or matter["metadata"].get("jurisdiction")

    # Add user message
    storage.add_message(
        matter_id=matter_id,
        role="user",
        content=request.content,
        context=request.context
    )

    if request.stream:
        return StreamingResponse(
            stream_deliberation(
                matter_id=matter_id,
                legal_question=request.content,
                context=request.context,
                practice_area=practice_area,
                jurisdiction=jurisdiction
            ),
            media_type="text/event-stream"
        )
    else:
        # Non-streaming deliberation
        engine = CounselDeliberation()
        result = await engine.run_deliberation(
            legal_question=request.content,
            context=request.context,
            practice_area=practice_area,
            jurisdiction=jurisdiction
        )

        # Save assistant response
        storage.add_message(
            matter_id=matter_id,
            role="assistant",
            stage1=result["stage1"],
            stage2=result["stage2"],
            stage3=result["stage3"]
        )

        # Return the result with matter info
        matter = storage.get_matter(matter_id)
        return {
            "matter_id": matter_id,
            "result": result,
            "messages": matter["messages"]
        }


async def stream_deliberation(
    matter_id: str,
    legal_question: str,
    context: str | None,
    practice_area: str | None,
    jurisdiction: str | None
):
    """Generator for streaming deliberation events via SSE."""
    engine = CounselDeliberation()
    storage = get_storage()

    stage1_results = {}
    stage2_results = {}
    stage3_result = {}

    async for event in engine.run_deliberation_stream(
        legal_question=legal_question,
        context=context,
        practice_area=practice_area,
        jurisdiction=jurisdiction
    ):
        event_type = event["type"]
        event_data = event["data"]

        # Track results for saving
        if event_type == "stage1_analysis":
            role = event_data["role"]
            stage1_results[role] = event_data["content"]
        elif event_type == "stage1_complete":
            stage1_results = event_data
        elif event_type == "stage2_complete":
            stage2_results = event_data
        elif event_type == "stage3_complete":
            stage3_result = event_data

        # Send SSE event
        yield f"event: {event_type}\n"
        yield f"data: {json.dumps(event_data)}\n\n"

    # Save the complete response
    storage.add_message(
        matter_id=matter_id,
        role="assistant",
        stage1=stage1_results,
        stage2=stage2_results,
        stage3=stage3_result
    )

    # Send completion event
    yield f"event: complete\n"
    yield f"data: {json.dumps({'matter_id': matter_id})}\n\n"


# ============================================================================
# Quick Deliberation (No Matter Required)
# ============================================================================

class QuickDeliberationRequest(BaseModel):
    """Request for quick deliberation without saving."""
    legal_question: str = Field(..., description="The legal question")
    context: str | None = Field(None, description="Additional context")
    practice_area: str | None = Field(None, description="Practice area")
    jurisdiction: str | None = Field(None, description="Jurisdiction")
    stream: bool = Field(False, description="Stream response")


@app.post("/api/deliberate")
async def quick_deliberate(request: QuickDeliberationRequest):
    """
    Run a quick deliberation without saving to a matter.

    Useful for one-off questions or testing.
    """
    engine = CounselDeliberation()

    if request.stream:
        return StreamingResponse(
            quick_stream_deliberation(
                legal_question=request.legal_question,
                context=request.context,
                practice_area=request.practice_area,
                jurisdiction=request.jurisdiction
            ),
            media_type="text/event-stream"
        )
    else:
        result = await engine.run_deliberation(
            legal_question=request.legal_question,
            context=request.context,
            practice_area=request.practice_area,
            jurisdiction=request.jurisdiction
        )
        return result


async def quick_stream_deliberation(
    legal_question: str,
    context: str | None,
    practice_area: str | None,
    jurisdiction: str | None
):
    """Generator for quick streaming deliberation."""
    engine = CounselDeliberation()

    async for event in engine.run_deliberation_stream(
        legal_question=legal_question,
        context=context,
        practice_area=practice_area,
        jurisdiction=jurisdiction
    ):
        yield f"event: {event['type']}\n"
        yield f"data: {json.dumps(event['data'])}\n\n"

    yield f"event: complete\n"
    yield f"data: {json.dumps({})}\n\n"


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
