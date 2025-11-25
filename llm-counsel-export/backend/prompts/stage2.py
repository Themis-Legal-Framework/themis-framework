"""
Stage 2 Prompt Builder

Builds prompts for the peer assessment stage.
"""
from __future__ import annotations


def build_stage2_prompt(
    legal_question: str,
    analyses: dict[str, str],
    context: str | None = None
) -> tuple[str, str]:
    """
    Build the system and user prompts for Stage 2 peer assessment.

    Args:
        legal_question: The original legal question
        analyses: Dict mapping anonymous labels (A, B, C...) to analysis text
        context: Additional case context

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = """You are a senior litigation partner reviewing associate memos for quality and strategic value.

Your task is to evaluate multiple legal analyses on the following criteria:
1. **Legal Accuracy** - Is the analysis legally sound? Are citations and legal principles correct?
2. **Strategic Merit** - Does this analysis advance the client's position effectively?
3. **Risk Assessment** - Are risks and weaknesses properly identified and addressed?
4. **Practical Viability** - Can these recommendations be executed effectively?
5. **Persuasiveness** - Would this analysis convince a judge, jury, or opposing counsel?

Be critical but fair. Identify both strengths and weaknesses in each analysis. Your evaluation will help determine which strategies to prioritize."""

    # Build the analyses section
    analyses_text = ""
    for label, content in sorted(analyses.items()):
        analyses_text += f"\n{'='*60}\nANALYSIS {label}\n{'='*60}\n{content}\n"

    context_section = f"\nCase Context:\n{context}\n" if context else ""

    user_prompt = f"""Please evaluate the following anonymized legal analyses for this matter.

LEGAL QUESTION:
{legal_question}
{context_section}
{analyses_text}

For each analysis, provide:
1. A brief evaluation of its strengths and weaknesses
2. Assessment on the five criteria (Legal Accuracy, Strategic Merit, Risk Assessment, Practical Viability, Persuasiveness)
3. Notable insights or concerns

After evaluating all analyses, provide your ranking from best to worst.

End your response with a clearly formatted ranking:

FINAL RANKING:
1. Analysis [X] - Best overall (brief reason)
2. Analysis [Y] - (brief reason)
3. Analysis [Z] - (brief reason)
... and so on for all analyses"""

    return system_prompt, user_prompt


def create_anonymous_labels(analyses: list[dict]) -> dict[str, dict]:
    """
    Create anonymous labels for analyses.

    Args:
        analyses: List of analysis dicts with "role" and "content" keys

    Returns:
        Dict mapping labels (A, B, C...) to analysis info
    """
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    labeled = {}

    for i, analysis in enumerate(analyses):
        if i >= len(labels):
            break
        labeled[labels[i]] = {
            "role": analysis["role"],
            "content": analysis["content"],
            "model": analysis.get("model", "unknown")
        }

    return labeled


def extract_ranking_from_text(text: str, valid_labels: list[str]) -> list[str]:
    """
    Extract ranking from evaluator's response text.

    Args:
        text: The full evaluation text
        valid_labels: List of valid analysis labels (e.g., ["A", "B", "C", "D"])

    Returns:
        Ordered list of labels from best to worst
    """
    import re

    # Look for FINAL RANKING section
    ranking_section = ""
    if "FINAL RANKING:" in text.upper():
        parts = text.upper().split("FINAL RANKING:")
        if len(parts) > 1:
            ranking_section = parts[1]
    elif "RANKING:" in text.upper():
        parts = text.upper().split("RANKING:")
        if len(parts) > 1:
            ranking_section = parts[1]
    else:
        # Use the last part of the text
        ranking_section = text[-500:]

    # Extract labels in order
    ranking = []
    # Look for patterns like "1. Analysis A" or "1. A" or "#1: A"
    pattern = r'(?:\d+[\.\)\:]?\s*)?(?:Analysis\s+)?([A-Z])(?:\s*[-–—]|\s*$|\s*\()'

    for match in re.finditer(pattern, ranking_section, re.IGNORECASE):
        label = match.group(1).upper()
        if label in valid_labels and label not in ranking:
            ranking.append(label)

    # If we didn't find all labels, try a simpler pattern
    if len(ranking) < len(valid_labels):
        simple_pattern = r'\b([A-Z])\b'
        for match in re.finditer(simple_pattern, ranking_section):
            label = match.group(1).upper()
            if label in valid_labels and label not in ranking:
                ranking.append(label)

    # Add any missing labels at the end (shouldn't happen with good LLM output)
    for label in valid_labels:
        if label not in ranking:
            ranking.append(label)

    return ranking[:len(valid_labels)]
