"""
LLM-COUNSEL Core Deliberation Engine

Implements the 3-stage legal strategy deliberation process:
1. Stage 1: Initial Legal Analyses (multiple attorney perspectives)
2. Stage 2: Peer Assessment (blind review and ranking)
3. Stage 3: Lead Counsel Synthesis (strategy memorandum)
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable

from backend.config import COUNSEL_TEAM, LEAD_COUNSEL_MODEL
from backend.openrouter import get_client
from backend.prompts import (
    build_stage1_prompt,
    build_stage2_prompt,
    build_stage3_prompt,
    get_persona,
)
from backend.prompts.stage2 import create_anonymous_labels, extract_ranking_from_text


class CounselDeliberation:
    """
    Orchestrates the 3-stage legal deliberation process.
    """

    def __init__(
        self,
        counsel_team: list[dict] | None = None,
        lead_counsel_model: str | None = None
    ):
        """
        Initialize the deliberation engine.

        Args:
            counsel_team: List of counsel member configs (defaults to COUNSEL_TEAM)
            lead_counsel_model: Model for Lead Counsel (defaults to LEAD_COUNSEL_MODEL)
        """
        self.counsel_team = counsel_team or COUNSEL_TEAM
        self.lead_counsel_model = lead_counsel_model or LEAD_COUNSEL_MODEL
        self.client = get_client()

    async def run_deliberation(
        self,
        legal_question: str,
        context: str | None = None,
        practice_area: str | None = None,
        jurisdiction: str | None = None,
        on_event: Callable[[str, Any], None] | None = None
    ) -> dict[str, Any]:
        """
        Run the complete 3-stage deliberation process.

        Args:
            legal_question: The legal question to analyze
            context: Additional case context
            practice_area: The practice area
            jurisdiction: The jurisdiction
            on_event: Callback for progress events

        Returns:
            Complete deliberation results with all three stages
        """
        def emit(event_type: str, data: Any = None):
            if on_event:
                on_event(event_type, data)

        # Stage 1: Collect initial analyses
        emit("stage1_start")
        stage1_results = await self.stage1_collect_analyses(
            legal_question=legal_question,
            context=context,
            practice_area=practice_area,
            jurisdiction=jurisdiction,
            on_analysis=lambda role, content: emit("stage1_analysis", {"role": role, "content": content})
        )
        emit("stage1_complete", stage1_results)

        # Stage 2: Peer assessment
        emit("stage2_start")
        stage2_results = await self.stage2_collect_assessments(
            legal_question=legal_question,
            stage1_analyses=stage1_results,
            context=context,
            on_assessment=lambda role, content: emit("stage2_assessment", {"role": role, "content": content})
        )
        emit("stage2_complete", stage2_results)

        # Stage 3: Lead Counsel synthesis
        emit("stage3_start")
        stage3_result = await self.stage3_lead_counsel_strategy(
            legal_question=legal_question,
            stage1_analyses=stage1_results,
            stage2_assessments=stage2_results["assessments"],
            aggregate_rankings=stage2_results["aggregate_rankings"],
            context=context,
            practice_area=practice_area,
            jurisdiction=jurisdiction
        )
        emit("stage3_complete", stage3_result)

        return {
            "stage1": stage1_results,
            "stage2": stage2_results,
            "stage3": stage3_result
        }

    async def run_deliberation_stream(
        self,
        legal_question: str,
        context: str | None = None,
        practice_area: str | None = None,
        jurisdiction: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Run deliberation with streaming events.

        Yields:
            Event dicts with "type" and "data" keys
        """
        # Stage 1
        yield {"type": "stage1_start", "data": None}

        stage1_results = {}
        async for role, content in self._stream_stage1(
            legal_question, context, practice_area, jurisdiction
        ):
            stage1_results[role] = content
            yield {"type": "stage1_analysis", "data": {"role": role, "content": content}}

        yield {"type": "stage1_complete", "data": stage1_results}

        # Stage 2
        yield {"type": "stage2_start", "data": None}

        stage2_results = await self.stage2_collect_assessments(
            legal_question=legal_question,
            stage1_analyses=stage1_results,
            context=context
        )

        for role, assessment in stage2_results["assessments"].items():
            yield {"type": "stage2_assessment", "data": {"role": role, "content": assessment}}

        yield {"type": "stage2_complete", "data": stage2_results}

        # Stage 3 (streaming)
        yield {"type": "stage3_start", "data": None}

        stage3_content = ""
        async for chunk in self._stream_stage3(
            legal_question=legal_question,
            stage1_analyses=stage1_results,
            stage2_assessments=stage2_results["assessments"],
            aggregate_rankings=stage2_results["aggregate_rankings"],
            context=context,
            practice_area=practice_area,
            jurisdiction=jurisdiction
        ):
            stage3_content += chunk
            yield {"type": "stage3_chunk", "data": chunk}

        stage3_result = {
            "model": self.lead_counsel_model,
            "content": stage3_content
        }
        yield {"type": "stage3_complete", "data": stage3_result}

    async def stage1_collect_analyses(
        self,
        legal_question: str,
        context: str | None = None,
        practice_area: str | None = None,
        jurisdiction: str | None = None,
        on_analysis: Callable[[str, dict], None] | None = None
    ) -> dict[str, dict]:
        """
        Stage 1: Collect initial analyses from all counsel members in parallel.

        Args:
            legal_question: The legal question
            context: Case context
            practice_area: Practice area
            jurisdiction: Jurisdiction
            on_analysis: Callback for each completed analysis

        Returns:
            Dict mapping roles to analysis results
        """
        async def get_analysis(counsel: dict) -> tuple[str, dict]:
            role = counsel["role"]
            model = counsel["model"]

            system_prompt, user_prompt = build_stage1_prompt(
                role=role,
                legal_question=legal_question,
                context=context,
                practice_area=practice_area,
                jurisdiction=jurisdiction
            )

            content = await self.client.generate(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=4096
            )

            result = {
                "model": model,
                "content": content,
                "display_name": counsel["display_name"]
            }

            if on_analysis:
                on_analysis(role, result)

            return role, result

        # Run all analyses in parallel
        tasks = [get_analysis(counsel) for counsel in self.counsel_team]
        results = await asyncio.gather(*tasks)

        return dict(results)

    async def _stream_stage1(
        self,
        legal_question: str,
        context: str | None,
        practice_area: str | None,
        jurisdiction: str | None
    ) -> AsyncIterator[tuple[str, dict]]:
        """Stream Stage 1 analyses as they complete."""
        async def get_analysis(counsel: dict) -> tuple[str, dict]:
            role = counsel["role"]
            model = counsel["model"]

            system_prompt, user_prompt = build_stage1_prompt(
                role=role,
                legal_question=legal_question,
                context=context,
                practice_area=practice_area,
                jurisdiction=jurisdiction
            )

            content = await self.client.generate(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=4096
            )

            return role, {
                "model": model,
                "content": content,
                "display_name": counsel["display_name"]
            }

        # Use asyncio.as_completed to yield results as they finish
        tasks = [asyncio.create_task(get_analysis(counsel)) for counsel in self.counsel_team]

        for coro in asyncio.as_completed(tasks):
            role, result = await coro
            yield role, result

    async def stage2_collect_assessments(
        self,
        legal_question: str,
        stage1_analyses: dict[str, dict],
        context: str | None = None,
        on_assessment: Callable[[str, dict], None] | None = None
    ) -> dict[str, Any]:
        """
        Stage 2: Have each counsel member assess and rank the anonymized analyses.

        Args:
            legal_question: The original legal question
            stage1_analyses: Results from Stage 1
            context: Case context
            on_assessment: Callback for each completed assessment

        Returns:
            Dict with "assessments" and "aggregate_rankings"
        """
        # Create anonymous labels for analyses
        analyses_list = [
            {"role": role, "content": data["content"], "model": data["model"]}
            for role, data in stage1_analyses.items()
        ]
        labeled_analyses = create_anonymous_labels(analyses_list)

        # Create label-to-role mapping for later
        label_to_role = {label: info["role"] for label, info in labeled_analyses.items()}

        # Build the anonymized analyses text
        analyses_for_prompt = {
            label: info["content"]
            for label, info in labeled_analyses.items()
        }

        async def get_assessment(counsel: dict) -> tuple[str, dict]:
            role = counsel["role"]
            model = counsel["model"]

            system_prompt, user_prompt = build_stage2_prompt(
                legal_question=legal_question,
                analyses=analyses_for_prompt,
                context=context
            )

            evaluation = await self.client.generate(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.5,
                max_tokens=3000
            )

            # Extract ranking from the evaluation
            valid_labels = list(labeled_analyses.keys())
            ranking = extract_ranking_from_text(evaluation, valid_labels)

            result = {
                "model": model,
                "evaluation": evaluation,
                "ranking": ranking
            }

            if on_assessment:
                on_assessment(role, result)

            return role, result

        # Run all assessments in parallel
        tasks = [get_assessment(counsel) for counsel in self.counsel_team]
        results = await asyncio.gather(*tasks)
        assessments = dict(results)

        # Calculate aggregate rankings
        aggregate_rankings = self._calculate_aggregate_rankings(
            assessments=assessments,
            label_to_role=label_to_role
        )

        return {
            "assessments": assessments,
            "aggregate_rankings": aggregate_rankings,
            "label_mapping": label_to_role
        }

    def _calculate_aggregate_rankings(
        self,
        assessments: dict[str, dict],
        label_to_role: dict[str, str]
    ) -> list[dict]:
        """
        Calculate aggregate rankings across all peer assessments.

        Args:
            assessments: Dict of role -> assessment results
            label_to_role: Mapping of anonymous labels to roles

        Returns:
            List of rankings sorted by average position (best first)
        """
        # Collect position scores for each label
        position_scores: dict[str, list[int]] = {label: [] for label in label_to_role}

        for assessment in assessments.values():
            ranking = assessment.get("ranking", [])
            for position, label in enumerate(ranking, 1):
                if label in position_scores:
                    position_scores[label].append(position)

        # Calculate average positions
        rankings = []
        for label, positions in position_scores.items():
            if positions:
                avg_position = sum(positions) / len(positions)
                rankings.append({
                    "label": label,
                    "role": label_to_role[label],
                    "avg_position": avg_position,
                    "positions": positions
                })

        # Sort by average position (lower is better)
        rankings.sort(key=lambda x: x["avg_position"])

        return rankings

    async def stage3_lead_counsel_strategy(
        self,
        legal_question: str,
        stage1_analyses: dict[str, dict],
        stage2_assessments: dict[str, dict],
        aggregate_rankings: list[dict],
        context: str | None = None,
        practice_area: str | None = None,
        jurisdiction: str | None = None
    ) -> dict[str, Any]:
        """
        Stage 3: Lead Counsel synthesizes all analyses into a strategy memorandum.

        Args:
            legal_question: The original legal question
            stage1_analyses: Stage 1 results
            stage2_assessments: Stage 2 assessment results
            aggregate_rankings: Calculated rankings
            context: Case context
            practice_area: Practice area
            jurisdiction: Jurisdiction

        Returns:
            Lead Counsel strategy result
        """
        system_prompt, user_prompt = build_stage3_prompt(
            legal_question=legal_question,
            stage1_analyses=stage1_analyses,
            stage2_assessments=stage2_assessments,
            aggregate_rankings=aggregate_rankings,
            context=context,
            practice_area=practice_area,
            jurisdiction=jurisdiction
        )

        content = await self.client.generate(
            model=self.lead_counsel_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=6000
        )

        return {
            "model": self.lead_counsel_model,
            "content": content
        }

    async def _stream_stage3(
        self,
        legal_question: str,
        stage1_analyses: dict[str, dict],
        stage2_assessments: dict[str, dict],
        aggregate_rankings: list[dict],
        context: str | None = None,
        practice_area: str | None = None,
        jurisdiction: str | None = None
    ) -> AsyncIterator[str]:
        """Stream Stage 3 Lead Counsel response."""
        system_prompt, user_prompt = build_stage3_prompt(
            legal_question=legal_question,
            stage1_analyses=stage1_analyses,
            stage2_assessments=stage2_assessments,
            aggregate_rankings=aggregate_rankings,
            context=context,
            practice_area=practice_area,
            jurisdiction=jurisdiction
        )

        async for chunk in self.client.generate_stream(
            model=self.lead_counsel_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=6000
        ):
            yield chunk


# Convenience function for simple usage
async def deliberate(
    legal_question: str,
    context: str | None = None,
    practice_area: str | None = None,
    jurisdiction: str | None = None,
    counsel_team: list[dict] | None = None,
    lead_counsel_model: str | None = None
) -> dict[str, Any]:
    """
    Run a legal deliberation with default settings.

    Args:
        legal_question: The legal question to analyze
        context: Additional case context
        practice_area: The practice area
        jurisdiction: The jurisdiction
        counsel_team: Custom counsel team (optional)
        lead_counsel_model: Custom Lead Counsel model (optional)

    Returns:
        Complete deliberation results
    """
    engine = CounselDeliberation(
        counsel_team=counsel_team,
        lead_counsel_model=lead_counsel_model
    )

    return await engine.run_deliberation(
        legal_question=legal_question,
        context=context,
        practice_area=practice_area,
        jurisdiction=jurisdiction
    )
