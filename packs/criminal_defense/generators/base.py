"""Base utilities for criminal defense document generators."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class Section:
    """A titled section of a legal document."""

    title: str
    body: str

    def render(self) -> str:
        lines: list[str] = []
        if self.title:
            lines.append(self.title.upper())
            lines.append("=" * len(self.title))
        lines.append(self.body.strip())
        return "\n".join(lines) + "\n"


class BaseGenerator:
    """Base class shared by all criminal defense document generators."""

    template_name: str = ""

    def __init__(self, matter: dict[str, Any], execution_result: dict[str, Any] | None = None):
        self.matter = matter
        self.execution_result = execution_result or {}
        self.artifacts = self.execution_result.get("artifacts", {})

    @property
    def metadata(self) -> dict[str, Any]:
        """Get matter metadata."""
        return self.matter.get("metadata", {})

    @property
    def client(self) -> dict[str, Any]:
        """Get client information."""
        return self.matter.get("client", {})

    @property
    def charges(self) -> list[dict[str, Any]]:
        """Get charges list."""
        return self.matter.get("charges", [])

    @property
    def arrest(self) -> dict[str, Any]:
        """Get arrest information."""
        return self.matter.get("arrest", {})

    @property
    def matter_name(self) -> str:
        """Get formatted matter name."""
        return self.matter.get("matter_name", "Unknown Case")

    @property
    def jurisdiction(self) -> str:
        """Get jurisdiction."""
        return self.metadata.get("jurisdiction", "State")

    @property
    def case_number(self) -> str:
        """Get case number."""
        return self.metadata.get("case_number", "Unknown")

    def sections(self) -> Iterable[Section]:  # pragma: no cover - override hook
        raise NotImplementedError

    def render(self) -> str:
        """Render the complete document."""
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        header = [
            f"Document: {self.template_name or self.__class__.__name__}",
            f"Generated: {timestamp}",
            f"Case: {self.matter_name}",
            f"Case No: {self.case_number}",
            "",
        ]
        body_parts = [section.render() for section in self.sections()]
        footer = [
            "",
            "=" * 80,
            "**ATTORNEY REVIEW REQUIRED** - This is a draft document.",
            "Review and customize before filing or sending.",
        ]
        return "\n".join(header + body_parts + footer)
