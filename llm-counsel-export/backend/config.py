"""
LLM-COUNSEL Configuration

Defines the legal team composition and model assignments.
"""
from __future__ import annotations

import os
from typing import TypedDict


class CounselMember(TypedDict):
    """Configuration for a single counsel team member."""
    model: str
    role: str
    display_name: str


# The Legal Team - each model takes a specific attorney role
COUNSEL_TEAM: list[CounselMember] = [
    {
        "model": "anthropic/claude-sonnet-4-20250514",
        "role": "plaintiff_strategist",
        "display_name": "Plaintiff's Strategist"
    },
    {
        "model": "openai/gpt-4o",
        "role": "defense_analyst",
        "display_name": "Defense Analyst"
    },
    {
        "model": "google/gemini-2.0-flash-001",
        "role": "procedural_specialist",
        "display_name": "Procedural Specialist"
    },
    {
        "model": "x-ai/grok-3-beta",
        "role": "evidence_counsel",
        "display_name": "Evidence Counsel"
    },
]

# Lead Counsel - synthesizes final strategy
LEAD_COUNSEL_MODEL = "anthropic/claude-sonnet-4-20250514"

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Server configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8001"))

# Storage configuration
DATA_DIR = os.getenv("DATA_DIR", "data/conversations")


# Preset Legal Team Configurations
PRESETS = {
    "balanced_litigation": {
        "description": "Balanced team for general civil litigation",
        "team": ["plaintiff_strategist", "defense_analyst", "procedural_specialist", "evidence_counsel"],
        "lead_counsel_model": "anthropic/claude-sonnet-4-20250514"
    },
    "plaintiff_aggressive": {
        "description": "Plaintiff-focused aggressive strategy",
        "team": ["plaintiff_strategist", "evidence_counsel", "settlement_strategist", "procedural_specialist"],
        "lead_counsel_model": "anthropic/claude-sonnet-4-20250514"
    },
    "defense_focused": {
        "description": "Defense-oriented risk assessment",
        "team": ["defense_analyst", "procedural_specialist", "appellate_consultant", "settlement_strategist"],
        "lead_counsel_model": "openai/gpt-4o"
    },
    "appellate_prep": {
        "description": "Focus on appellate preservation",
        "team": ["appellate_consultant", "procedural_specialist", "evidence_counsel", "defense_analyst"],
        "lead_counsel_model": "anthropic/claude-sonnet-4-20250514"
    },
    "settlement_evaluation": {
        "description": "Settlement value and negotiation focus",
        "team": ["settlement_strategist", "plaintiff_strategist", "defense_analyst", "evidence_counsel"],
        "lead_counsel_model": "google/gemini-2.0-flash-001"
    }
}
