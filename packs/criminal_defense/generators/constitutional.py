"""Constitutional issues analysis generator."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from packs.criminal_defense.generators.base import BaseGenerator, Section


class ConstitutionalAnalysisGenerator(BaseGenerator):
    """Generates constitutional issues analysis memo."""

    template_name = "Constitutional Issues Analysis"

    def sections(self) -> Iterable[Section]:
        yield self._header_section()
        yield self._fourth_amendment_section()
        yield self._fifth_amendment_section()
        yield self._sixth_amendment_section()
        yield self._other_issues_section()
        yield self._recommendations_section()

    def _header_section(self) -> Section:
        lines = [
            f"Case: {self.matter_name}",
            f"Client: {self.client.get('name', 'Unknown')}",
            f"Charges: {self._format_charges()}",
            "",
            "This memorandum analyzes potential constitutional issues that may form ",
            "the basis for suppression motions or other defense strategies.",
        ]
        return Section(title="Constitutional Analysis Memo", body="\n".join(lines))

    def _format_charges(self) -> str:
        charges = self.charges
        if not charges:
            return "Unknown"
        descriptions = [c.get("description", "Unknown") for c in charges if isinstance(c, dict)]
        return "; ".join(descriptions[:3]) + ("..." if len(descriptions) > 3 else "")

    def _fourth_amendment_section(self) -> Section:
        lines: list[str] = []
        issues = self._get_issues_by_type("fourth")

        # Analyze stop/seizure
        arrest = self.arrest
        circumstances = arrest.get("circumstances", "")
        if circumstances:
            lines.extend([
                "A. Initial Stop Analysis",
                "",
                f"Stated basis for stop: {circumstances}",
                "",
                "Questions to investigate:",
                "  - Was there reasonable suspicion for the stop?",
                "  - Did officers have specific, articulable facts?",
                "  - Was the stop pretextual?",
                "",
            ])

        # Analyze search
        search = self.matter.get("search_and_seizure", {})
        if search.get("was_search_conducted"):
            search_type = search.get("search_type", "unknown")
            lines.extend([
                "B. Search Analysis",
                "",
                f"Search type: {search_type.replace('_', ' ').title()}",
                "",
            ])

            if search_type == "warrant":
                lines.extend([
                    "Warrant issues to investigate:",
                    "  - Was the affidavit truthful and not recklessly false?",
                    "  - Did probable cause exist?",
                    "  - Was the warrant properly executed?",
                    "",
                ])
            elif search_type == "consent":
                lines.extend([
                    "Consent issues to investigate:",
                    "  - Was consent voluntary?",
                    "  - Was consent given by someone with authority?",
                    "  - Was the scope of consent exceeded?",
                    "",
                ])
            elif search_type == "incident_to_arrest":
                lines.extend([
                    "Search incident to arrest issues:",
                    "  - Was the underlying arrest lawful?",
                    "  - Was the search contemporaneous with arrest?",
                    "  - Was the search within permissible scope?",
                    "",
                ])

        # Add identified issues
        if issues:
            lines.append("C. Identified Fourth Amendment Issues")
            lines.append("")
            for issue in issues:
                lines.append(f"  ISSUE: {issue.get('description', 'Unknown')}")
                evidence = issue.get("evidence", [])
                if evidence:
                    lines.append("  Evidence:")
                    for e in evidence:
                        lines.append(f"    - {e}")
                lines.append("")

        if not lines:
            lines = ["No specific Fourth Amendment issues identified at this time."]

        return Section(title="I. Fourth Amendment (Search & Seizure)", body="\n".join(lines))

    def _fifth_amendment_section(self) -> Section:
        lines: list[str] = []
        issues = self._get_issues_by_type("fifth")

        interrogation = self.matter.get("interrogation", {})
        if interrogation.get("was_interrogated"):
            miranda_given = interrogation.get("miranda_given", False)
            miranda_waived = interrogation.get("miranda_waived", False)
            statements = interrogation.get("statements_made", [])

            lines.extend([
                "A. Interrogation Analysis",
                "",
                f"Miranda warnings given: {'Yes' if miranda_given else 'NO - POTENTIAL ISSUE'}",
                f"Miranda waiver obtained: {'Yes' if miranda_waived else 'No'}",
                f"Statements obtained: {'Yes' if statements else 'No'}",
                "",
            ])

            if not miranda_given and statements:
                lines.extend([
                    "*** CRITICAL ISSUE ***",
                    "Statements obtained without Miranda warnings are presumptively inadmissible.",
                    "Motion to suppress statements recommended.",
                    "",
                ])

            if statements:
                lines.append("Statements made:")
                for stmt in statements:
                    lines.append(f'  - "{stmt}"')
                lines.append("")

            lines.extend([
                "Issues to investigate:",
                "  - Was defendant in custody for Miranda purposes?",
                "  - Was the waiver knowing and voluntary?",
                "  - Were statements coerced or involuntary?",
                f"  - Duration of interrogation: {interrogation.get('duration', 'Unknown')}",
                "",
            ])

        # Add identified issues
        if issues:
            lines.append("B. Identified Fifth Amendment Issues")
            lines.append("")
            for issue in issues:
                lines.append(f"  ISSUE: {issue.get('description', 'Unknown')}")
                evidence = issue.get("evidence", [])
                if evidence:
                    lines.append("  Evidence:")
                    for e in evidence:
                        lines.append(f"    - {e}")
                lines.append("")

        if not lines:
            lines = ["No specific Fifth Amendment issues identified at this time."]

        return Section(title="II. Fifth Amendment (Self-Incrimination)", body="\n".join(lines))

    def _sixth_amendment_section(self) -> Section:
        lines: list[str] = []
        issues = self._get_issues_by_type("sixth")

        identification = self.matter.get("identification", {})
        if identification.get("identification_procedure") and identification.get("identification_procedure") != "none":
            procedure = identification.get("identification_procedure", "").replace("_", " ").title()
            counsel_present = identification.get("was_counsel_present", False)
            confidence = identification.get("witness_confidence", "unknown")

            lines.extend([
                "A. Identification Procedure Analysis",
                "",
                f"Procedure used: {procedure}",
                f"Counsel present: {'Yes' if counsel_present else 'No'}",
                f"Witness confidence level: {confidence}",
                "",
                "Issues to investigate:",
                "  - Was the procedure suggestive?",
                "  - Was there independent reliability?",
                "  - Should counsel have been present (post-indictment)?",
                "",
            ])

        # Add identified issues
        if issues:
            lines.append("B. Identified Sixth Amendment Issues")
            lines.append("")
            for issue in issues:
                lines.append(f"  ISSUE: {issue.get('description', 'Unknown')}")
                evidence = issue.get("evidence", [])
                if evidence:
                    lines.append("  Evidence:")
                    for e in evidence:
                        lines.append(f"    - {e}")
                lines.append("")

        if not lines:
            lines = ["No specific Sixth Amendment issues identified at this time."]

        return Section(title="III. Sixth Amendment (Right to Counsel)", body="\n".join(lines))

    def _other_issues_section(self) -> Section:
        issues = self._get_issues_by_type("other")
        if not issues:
            return Section(title="", body="")

        lines = []
        for issue in issues:
            lines.append(f"ISSUE: {issue.get('description', 'Unknown')}")
            evidence = issue.get("evidence", [])
            if evidence:
                lines.append("Evidence:")
                for e in evidence:
                    lines.append(f"  - {e}")
            lines.append("")

        return Section(title="IV. Other Constitutional/Procedural Issues", body="\n".join(lines))

    def _recommendations_section(self) -> Section:
        all_issues = self.matter.get("constitutional_issues", [])
        lines = ["Based on the above analysis, the following actions are recommended:", ""]

        if any(i.get("issue_type") == "fourth_amendment" for i in all_issues if isinstance(i, dict)):
            lines.append("[ ] File Motion to Suppress Evidence (Fourth Amendment)")

        if any(i.get("issue_type") == "fifth_amendment" for i in all_issues if isinstance(i, dict)):
            lines.append("[ ] File Motion to Suppress Statements (Fifth Amendment)")

        if any(i.get("issue_type") == "sixth_amendment" for i in all_issues if isinstance(i, dict)):
            lines.append("[ ] File Motion to Suppress Identification (Sixth Amendment)")

        lines.extend([
            "[ ] Request all discovery related to constitutional issues",
            "[ ] Interview client regarding specific facts",
            "[ ] Subpoena body cam/dash cam footage",
            "[ ] Research jurisdiction-specific case law",
        ])

        return Section(title="V. Recommendations", body="\n".join(lines))

    def _get_issues_by_type(self, issue_type: str) -> list[dict[str, Any]]:
        """Filter constitutional issues by type."""
        all_issues = self.matter.get("constitutional_issues", [])
        return [
            i for i in all_issues
            if isinstance(i, dict) and issue_type in i.get("issue_type", "").lower()
        ]
