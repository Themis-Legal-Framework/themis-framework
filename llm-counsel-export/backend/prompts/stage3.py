"""
Stage 3 Prompt Builder

Builds prompts for the Lead Counsel synthesis stage.
"""
from __future__ import annotations

from backend.prompts.personas import LEAD_COUNSEL_PROMPT, LEGAL_PERSONAS


def build_stage3_prompt(
    legal_question: str,
    stage1_analyses: dict[str, dict],
    stage2_assessments: dict[str, dict],
    aggregate_rankings: list[dict],
    context: str | None = None,
    practice_area: str | None = None,
    jurisdiction: str | None = None
) -> tuple[str, str]:
    """
    Build the system and user prompts for Stage 3 Lead Counsel synthesis.

    Args:
        legal_question: The original legal question
        stage1_analyses: Dict mapping roles to their analyses
        stage2_assessments: Dict mapping roles to their peer evaluations
        aggregate_rankings: List of rankings with scores
        context: Additional case context
        practice_area: The practice area
        jurisdiction: The jurisdiction

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = LEAD_COUNSEL_PROMPT

    # Format Stage 1 analyses with role labels
    analyses_section = "\n## LEGAL TEAM ANALYSES\n"
    for role, analysis_data in stage1_analyses.items():
        persona = LEGAL_PERSONAS.get(role, {})
        display_name = persona.get("display_name", role)
        icon = persona.get("icon", "")
        content = analysis_data.get("content", "")
        model = analysis_data.get("model", "unknown")

        analyses_section += f"""
### {icon} {display_name}
*Model: {model}*

{content}

---
"""

    # Format aggregate rankings
    rankings_section = "\n## AGGREGATE PEER RANKINGS\n"
    rankings_section += "Based on peer assessments, the analyses rank as follows:\n\n"
    for i, rank_info in enumerate(aggregate_rankings, 1):
        role = rank_info.get("role", "unknown")
        persona = LEGAL_PERSONAS.get(role, {})
        display_name = persona.get("display_name", role)
        avg_position = rank_info.get("avg_position", 0)
        rankings_section += f"{i}. **{display_name}** (avg. position: {avg_position:.2f})\n"

    # Format individual peer assessments
    assessments_section = "\n## INDIVIDUAL PEER ASSESSMENTS\n"
    for role, assessment_data in stage2_assessments.items():
        persona = LEGAL_PERSONAS.get(role, {})
        display_name = persona.get("display_name", role)
        evaluation = assessment_data.get("evaluation", "")

        assessments_section += f"""
### Assessment by {display_name}

{evaluation}

---
"""

    # Build context section
    context_parts = []
    if practice_area:
        context_parts.append(f"**Practice Area:** {practice_area}")
    if jurisdiction:
        context_parts.append(f"**Jurisdiction:** {_format_jurisdiction(jurisdiction)}")
    if context:
        context_parts.append(f"\n**Case Context:**\n{context}")

    context_section = "\n".join(context_parts) if context_parts else ""

    user_prompt = f"""# MATTER FOR STRATEGIC SYNTHESIS

{context_section}

## LEGAL QUESTION
{legal_question}

{analyses_section}

{rankings_section}

{assessments_section}

---

## YOUR TASK

As Lead Counsel, synthesize the above analyses and assessments into a comprehensive Legal Strategy Memorandum.

Your memorandum should include:

1. **EXECUTIVE SUMMARY** - Key conclusions and recommended course of action (2-3 paragraphs)

2. **CASE ASSESSMENT**
   - Strengths of our position
   - Weaknesses and risks
   - Likely outcome range

3. **RECOMMENDED STRATEGY**
   - Primary legal theories/defenses to pursue
   - Key arguments synthesized from team analyses
   - Areas of team consensus
   - Resolution of any team disagreements

4. **ACTION ITEMS**
   - Immediate next steps (with specificity)
   - Discovery priorities
   - Motion strategy
   - Settlement considerations

5. **OPEN ISSUES**
   - Areas requiring further research
   - Questions for client
   - Expert consultation needs

Format the memorandum professionally. Be direct and actionable. The client is relying on this guidance."""

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
