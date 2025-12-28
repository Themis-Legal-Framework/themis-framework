"""Case timeline generator."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from packs.criminal_defense.generators.base import BaseGenerator, Section


class TimelineGenerator(BaseGenerator):
    """Generates chronological case timeline with constitutional flags."""

    template_name = "Case Timeline"

    def sections(self) -> Iterable[Section]:
        yield self._header_section()
        yield self._chronology_section()
        yield self._constitutional_events_section()
        yield self._upcoming_deadlines_section()

    def _header_section(self) -> Section:
        lines = [
            f"Case: {self.matter_name}",
            f"Client: {self.client.get('name', 'Unknown')}",
            f"Case Number: {self.case_number}",
            "",
            "This timeline documents key events in chronological order.",
            "Events with constitutional implications are flagged for motion preparation.",
        ]
        return Section(title="Case Timeline", body="\n".join(lines))

    def _chronology_section(self) -> Section:
        events = self._collect_events()

        if not events:
            return Section(
                title="I. Chronological Events",
                body="No events documented yet. Add events as case develops.",
            )

        lines = [
            "| Date | Event | Constitutional Flag | Source |",
            "|------|-------|---------------------|--------|",
        ]

        for event in events:
            date = event.get("date", "Unknown")
            description = event.get("description", "")
            flag = event.get("flag", "")
            source = event.get("source", "")
            lines.append(f"| {date} | {description} | {flag} | {source} |")

        return Section(title="I. Chronological Events", body="\n".join(lines))

    def _constitutional_events_section(self) -> Section:
        """Highlight events with constitutional implications."""
        events = self._collect_events()
        flagged = [e for e in events if e.get("flag")]

        if not flagged:
            return Section(
                title="II. Constitutional Issues Timeline",
                body="No constitutional issues flagged in timeline.",
            )

        lines = ["Events requiring motion consideration:", ""]
        for event in flagged:
            lines.extend([
                f"**{event.get('date', 'Unknown')}**: {event.get('description', '')}",
                f"   Constitutional Issue: {event.get('flag', '')}",
                f"   Recommended Action: {event.get('action', 'Review for motion')}",
                "",
            ])

        return Section(title="II. Constitutional Issues Timeline", body="\n".join(lines))

    def _upcoming_deadlines_section(self) -> Section:
        lines = [
            "CRITICAL DEADLINES TO TRACK:",
            "",
            "[ ] Motion filing deadline: _____________",
            "[ ] Discovery deadline: _____________",
            "[ ] Preliminary hearing: _____________",
            "[ ] Suppression hearing: _____________",
            "[ ] Trial date: _____________",
            "",
            "STATUTE OF LIMITATIONS:",
            "",
        ]

        # Add SOL tracking for charges
        for charge in self.charges:
            if isinstance(charge, dict):
                description = charge.get("description", "Unknown charge")
                lines.append(f"[ ] {description}: _____________")

        return Section(title="III. Deadlines & Limitations", body="\n".join(lines))

    def _collect_events(self) -> list[dict[str, Any]]:
        """Collect and sort all events from the matter."""
        events: list[dict[str, Any]] = []

        # Add arrest date
        arrest = self.arrest
        if arrest.get("date"):
            event: dict[str, Any] = {
                "date": arrest["date"],
                "description": f"Arrest: {arrest.get('circumstances', 'Arrested')}",
                "source": "Arrest record",
            }

            # Check for constitutional issues at arrest
            if self.matter.get("interrogation", {}).get("was_interrogated"):
                if not self.matter.get("interrogation", {}).get("miranda_given"):
                    event["flag"] = "⚠ Fifth Amendment - No Miranda"
                    event["action"] = "File motion to suppress statements"

            events.append(event)

        # Add search event if applicable
        search = self.matter.get("search_and_seizure", {})
        if search.get("was_search_conducted"):
            search_event: dict[str, Any] = {
                "date": arrest.get("date", "Unknown"),
                "description": f"Search conducted ({search.get('search_type', 'unknown type')})",
                "source": "Police report",
            }

            # Flag potential Fourth Amendment issues
            constitutional_issues = self.matter.get("constitutional_issues", [])
            fourth_issues = [
                i for i in constitutional_issues
                if isinstance(i, dict) and "fourth" in i.get("issue_type", "").lower()
            ]
            if fourth_issues:
                search_event["flag"] = "⚠ Fourth Amendment - Search issue"
                search_event["action"] = "File motion to suppress evidence"

            events.append(search_event)

        # Add interrogation event
        interrogation = self.matter.get("interrogation", {})
        if interrogation.get("was_interrogated"):
            interrog_event: dict[str, Any] = {
                "date": arrest.get("date", "Unknown"),
                "description": f"Interrogation ({interrogation.get('duration', 'unknown duration')})",
                "source": "Interrogation record",
            }

            if not interrogation.get("miranda_given"):
                interrog_event["flag"] = "⚠ Fifth Amendment - Miranda violation"
                interrog_event["action"] = "File motion to suppress statements"

            events.append(interrog_event)

        # Add identification procedure
        identification = self.matter.get("identification", {})
        procedure = identification.get("identification_procedure")
        if procedure and procedure != "none":
            id_event: dict[str, Any] = {
                "date": "Unknown",
                "description": f"Identification procedure: {procedure.replace('_', ' ').title()}",
                "source": "Police report",
            }

            if not identification.get("was_counsel_present"):
                id_event["flag"] = "⚠ Sixth Amendment - No counsel at lineup"
                id_event["action"] = "Challenge identification procedure"

            events.append(id_event)

        # Add discovery received events
        for doc in self.matter.get("discovery_received", []):
            if isinstance(doc, dict) and doc.get("date_received"):
                events.append({
                    "date": doc["date_received"],
                    "description": f"Discovery received: {doc.get('document_type', 'Document')}",
                    "source": "Discovery log",
                })

        # Sort by date
        def parse_date(event: dict[str, Any]) -> str:
            date = event.get("date", "")
            if date and date != "Unknown":
                return date
            return "9999-99-99"  # Put unknown dates at end

        events.sort(key=parse_date)

        return events

    def render_csv(self) -> str:
        """Render timeline as CSV for spreadsheet import."""
        events = self._collect_events()

        lines = ["date,event,constitutional_flag,source,action"]
        for event in events:
            date = event.get("date", "")
            description = event.get("description", "").replace(",", ";")
            flag = event.get("flag", "").replace(",", ";")
            source = event.get("source", "").replace(",", ";")
            action = event.get("action", "").replace(",", ";")
            lines.append(f"{date},{description},{flag},{source},{action}")

        return "\n".join(lines)
