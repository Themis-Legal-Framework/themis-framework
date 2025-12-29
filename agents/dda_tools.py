"""Default tool implementations for the Document Drafting Agent (DDA).

Contains the default implementations for section generation, citation formatting,
document composition, validation, and tone analysis.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.constants import (
    MAX_DOCUMENT_WORDS,
    MAX_TOKENS_DOCUMENT_GENERATION,
    MAX_TOKENS_SYNTHESIS,
    MAX_TOKENS_TONE_ANALYSIS,
    MAX_WARNINGS_FOR_VALID_DOC,
    MIN_DOCUMENT_WORDS,
    MIN_PARTIES_FOR_DEFENDANT,
    MIN_SECTIONS_FOR_VALID_DOC,
    MIN_SUMMARY_LENGTH,
)
from tools.llm_client import get_llm_client

logger = logging.getLogger("themis.agents.dda.tools")


# Helper functions for defensive type handling
def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get a value from an object that might be a dict or string."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def format_issue(issue: Any) -> str:
    """Format an issue that might be a dict or string."""
    if isinstance(issue, dict):
        return f"  - {issue.get('issue', 'Unknown')} (Strength: {issue.get('strength', 'N/A')})"
    return f"  - {issue}"


def format_event(event: Any) -> str:
    """Format an event that might be a dict or string."""
    if isinstance(event, dict):
        return f"  {event.get('date', 'N/A')}: {event.get('description', 'N/A')}"
    return f"  - {event}"


def format_authority(auth: Any, max_len: int = 100) -> str:
    """Format an authority that might be a dict or string."""
    if isinstance(auth, dict):
        citation = auth.get('citation', auth.get('cite', 'N/A'))
        holding = auth.get('holding', auth.get('summary', 'N/A'))
        if len(holding) > max_len:
            holding = holding[:max_len]
        return f"  - {citation}: {holding}"
    return f"  - {auth}"


def normalise_party_roles(parties: Any) -> dict[str, str]:
    """Map arbitrary party payloads to plaintiff/defendant placeholders."""

    defaults = {"plaintiff": "PLAINTIFF NAME", "defendant": "DEFENDANT NAME"}
    if parties is None:
        return defaults.copy()

    # Direct mapping support
    if isinstance(parties, dict):
        normalised = defaults.copy()
        for role in defaults:
            value = parties.get(role)
            if isinstance(value, str) and value.strip():
                normalised[role] = value.strip()
        if normalised != defaults:
            return normalised

        # Fall back to the first non-empty string values
        names = [str(value).strip() for value in parties.values() if str(value).strip()]
        if names:
            normalised["plaintiff"] = names[0]
            if len(names) >= MIN_PARTIES_FOR_DEFENDANT:
                normalised["defendant"] = names[1]
        return normalised

    # List of parties (strings or dicts)
    if isinstance(parties, list):
        normalised = defaults.copy()
        unnamed: list[str] = []
        for entry in parties:
            if isinstance(entry, str):
                name = entry.strip()
                if name:
                    unnamed.append(name)
                continue
            if isinstance(entry, dict):
                name_field = entry.get("name") or entry.get("party") or entry.get("full_name")
                role_field = entry.get("role") or entry.get("type") or entry.get("side")
                if isinstance(role_field, str) and isinstance(name_field, str):
                    role_lower = role_field.lower()
                    name = name_field.strip()
                    if not name:
                        continue
                    if any(tag in role_lower for tag in ("plaintiff", "claimant", "petitioner")):
                        normalised["plaintiff"] = name
                        continue
                    if any(tag in role_lower for tag in ("defendant", "respondent", "accused")):
                        normalised["defendant"] = name
                        continue
                    unnamed.append(name)
                    continue
                if isinstance(name_field, str) and name_field.strip():
                    unnamed.append(name_field.strip())
                continue
            if entry is not None:
                entry_str = str(entry).strip()
                if entry_str:
                    unnamed.append(entry_str)
        if normalised["plaintiff"] == defaults["plaintiff"] and unnamed:
            normalised["plaintiff"] = unnamed[0]
        if normalised["defendant"] == defaults["defendant"] and len(unnamed) >= MIN_PARTIES_FOR_DEFENDANT:
            normalised["defendant"] = unnamed[1]
        return normalised

    if isinstance(parties, str) and parties.strip():
        return {"plaintiff": parties.strip(), "defendant": defaults["defendant"]}

    return defaults.copy()


async def default_section_generator(
    document_type: str,
    facts: dict[str, Any],
    legal_analysis: dict[str, Any],
    strategy: dict[str, Any],
    jurisdiction: str,
) -> dict[str, Any]:
    """Generate document sections using LLM with modern legal prose."""
    llm = get_llm_client()

    # Build context from matter data
    context_parts = []

    # Facts
    if facts:
        fact_pattern = facts.get("fact_pattern_summary", [])
        logger.debug(f"section_generator received {len(fact_pattern)} facts")
        if fact_pattern:
            context_parts.append("Facts:\n" + "\n".join(f"  - {f}" for f in fact_pattern))

        parties = facts.get("parties", {})
        if parties:
            context_parts.append(f"Parties: {parties}")

        timeline = facts.get("timeline", [])
        if timeline:
            timeline_summary = "\n".join(format_event(event) for event in timeline[:10])
            context_parts.append(f"Timeline:\n{timeline_summary}")

    # Legal analysis
    if legal_analysis:
        issues = legal_analysis.get("issues", [])
        if issues:
            issues_summary = "\n".join(format_issue(issue) for issue in issues)
            context_parts.append(f"Legal Issues:\n{issues_summary}")

        analysis = legal_analysis.get("analysis")
        if analysis:
            context_parts.append(f"Legal Analysis:\n{analysis[:1000]}")

        authorities = legal_analysis.get("authorities", [])
        if authorities:
            auth_summary = "\n".join(format_authority(auth) for auth in authorities[:5])
            context_parts.append(f"Key Authorities:\n{auth_summary}")

    # Strategy
    if strategy:
        objectives = strategy.get("objectives")
        if objectives:
            context_parts.append(f"Strategic Objectives: {objectives}")

        positions = strategy.get("positions", {})
        if positions:
            context_parts.append(f"Negotiation Position: {positions}")

    context = "\n\n".join(context_parts)

    # Document type-specific system prompts
    system_prompts = {
        "complaint": """You are an expert legal writer specializing in civil complaints. Write using modern legal prose that is:
- Clear and concise (plain language movement principles)
- Properly structured (caption, jurisdiction, parties, facts, causes of action, prayer)
- Factually grounded and persuasive
- Compliant with pleading standards (notice pleading or fact pleading as appropriate)
- Free of legalese and unnecessary Latin phrases""",

        "demand_letter": """You are an expert legal writer specializing in demand letters. Write using modern legal prose that is:
- Professional but accessible
- Persuasive and fact-focused
- Clear about demands and consequences
- Free of unnecessary legalese
- Appropriate for settlement negotiations""",

        "motion": """You are an expert legal writer specializing in motions and briefs. Write using modern legal prose that is:
- Persuasive and well-organized (IRAC or similar structure)
- Grounded in controlling authority
- Clear and compelling
- Compliant with local rules and page limits
- Free of hyperbole and unnecessary adjectives""",

        "memorandum": """You are an expert legal writer specializing in legal memoranda. Write using modern legal prose that is:
- Objective and analytical
- Well-structured (Question Presented, Brief Answer, Facts, Discussion, Conclusion)
- Thoroughly researched with proper citations
- Clear and accessible
- Balanced in presenting both sides""",

        "client_letter": """You are an expert legal writer specializing in client communications. Write a professional legal letter that is:
- Clear, accessible, and free of unnecessary legal jargon
- Properly addressed to the client with professional salutation and closing
- Organized with clear headings for each major issue
- Analytical in applying relevant legal standards to the facts
- Provides clear recommendations and next steps
- Maintains appropriate attorney-client relationship tone
- Does NOT include a statement of facts unless specifically requested""",
    }

    system_prompt = system_prompts.get(
        document_type,
        system_prompts["memorandum"],  # Default to memo style
    )

    # Single flexible prompt that lets the LLM determine structure based on document type and jurisdiction
    user_prompt = f"""Generate a complete, professional {document_type} appropriate for {jurisdiction} jurisdiction.

MATTER INFORMATION:
{context}

INSTRUCTIONS:
You are an expert legal writer. Generate a court-ready, professional {document_type} that:

1. Follows all formatting, pleading, and procedural requirements for {jurisdiction} jurisdiction
2. Uses proper legal citations and statutory references for this jurisdiction
3. Includes all required sections and elements for this document type in this jurisdiction
4. Uses modern legal prose (clear, concise, plain language where appropriate)
5. Is detailed, specific, and ready for filing or sending without revision
6. Includes proper attorney signature blocks, verification if required, and any jurisdiction-specific formalities

For the facts, legal issues, and strategy provided, determine:
- What structure this document type requires in this jurisdiction
- What sections are mandatory vs. optional
- What citations, statutes, and procedural rules apply
- What tone is appropriate (objective for memos, persuasive for complaints/motions, firm for demand letters)
- What specific language, forms, or boilerplate this jurisdiction expects

Generate a complete {document_type} that an attorney could file or send immediately.

Return the document as a single complete text in the 'full_document' field."""

    response_format = {
        "full_document": "string",
    }

    try:
        result = await llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=response_format,
            max_tokens=MAX_TOKENS_DOCUMENT_GENERATION,
        )

        logger.debug(f"Document generator response keys: {list(result.keys())}")

        # Handle case where LLM wraps response in 'response' key
        if 'response' in result and isinstance(result['response'], str):
            try:
                result = json.loads(result['response'])
                logger.debug("Parsed nested JSON from 'response' key")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse nested JSON: {result['response'][:200]}")

        # Log document preview if we got it
        if result.get('full_document'):
            doc_preview = result['full_document'][:200].replace('\n', ' ')
            logger.debug(f"Generated {document_type} document ({len(result['full_document'])} chars): {doc_preview}...")

        return result
    except Exception as e:
        logger.error(f"Document generator LLM call failed: {e!s}", exc_info=True)

        # Fallback to basic document generation
        fact_pattern = facts.get("fact_pattern_summary", [])
        facts_text = "\n\n".join(fact_pattern) if fact_pattern else "Facts to be provided."

        issues = legal_analysis.get("issues", [])
        def format_issue_analysis(issue):
            if isinstance(issue, dict):
                return f"{issue.get('issue', 'Issue')}: {issue.get('analysis', 'Analysis pending.')}"
            return str(issue)
        issues_text = "\n\n".join(
            format_issue_analysis(issue) for issue in issues
        ) if issues else "Legal analysis to be provided."

        fallback_doc = f"""
{document_type.upper()}

This {document_type} addresses the legal issues arising from the facts presented below.

FACTS:
{facts_text}

LEGAL ANALYSIS:
{issues_text}

CONCLUSION:
For the foregoing reasons, the relief requested should be granted.

[Attorney Signature Block]
"""

        return {"full_document": fallback_doc.strip()}


async def default_citation_formatter(
    authorities: list[dict[str, Any]],
    jurisdiction: str,
) -> dict[str, Any]:
    """Format legal citations according to jurisdiction standards."""
    llm = get_llm_client()

    if not authorities:
        return {"citations": [], "formatted_count": 0}

    # Build authority list
    authority_list = "\n".join(
        f"{i+1}. {format_authority(auth, max_len=200)}"
        for i, auth in enumerate(authorities[:20])  # Limit to 20 authorities
    )

    system_prompt = """You are a legal citation expert specializing in Bluebook and jurisdiction-specific citation formats. Your job is to:
1. Format citations according to Bluebook standards (or jurisdiction-specific rules)
2. Include proper pin-cites and parentheticals
3. Use proper short forms and id. references
4. Ensure consistency across all citations
5. Add explanatory parentheticals where helpful"""

    user_prompt = f"""Format the following legal authorities according to proper citation standards for {jurisdiction} jurisdiction:

{authority_list}

For each authority, provide:
1. Full citation (first reference)
2. Short citation (subsequent references)
3. Explanatory parenthetical (if helpful)

Respond in JSON format:
{{
  "citations": [
    {{
      "full_citation": "complete Bluebook citation",
      "short_citation": "id. or short form",
      "parenthetical": "explanatory parenthetical if needed",
      "case_name": "case name",
      "holding": "brief holding summary"
    }}
  ]
}}"""

    response_format = {
        "citations": [
            {
                "full_citation": "string",
                "short_citation": "string",
                "parenthetical": "string",
                "case_name": "string",
                "holding": "string",
            }
        ]
    }

    try:
        result = await llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=response_format,
            max_tokens=MAX_TOKENS_SYNTHESIS,
        )
        result["formatted_count"] = len(result.get("citations", []))
        return result
    except Exception:
        # Fallback to basic formatting
        citations = []
        for auth in authorities:
            if isinstance(auth, dict):
                citation = auth.get("citation", auth.get("cite", "Citation not available"))
                citations.append({
                    "full_citation": citation,
                    "short_citation": "Id.",
                    "parenthetical": "",
                    "case_name": auth.get("case_name", ""),
                    "holding": auth.get("holding", auth.get("summary", "")),
                })
            else:
                citations.append({
                    "full_citation": str(auth),
                    "short_citation": "Id.",
                    "parenthetical": "",
                    "case_name": "",
                    "holding": "",
                })
        return {"citations": citations, "formatted_count": len(citations)}


async def default_document_composer(
    document_type: str,
    sections: dict[str, Any],
    jurisdiction: str,
    citations: dict[str, Any] | None = None,
    matter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble complete legal document from sections."""
    # Handle optional arguments with defaults
    if citations is None:
        citations = {}
    if matter is None:
        matter = {}

    # Document header
    parties = normalise_party_roles(matter.get("parties"))
    plaintiff = parties.get("plaintiff", "PLAINTIFF NAME")
    defendant = parties.get("defendant", "DEFENDANT NAME")

    metadata = matter.get("metadata", {})

    case_number = None
    if isinstance(metadata, dict):
        case_number = metadata.get("case_number") or metadata.get("docket_number")
    if not case_number:
        case_number = matter.get("case_number")
    case_number = case_number or "No. XX-XXXX"

    court = None
    if isinstance(metadata, dict):
        court = metadata.get("court") or metadata.get("jurisdiction")
    if not court:
        court = matter.get("court") or matter.get("jurisdiction")
    court = court or "COURT NAME"

    # If LLM returned a complete document, use it directly
    if sections.get("full_document"):
        full_text = sections["full_document"]
    else:
        # Fallback: try to assemble from sections
        # This handles the 'response' wrapper case and legacy formats
        parts = []

        # Try to extract any sections we have
        for key in ["caption", "header", "heading", "introduction", "parties_section",
                    "jurisdiction_venue_section", "general_allegations", "facts", "facts_section",
                    "liability", "causes_of_action", "argument", "argument_section",
                    "damages", "damages_section", "prayer", "conclusion",
                    "jury_demand", "signature", "signature_block"]:
            value = sections.get(key)
            if value and isinstance(value, str):
                parts.append(value.strip())
                parts.append("\n\n")

        # If we have some parts, assemble them
        if parts:
            full_text = "".join(parts)
        else:
            # Ultimate fallback: generate a basic document
            parts = []
            parties = normalise_party_roles(matter.get("parties"))
            plaintiff = parties.get("plaintiff", "PLAINTIFF NAME")
            defendant = parties.get("defendant", "DEFENDANT NAME")

            parts.append(f"{court}\n\n")
            parts.append(f"{plaintiff},\n    Plaintiff,\nv.                                  {case_number}\n{defendant},\n    Defendant.\n\n")

            title_map = {
                "complaint": "COMPLAINT",
                "demand_letter": "DEMAND LETTER",
                "motion": "MOTION",
                "memorandum": "MEMORANDUM OF LAW",
            }
            title = title_map.get(document_type, "LEGAL DOCUMENT")
            parts.append(f"{title}\n")
            parts.append("=" * len(title))
            parts.append("\n\n")

            parts.append("[Document content to be generated]\n\n")

            attorney_name = matter.get("attorney_name", "[Attorney Name]")
            attorney_bar = matter.get("attorney_bar_number", "[Bar Number]")
            firm_name = matter.get("firm_name", "[Law Firm]")

            parts.append(f"Respectfully submitted,\n\n________________________\n{attorney_name}\n{firm_name}\nBar No. {attorney_bar}\n")

            full_text = "".join(parts)

    # Calculate metrics
    word_count = len(full_text.split())
    page_estimate = word_count // 250  # Rough estimate: 250 words/page

    return {
        "full_text": full_text,
        "word_count": word_count,
        "page_estimate": page_estimate,
        "sections": list(sections.keys()),
        "citation_count": citations.get("formatted_count", 0),
    }


async def default_document_validator(
    document: dict[str, Any],
    document_type: str,
    matter: dict[str, Any],
) -> dict[str, Any]:
    """Validate document completeness and compliance."""

    full_text = document.get("full_text", "")
    missing_elements = []
    warnings = []

    # Check required elements by document type
    required_elements = {
        "complaint": [
            ("caption", ["plaintiff", "defendant", "v."]),
            ("jurisdiction", ["jurisdiction"]),
            ("facts", ["factual background", "facts"]),
            ("causes_of_action", ["cause of action", "claim", "count"]),
            ("prayer", ["prayer", "wherefore", "relief"]),
        ],
        "demand_letter": [
            ("introduction", ["demand", "settlement"]),
            ("facts", ["facts", "incident"]),
            ("damages", ["damages", "injury", "loss"]),
            ("demand_amount", ["$", "amount", "settlement"]),
        ],
        "motion": [
            ("caption", ["plaintiff", "defendant"]),
            ("introduction", ["motion", "moves"]),
            ("argument", ["argument", "analysis"]),
            ("conclusion", ["conclusion", "wherefore"]),
        ],
        "memorandum": [
            ("facts", ["facts", "factual"]),
            ("analysis", ["analysis", "discussion"]),
            ("conclusion", ["conclusion"]),
        ],
    }

    required = required_elements.get(document_type, [])
    full_text_lower = full_text.lower()

    for element_name, keywords in required:
        if not any(keyword in full_text_lower for keyword in keywords):
            missing_elements.append(element_name)

    # Check document length
    word_count = document.get("word_count", 0)
    if word_count < MIN_DOCUMENT_WORDS:
        warnings.append(f"Document appears too short (< {MIN_DOCUMENT_WORDS} words)")
    elif word_count > MAX_DOCUMENT_WORDS:
        warnings.append(f"Document may be too long (> {MAX_DOCUMENT_WORDS:,} words)")

    # Check for placeholder text
    placeholders = ["[", "TODO", "TBD", "XXXX", "N/A"]
    for placeholder in placeholders:
        if placeholder in full_text:
            warnings.append(f"Document contains placeholder text: {placeholder}")

    is_valid = len(missing_elements) == 0 and len(warnings) < MAX_WARNINGS_FOR_VALID_DOC

    return {
        "is_valid": is_valid,
        "missing_elements": missing_elements,
        "warnings": warnings,
        "completeness_score": max(0, 100 - (len(missing_elements) * 20) - (len(warnings) * 5)),
    }


async def default_tone_analyzer(
    document: dict[str, Any],
    document_type: str,
) -> dict[str, Any]:
    """Analyze legal writing quality and tone appropriateness."""
    llm = get_llm_client()

    full_text = document.get("full_text", "")

    if not full_text or len(full_text) < MIN_SUMMARY_LENGTH:
        return {
            "overall_score": 0,
            "issues": ["Document too short to analyze"],
            "strengths": [],
            "recommendations": ["Generate complete document before analysis"],
        }

    # Sample text for analysis (first 2000 chars to stay within token limits)
    sample_text = full_text[:2000]

    system_prompt = """You are a legal writing expert specializing in modern legal prose. Analyze legal documents for:
1. Clarity and conciseness
2. Appropriate tone for document type
3. Plain language usage (avoiding unnecessary legalese)
4. Proper structure and organization
5. Persuasiveness (for advocacy documents) or objectivity (for memos)
6. Grammar and professionalism

Provide constructive feedback focused on modern legal writing best practices."""

    user_prompt = f"""Analyze this {document_type} excerpt for legal writing quality:

{sample_text}

Provide:
1. Overall quality score (0-100)
2. Specific issues or weaknesses
3. Strengths and positive aspects
4. Recommendations for improvement

Respond in JSON format:
{{
  "overall_score": 85,
  "issues": ["issue 1", "issue 2"],
  "strengths": ["strength 1", "strength 2"],
  "recommendations": ["recommendation 1", "recommendation 2"]
}}"""

    response_format = {
        "overall_score": 0,
        "issues": ["string"],
        "strengths": ["string"],
        "recommendations": ["string"],
    }

    try:
        result = await llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=response_format,
            max_tokens=MAX_TOKENS_TONE_ANALYSIS,
        )
        # Ensure score is in valid range
        if "overall_score" in result:
            result["overall_score"] = max(0, min(100, int(result.get("overall_score", 60))))
        return result
    except Exception:
        # Fallback to basic analysis
        word_count = document.get("word_count", 0)
        has_sections = len(document.get("sections", [])) > MIN_SECTIONS_FOR_VALID_DOC

        score = 60
        if has_sections:
            score += 10
        if word_count > 500:
            score += 10

        return {
            "overall_score": score,
            "issues": ["Unable to perform detailed tone analysis"],
            "strengths": ["Document structure appears reasonable"] if has_sections else [],
            "recommendations": ["Review for clarity and conciseness", "Ensure proper citation format"],
        }
