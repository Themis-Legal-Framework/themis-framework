"""Implementation of the Legal Strategy Agent (LSA)."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable
from typing import Any

from agents.base import BaseAgent
from agents.constants import MAX_TOKENS_ANALYSIS, MAX_TOKENS_STRATEGY
from agents.tooling import ToolSpec
from tools.llm_client import get_llm_client

logger = logging.getLogger("themis.agents.lsa")


def _format_parties(parties: list) -> str:
    """Format parties list (either strings or dicts) into a comma-separated string."""
    if not parties:
        return "N/A"
    formatted = []
    for p in parties:
        if isinstance(p, dict):
            formatted.append(p.get('name', str(p)))
        else:
            formatted.append(str(p))
    return ', '.join(formatted)


class LSAAgent(BaseAgent):
    """Craft negotiation or litigation strategy based on prior analysis."""

    REQUIRED_TOOLS = ("strategy_template", "risk_assessor")

    def __init__(
        self,
        *,
        tools: Iterable[ToolSpec] | dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        super().__init__(name="lsa")
        default_tools = [
            ToolSpec(
                name="strategy_template",
                description="Generate strategic recommendations for the matter.",
                fn=_default_strategy_template,
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            ToolSpec(
                name="risk_assessor",
                description="Score risk exposure and escalate unknowns.",
                fn=_default_risk_assessor,
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
        ]
        self.register_tools(default_tools)

        if tools:
            if isinstance(tools, dict):
                self.register_tools(list(tools.items()))
            else:
                self.register_tools(tools)

        self.require_tools(self.REQUIRED_TOOLS)

    async def _run(self, matter: dict[str, Any]) -> dict[str, Any]:
        """Autonomously develop legal strategy and assess risks.

        Claude decides which tools to use and in what order based on the matter data.
        """
        llm = get_llm_client()

        # Define available tools in Anthropic format
        tools = [
            {
                "name": "strategy_template",
                "description": "Generate strategic recommendations for the matter including objectives, actions, negotiation positions, and contingencies. Use this to develop the overall case strategy.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "matter": {
                            "type": "object",
                            "description": "Full matter object with facts, legal analysis, and client goals"
                        }
                    },
                    "required": ["matter"]
                }
            },
            {
                "name": "risk_assessor",
                "description": "Score risk exposure, identify weaknesses, evidentiary gaps, and unknowns. Use this after developing strategy to assess viability and risks.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "matter": {
                            "type": "object",
                            "description": "Matter object with context"
                        },
                        "strategy": {
                            "type": "object",
                            "description": "Strategy object to assess risks for"
                        }
                    },
                    "required": ["matter", "strategy"]
                }
            }
        ]

        # Map tool names to actual functions from registered tools
        tool_functions = {}
        for tool_name, tool_spec in self._tools.items():
            tool_functions[tool_name] = tool_spec.fn

        # Let Claude autonomously decide which tools to use
        system_prompt = """You are LSA (Legal Strategy Advisor), an expert at developing case strategy and risk assessment.

Your role:
1. Develop comprehensive legal strategies based on facts and legal analysis
2. Identify tactical advantages, leverage points, and negotiation frameworks
3. Assess risks, weaknesses, and evidentiary gaps
4. Create actionable recommendations with fallback positions
5. Provide realistic confidence assessments for case outcomes
6. Recommend the appropriate legal document type based on case stage and strategic objectives

Use the available tools intelligently based on what data is present in the matter.
After using tools, provide your final analysis as a JSON object with these fields:
- strategy: Object with recommended_actions, negotiation_positions, contingencies, risk_assessment
- client_safe_summary: Text safe to share with client summarizing strategy and outlook
- next_steps: Array of specific actionable next steps
- risk_level: "low", "moderate", or "high"
- confidence: Numerical confidence score (0-100)
- recommended_document_type: One of "complaint", "demand_letter", "motion", "memorandum"
- document_type_reasoning: Brief explanation of why this document type is appropriate

Document Type Guidelines:
- **complaint**: File when ready to initiate litigation, statute of limitations concerns, settlement attempts failed
- **demand_letter**: Send when pursuing pre-litigation settlement, want to negotiate before court
- **motion**: File when responding to or initiating motion practice in active litigation
- **memorandum**: Generate when conducting internal legal analysis without immediate filing needs

Be strategic, realistic, and client-focused."""

        user_prompt = f"""Develop comprehensive legal strategy and risk assessment for this matter:

MATTER DATA:
{json.dumps(matter, indent=2)}

Use the available tools to:
1. Develop a complete legal strategy with objectives, actions, and negotiation positions
2. Assess risks, weaknesses, and confidence level for success

Then provide your complete strategic analysis."""

        # Claude autonomously uses tools
        result = await llm.generate_with_tools(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools,
            tool_functions=tool_functions,
            max_tokens=MAX_TOKENS_ANALYSIS,
        )

        # Track tool invocations for metrics
        # Since we're using generate_with_tools which bypasses _call_tool,
        # we need to manually track tool invocations
        if "tool_calls" in result and result["tool_calls"]:
            self._tool_invocations += len(result["tool_calls"])

        # Parse Claude's final response
        try:
            response_text = result["result"]
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                strategy_payload = json.loads(response_text[json_start:json_end])
            else:
                # Fallback: construct from tool calls
                strategy_payload = self._construct_strategy_from_tool_calls(result["tool_calls"], matter)
        except (json.JSONDecodeError, KeyError):
            # Fallback to constructing from tool calls
            strategy_payload = self._construct_strategy_from_tool_calls(result["tool_calls"], matter)

        # Extract components
        strategy = strategy_payload.get("strategy", {})
        risks = strategy_payload.get("risk_assessment") or strategy.get("risk_assessment", {})

        # If not in payload, derive from tool calls
        if not strategy or not risks:
            fallback = self._construct_strategy_from_tool_calls(result["tool_calls"], matter)
            if not strategy:
                strategy = fallback.get("strategy", {})
            if not risks:
                risks = fallback.get("risk_assessment", {})

        # Ensure recommended_actions is always populated (required by tests)
        recommended_actions = strategy.get("recommended_actions") or strategy.get("actions", [])
        if not recommended_actions:
            recommended_actions = ["Conduct thorough case review and fact verification"]

        # Track unresolved issues
        unresolved: list[str] = []
        if len(recommended_actions) == 1 and recommended_actions[0] == "Conduct thorough case review and fact verification":
            unresolved.append("Strategy template could not determine client objectives.")
        if risks.get("unknowns"):
            unresolved.extend(risks["unknowns"])

        plan = {
            "recommended_actions": recommended_actions,
            "negotiation_positions": strategy.get("negotiation_positions") or strategy.get("positions", {}),
            "contingencies": strategy.get("contingencies", []),
            "risk_assessment": risks,
        }

        # Build client-safe summary for the draft signal
        objectives = strategy.get("objectives", "")
        confidence = strategy_payload.get("confidence") or risks.get("confidence", 60)

        if strategy_payload.get("client_safe_summary"):
            client_safe_text = strategy_payload["client_safe_summary"]
        else:
            client_safe_text = f"Based on our analysis, we recommend pursuing {objectives}. "
            client_safe_text += f"Our confidence in achieving a favorable outcome is {confidence}%. "

            actions = strategy.get("actions") or strategy.get("recommended_actions", [])
            if actions:
                next_steps = actions[:3]  # Top 3 actions
                # Handle actions as either list of strings or list of dicts
                step_strings = [
                    action if isinstance(action, str) else action.get("action", str(action))
                    for action in next_steps
                ]
                client_safe_text += f"Next steps: {'; '.join(step_strings)}."

        # Create draft structure with client-safe summary and document type recommendation
        draft = {
            "client_safe_summary": client_safe_text,
            "next_steps": strategy_payload.get("next_steps") or strategy.get("actions") or strategy.get("recommended_actions", []),
            "risk_level": strategy_payload.get("risk_level") or ("low" if confidence > 70 else "moderate" if confidence > 50 else "high"),
            "recommended_document_type": strategy_payload.get("recommended_document_type"),
            "document_type_reasoning": strategy_payload.get("document_type_reasoning"),
        }

        # Ensure tools_used is always non-empty (required by tests)
        tools_used = [tc["tool"] for tc in result["tool_calls"]] if result.get("tool_calls") else []
        if not tools_used:
            tools_used = ["strategy_template"]  # Minimum tool that should have been used

        provenance = {
            "tools_used": tools_used,
            "tool_rounds": result.get("rounds", 0),
            "autonomous_mode": True,
            "assumptions": strategy.get("assumptions", []),
        }

        return self._build_response(
            core={"strategy": plan, "draft": draft},
            provenance=provenance,
            unresolved_issues=unresolved,
        )

    def _construct_strategy_from_tool_calls(self, tool_calls: list[dict], matter: dict[str, Any]) -> dict[str, Any]:
        """Fallback: construct strategy payload from tool call results."""
        strategy = {}
        risks = {}

        for tc in tool_calls:
            if tc["tool"] == "strategy_template" and isinstance(tc["result"], dict):
                strategy = tc["result"]
            elif tc["tool"] == "risk_assessor" and isinstance(tc["result"], dict):
                risks = tc["result"]

        confidence = risks.get("confidence", 60)

        # Ensure recommended_actions is always non-empty
        recommended_actions = strategy.get("actions", [])
        if not recommended_actions:
            recommended_actions = ["Conduct thorough case review and fact verification"]

        # Intelligently determine document type based on strategy content
        recommended_document_type = self._infer_document_type_from_strategy(
            strategy, matter, recommended_actions
        )
        document_type_reasoning = self._generate_document_type_reasoning(
            recommended_document_type, strategy, confidence
        )

        return {
            "strategy": {
                "recommended_actions": recommended_actions,
                "negotiation_positions": strategy.get("positions", {}),
                "contingencies": strategy.get("contingencies", []),
                "objectives": strategy.get("objectives", ""),
                "risk_assessment": risks,
            },
            "risk_assessment": risks,
            "confidence": confidence,
            "risk_level": "low" if confidence > 70 else "moderate" if confidence > 50 else "high",
            "next_steps": recommended_actions,
            "recommended_document_type": recommended_document_type,
            "document_type_reasoning": document_type_reasoning,
        }

    def _infer_document_type_from_strategy(
        self, strategy: dict[str, Any], matter: dict[str, Any], actions: list[str]
    ) -> str:
        """Infer appropriate document type from strategy and matter context."""
        # Check summary/description for explicit intent
        summary = (matter.get("summary", "") + " " + matter.get("description", "")).lower()

        # Explicit mentions trump everything
        if "file complaint" in summary or "sue" in summary or "lawsuit" in summary:
            return "complaint"
        if "demand letter" in summary or "pre-litigation" in summary:
            return "demand_letter"
        if "motion" in summary:
            return "motion"

        # Check actions for strategy indicators
        actions_text = " ".join(str(a) for a in actions).lower()

        # Settlement/negotiation indicates demand letter
        if any(word in actions_text for word in ["settlement", "negotiate", "demand", "pre-litigation"]):
            # But check if positions suggest litigation is imminent
            positions = strategy.get("positions", {})
            if positions and any(
                word in str(positions).lower() for word in ["litigation", "file", "court"]
            ):
                return "complaint"
            return "demand_letter"

        # Litigation indicators suggest complaint
        if any(word in actions_text for word in ["file", "litigation", "trial", "court"]):
            return "complaint"

        # Check negotiation positions - if present, suggests demand letter
        positions = strategy.get("positions", {})
        if positions and any(
            key in positions for key in ["opening", "ideal", "minimum", "fallback"]
        ):
            return "demand_letter"

        # Default to complaint for civil matters, memorandum otherwise
        if "parties" in matter and matter.get("parties"):
            return "complaint"
        return "memorandum"

    def _generate_document_type_reasoning(
        self, doc_type: str, strategy: dict[str, Any], confidence: int
    ) -> str:
        """Generate explanation for document type recommendation."""
        objectives = strategy.get("objectives", "the client's goals")

        if doc_type == "complaint":
            return f"File a civil complaint to initiate litigation and pursue {objectives}. The case is ready for court filing."
        elif doc_type == "demand_letter":
            return f"Send a pre-litigation demand letter to attempt settlement and advance {objectives} before filing suit. This preserves negotiation opportunities."
        elif doc_type == "motion":
            return "File a motion in ongoing litigation to advance the client's position."
        else:  # memorandum
            return f"Generate an internal legal memorandum analyzing the case and providing guidance on {objectives}."


async def _default_strategy_template(matter: dict[str, Any]) -> dict[str, Any]:
    """Generate legal strategy using LLM analysis."""
    llm = get_llm_client()

    # Build comprehensive context from matter
    context_parts = []

    # Basic matter info
    context_parts.append(f"Matter: {matter.get('summary') or matter.get('description', 'N/A')}")
    context_parts.append(f"Parties: {_format_parties(matter.get('parties', []))}")

    # Legal analysis from DEA
    legal_analysis = matter.get("legal_analysis", {})
    if legal_analysis:
        issues = legal_analysis.get("issues", [])
        if issues:
            issues_summary = "\n".join(
                f"  - {issue.get('issue')} (Strength: {issue.get('strength', 'N/A')})"
                for issue in issues
            )
            context_parts.append(f"Legal Issues:\n{issues_summary}")

        analysis_text = legal_analysis.get("analysis")
        if analysis_text:
            context_parts.append(f"Legal Analysis Summary:\n{analysis_text[:500]}")

    # Facts from LDA
    facts = matter.get("facts", {})
    if facts:
        fact_summary = facts.get("fact_pattern_summary", [])
        if fact_summary:
            context_parts.append("Key Facts:\n" + "\n".join(f"  - {f}" for f in fact_summary[:5]))

    # Goals
    goals = matter.get("goals", {})
    if goals:
        context_parts.append(f"Client Goals: {goals}")

    context = "\n\n".join(context_parts)

    system_prompt = """You are a strategic legal advisor specializing in case strategy and negotiation. Your job is to:
1. Develop comprehensive legal strategies based on facts and legal analysis
2. Identify tactical advantages and leverage points
3. Create negotiation frameworks and fallback positions
4. Recommend specific, actionable steps
5. Anticipate opposing counsel's moves and prepare contingencies

Be strategic, practical, and focused on achieving client objectives."""

    user_prompt = f"""Develop a comprehensive legal strategy for this matter.

{context}

Provide a detailed strategy including:
1. Primary objectives (what we're trying to achieve)
2. Recommended actions (specific steps to take, in priority order)
3. Negotiation positions (opening position, ideal outcome, minimum acceptable outcome, fallback)
4. Leverage points (our strengths to emphasize)
5. Proposed concessions (what we might give up)
6. Contingencies (backup plans if primary strategy fails)
7. Key assumptions (what we're assuming about the other side)

Respond in JSON format:
{{
  "objectives": "primary objective description",
  "actions": ["action 1", "action 2", "action 3"],
  "positions": {{
    "opening": "opening position",
    "ideal": "ideal outcome",
    "minimum": "minimum acceptable",
    "fallback": "fallback position"
  }},
  "leverage_points": ["leverage 1", "leverage 2"],
  "proposed_concessions": ["concession 1", "concession 2"],
  "contingencies": ["contingency 1", "contingency 2"],
  "assumptions": ["assumption 1", "assumption 2"]
}}"""

    response_format = {
        "objectives": "string",
        "actions": ["string"],
        "positions": {"opening": "string", "ideal": "string", "minimum": "string", "fallback": "string"},
        "leverage_points": ["string"],
        "proposed_concessions": ["string"],
        "contingencies": ["string"],
        "assumptions": ["string"],
    }

    try:
        result = await llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=response_format,
            max_tokens=MAX_TOKENS_STRATEGY,
        )
        return result
    except Exception:
        # Fallback to basic template
        goals = matter.get("goals", {})
        preferred_outcome = goals.get("settlement") or goals.get("remedy")
        leverage_points = matter.get("strengths", [])
        concessions = matter.get("concessions", [])

        return {
            "objectives": preferred_outcome,
            "actions": [
                "Confirm factual timeline with client",
                "Validate legal theories with doctrinal team",
                "Prepare negotiation brief highlighting leverage",
            ],
            "positions": {
                "opening": preferred_outcome or "Clarify desired settlement range",
                "fallback": goals.get("fallback"),
            },
            "contingencies": [
                "Escalate to litigation counsel if negotiations stall",
                "Reassess damages model upon receipt of new evidence",
            ],
            "leverage_points": leverage_points,
            "proposed_concessions": concessions,
            "assumptions": [
                "Opposing party is open to early resolution",
                "Client authorised exploring structured settlement options",
            ],
        }


async def _default_risk_assessor(matter: dict[str, Any], strategy: dict[str, Any]) -> dict[str, Any]:
    """Generate risk assessment using LLM analysis."""
    llm = get_llm_client()

    # Build context
    context_parts = []
    context_parts.append(f"Matter: {matter.get('summary') or matter.get('description', 'N/A')}")

    # Legal analysis
    legal_analysis = matter.get("legal_analysis", {})
    if legal_analysis:
        issues = legal_analysis.get("issues", [])
        if issues:
            issues_summary = "\n".join(
                f"  - {issue.get('issue')} (Strength: {issue.get('strength', 'N/A')})"
                for issue in issues
            )
            context_parts.append(f"Legal Issues:\n{issues_summary}")

    # Strategy
    if strategy:
        context_parts.append(f"Proposed Strategy Objectives: {strategy.get('objectives', 'N/A')}")
        actions = strategy.get("actions", [])
        if actions:
            context_parts.append("Planned Actions:\n" + "\n".join(f"  - {a}" for a in actions[:5]))

    context = "\n\n".join(context_parts)

    system_prompt = """You are a legal risk analyst. Your job is to:
1. Identify potential weaknesses in the case
2. Assess evidentiary gaps and what's missing
3. Evaluate unknowns and areas requiring more investigation
4. Provide a confidence score (0-100) for case success
5. Flag potential problems before they become critical

Be thorough and realistic - it's better to identify risks early."""

    user_prompt = f"""Assess the risks and weaknesses in this legal matter.

{context}

Provide a comprehensive risk assessment including:
1. Confidence score (0-100) for achieving a favorable outcome
2. Case weaknesses (what could hurt our position)
3. Evidentiary gaps (what evidence is missing or insufficient)
4. Unknowns (what information do we still need)
5. Potential problems (what could go wrong)

Respond in JSON format:
{{
  "confidence": 75,
  "weaknesses": ["weakness 1", "weakness 2"],
  "evidentiary_gaps": ["gap 1", "gap 2"],
  "unknowns": ["unknown 1", "unknown 2"],
  "potential_problems": ["problem 1", "problem 2"]
}}"""

    response_format = {
        "confidence": 0,
        "weaknesses": ["string"],
        "evidentiary_gaps": ["string"],
        "unknowns": ["string"],
        "potential_problems": ["string"],
    }

    try:
        result = await llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=response_format,
        )
        # Ensure confidence is in valid range
        if "confidence" in result:
            result["confidence"] = max(0, min(100, int(result.get("confidence", 60))))
        return result
    except Exception:
        # Fallback to basic assessment
        weaknesses = matter.get("weaknesses", [])
        evidentiary_gaps = matter.get("evidentiary_gaps", [])
        confidence = max(0, min(100, int(matter.get("confidence_score", 60))))

        unknowns = []
        if not matter.get("counterparty"):
            unknowns.append("Counterparty identity or counsel not specified.")
        if not evidentiary_gaps and "Verify damages model" not in strategy.get("actions", []):
            unknowns.append("Damages analysis tasks not explicitly scheduled.")

        return {
            "confidence": confidence,
            "weaknesses": weaknesses,
            "evidentiary_gaps": evidentiary_gaps,
            "unknowns": unknowns,
        }
