# LLM-COUNSEL - Claude Agent Guide

This document provides context for AI agents working with the LLM-COUNSEL legal deliberation system.

## System Overview

LLM-COUNSEL is a multi-model legal strategy deliberation platform that orchestrates multiple AI attorneys to analyze legal questions from different perspectives, peer-review each other's work, and synthesize findings into actionable strategy.

## Architecture

### Three-Stage Deliberation Flow

```
Legal Question → Stage 1 (Initial Analyses) → Stage 2 (Peer Assessment) → Stage 3 (Lead Counsel Strategy)
```

1. **Stage 1**: Multiple AI attorneys (4 by default) analyze the legal question with specialized perspectives
2. **Stage 2**: Each attorney blind-reviews and ranks the anonymized analyses
3. **Stage 3**: Lead Counsel synthesizes everything into a strategy memorandum

### Legal Personas

Available attorney roles in `backend/prompts/personas.py`:

- `plaintiff_strategist` - Aggressive case theory, damages maximization
- `defense_analyst` - Risk assessment, counterarguments
- `procedural_specialist` - Motion strategy, timing, rules
- `evidence_counsel` - Admissibility, discovery, experts
- `appellate_consultant` - Issue preservation, precedent
- `settlement_strategist` - Valuation, negotiation
- `trial_tactician` - Jury strategy, trial presentation
- `regulatory_specialist` - Compliance, agency proceedings

## Development Commands

### Running the Application

```bash
# Start both backend and frontend
./start.sh

# Or start separately:
# Backend (port 8001)
uvicorn backend.main:app --reload --port 8001

# Frontend (port 5173)
cd frontend && npm run dev
```

### API Endpoints

- `GET /api/matters` - List matters
- `POST /api/matters` - Create matter
- `POST /api/matters/{id}/messages` - Submit question (triggers deliberation)
- `POST /api/deliberate` - Quick deliberation without matter
- `GET /api/config/team` - Get team configuration

### Testing

```bash
# Run Python tests
pytest tests/ -v

# Lint
ruff check .
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/counsel.py` | Core 3-stage deliberation engine |
| `backend/config.py` | Team configuration, presets |
| `backend/prompts/personas.py` | Legal persona definitions |
| `backend/prompts/stage1.py` | Initial analysis prompts |
| `backend/prompts/stage2.py` | Peer assessment prompts |
| `backend/prompts/stage3.py` | Lead Counsel synthesis prompts |
| `backend/openrouter.py` | OpenRouter API client |
| `backend/storage.py` | JSON matter persistence |
| `backend/main.py` | FastAPI server |
| `frontend/src/api.js` | Frontend API client |

## Adding New Personas

1. Add persona definition to `backend/prompts/personas.py`:

```python
LEGAL_PERSONAS["new_role"] = {
    "system_prompt": """Your specialized prompt...""",
    "display_name": "Display Name",
    "icon": "emoji",
    "focus_areas": ["area1", "area2"]
}
```

2. Add to `COUNSEL_TEAM` in `backend/config.py` or create a preset

## Modifying Deliberation Behavior

### Change Stage 1 (Initial Analysis)
Edit `backend/prompts/stage1.py` - `build_stage1_prompt()`

### Change Stage 2 (Peer Assessment)
Edit `backend/prompts/stage2.py` - `build_stage2_prompt()`

### Change Stage 3 (Lead Counsel)
Edit `backend/prompts/stage3.py` - `build_stage3_prompt()`

### Change Ranking Logic
Edit `backend/prompts/stage2.py` - `extract_ranking_from_text()`

## Environment Variables

```bash
OPENROUTER_API_KEY=sk-or-v1-...  # Required
API_HOST=0.0.0.0                  # Optional
API_PORT=8001                     # Optional
DATA_DIR=data/conversations       # Optional
```

## Data Storage

Matters stored as JSON in `data/conversations/`:

```json
{
  "id": "matter_abc123",
  "metadata": {
    "matter_name": "Smith v. Acme",
    "practice_area": "employment",
    "jurisdiction": "federal"
  },
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "stage1": {...}, "stage2": {...}, "stage3": {...}}
  ]
}
```

## Frontend Components

| Component | Purpose |
|-----------|---------|
| `App.jsx` | Main app, matter management |
| `Sidebar.jsx` | Matter list navigation |
| `MatterInterface.jsx` | Main deliberation UI |
| `Stage1Display.jsx` | Show attorney analyses |
| `Stage2Display.jsx` | Show peer rankings |
| `Stage3Display.jsx` | Show Lead Counsel memo |

## Integration with Themis Framework

LLM-COUNSEL can integrate with the broader Themis legal AI framework:

- Use DEA analysis as input context
- Feed Stage 3 output to DDA for document drafting
- Connect to matter management in main Themis system

## Best Practices

1. **Clear Questions**: More specific legal questions yield better results
2. **Provide Context**: Include relevant facts, procedural posture, jurisdiction
3. **Review All Stages**: Don't just read Stage 3 - the individual analyses have value
4. **Human Review**: All AI output requires attorney review before use

## Quick Reference

```bash
# Start app
./start.sh

# API docs
open http://localhost:8001/docs

# Frontend
open http://localhost:5173
```
