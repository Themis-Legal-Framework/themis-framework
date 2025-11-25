"""
Stage 1 Prompt Builder

Builds prompts for the initial legal analysis stage.
"""
from __future__ import annotations

from backend.prompts.personas import get_persona


def build_stage1_prompt(
    role: str,
    legal_question: str,
    context: str | None = None,
    practice_area: str | None = None,
    jurisdiction: str | None = None
) -> tuple[str, str]:
    """
    Build the system and user prompts for Stage 1 analysis.

    Args:
        role: The attorney role identifier
        legal_question: The legal question to analyze
        context: Additional case context
        practice_area: The practice area (e.g., "employment")
        jurisdiction: The jurisdiction (e.g., "federal", "ca_state")

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    persona = get_persona(role)
    if not persona:
        raise ValueError(f"Unknown attorney role: {role}")

    system_prompt = persona["system_prompt"]

    # Build context section
    context_parts = []
    if practice_area:
        context_parts.append(f"Practice Area: {practice_area}")
    if jurisdiction:
        context_parts.append(f"Jurisdiction: {_format_jurisdiction(jurisdiction)}")
    if context:
        context_parts.append(f"\nCase Context:\n{context}")

    context_section = "\n".join(context_parts) if context_parts else ""

    user_prompt = f"""Please provide your legal analysis of the following matter.

{context_section}

LEGAL QUESTION:
{legal_question}

Provide a thorough analysis from your perspective as {persona['display_name']}. Focus on your areas of expertise: {', '.join(persona['focus_areas'])}.

Structure your analysis clearly with headings and be specific in your recommendations. Cite relevant authority where applicable."""

    return system_prompt, user_prompt


def _format_jurisdiction(jurisdiction: str) -> str:
    """Format jurisdiction code to readable string."""
    jurisdiction_map = {
        "federal": "Federal Court",
        "ca_state": "California State Court",
        "ny_state": "New York State Court",
        "tx_state": "Texas State Court",
        "fl_state": "Florida State Court",
        "il_state": "Illinois State Court",
        "9th_circuit": "Ninth Circuit",
        "2nd_circuit": "Second Circuit",
        "5th_circuit": "Fifth Circuit",
    }
    return jurisdiction_map.get(jurisdiction, jurisdiction)
