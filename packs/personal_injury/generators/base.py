"""Base utilities for document generators."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from packs.personal_injury.schema import PersonalInjuryMatter, matter_summary


@dataclass(slots=True)
class Section:
    title: str
    body: str

    def render(self) -> str:
        lines: list[str] = []
        if self.title:
            lines.append(self.title.upper())
            lines.append("".ljust(len(self.title), "="))
        lines.append(self.body.strip())
        return "\n".join(lines) + "\n"


class BaseGenerator:
    """Base class shared by all document generators."""

    template_name: str = ""

    def __init__(self, matter: PersonalInjuryMatter):
        self.matter = matter

    def sections(self) -> Iterable[Section]:  # pragma: no cover - override hook
        raise NotImplementedError

    def render(self) -> str:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        header = [
            f"Document: {self.template_name or self.__class__.__name__}",
            f"Generated: {timestamp}",
            f"Matter: {self.matter.metadata.title} ({self.matter.metadata.id})",
            "",
        ]
        body_parts = [section.render() for section in self.sections()]
        analytics = [
            "",
            "=== ANALYTICS CONTEXT ===",
            str(matter_summary(self.matter)),
        ]
        return "\n".join(header + body_parts + analytics) + "\n"

    # Convenience helpers -------------------------------------------------
    def party_by_role(self, role: str) -> str:
        for party in self.matter.parties:
            if party.role.lower() == role.lower():
                return party.name
        return "Unknown"

    def format_timeline(self, max_events: int = 10) -> str:
        lines: list[str] = []
        for event in self.matter.fact_pattern.timeline[:max_events]:
            date_text = event.get("date") or ""
            desc = event.get("description") or ""
            lines.append(f"- {date_text} {desc}".strip())
        return "\n".join(lines)

    def list_evidence(self, max_items: int = 10) -> str:
        items = self.matter.fact_pattern.evidence[:max_items]
        return "\n".join(f"- {item}" for item in items)
