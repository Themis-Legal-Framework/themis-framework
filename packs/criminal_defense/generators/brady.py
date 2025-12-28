"""Brady/Giglio exculpatory evidence checklist generator."""

from __future__ import annotations

from collections.abc import Iterable

from packs.criminal_defense.generators.base import BaseGenerator, Section


class BradyChecklistGenerator(BaseGenerator):
    """Generates Brady/Giglio exculpatory evidence checklist."""

    template_name = "Brady/Giglio Checklist"

    def sections(self) -> Iterable[Section]:
        yield self._header_section()
        yield self._exculpatory_section()
        yield self._impeachment_section()
        yield self._case_specific_section()
        yield self._tracking_section()

    def _header_section(self) -> Section:
        lines = [
            f"Case: {self.matter_name}",
            f"Client: {self.client.get('name', 'Unknown')}",
            "",
            "Under Brady v. Maryland (1963) and Giglio v. United States (1972), the prosecution",
            "must disclose all material evidence favorable to the defendant, including:",
            "  - Evidence of innocence (Brady)",
            "  - Evidence affecting witness credibility (Giglio)",
            "",
            "Use this checklist to track exculpatory evidence demands and disclosures.",
        ]
        return Section(title="Brady/Giglio Checklist", body="\n".join(lines))

    def _exculpatory_section(self) -> Section:
        lines = [
            "[ ] Evidence favorable to defendant on guilt",
            "    - Evidence defendant did not commit the crime",
            "    - Evidence of misidentification",
            "    - Evidence of alibi",
            "    - Evidence pointing to another suspect",
            "",
            "[ ] Evidence favorable on punishment",
            "    - Mitigating circumstances",
            "    - Evidence supporting lesser charge",
            "    - Evidence of rehabilitation",
            "",
            "[ ] Evidence contradicting prosecution theory",
            "    - Inconsistent physical evidence",
            "    - Conflicting witness accounts",
            "    - Exculpatory forensic evidence",
            "",
            "[ ] Evidence of other suspects",
            "    - Third-party culpability evidence",
            "    - Evidence of motive by others",
            "    - Evidence of opportunity by others",
        ]
        return Section(title="I. Exculpatory Evidence (Brady)", body="\n".join(lines))

    def _impeachment_section(self) -> Section:
        lines = [
            "[ ] Witness credibility evidence",
            "    - Prior inconsistent statements",
            "    - Bias, prejudice, or interest in outcome",
            "    - Motive to fabricate",
            "",
            "[ ] Criminal histories of prosecution witnesses",
            "    - Prior convictions (especially dishonesty crimes)",
            "    - Pending charges",
            "    - Arrests without conviction",
            "",
            "[ ] Benefits given to witnesses",
            "    - Plea agreements",
            "    - Immunity grants",
            "    - Payment or rewards",
            "    - Favorable treatment in other cases",
            "    - Immigration benefits",
            "",
            "[ ] Law enforcement misconduct",
            "    - Officer disciplinary records",
            "    - Prior false testimony findings",
            "    - Pending investigations",
            "    - Brady/Giglio lists (if jurisdiction maintains)",
        ]
        return Section(title="II. Impeachment Evidence (Giglio)", body="\n".join(lines))

    def _case_specific_section(self) -> Section:
        lines: list[str] = []

        # Add search-specific items
        search = self.matter.get("search_and_seizure", {})
        if search.get("was_search_conducted"):
            lines.extend([
                "SEARCH & SEIZURE SPECIFIC:",
                "[ ] Evidence search was unlawful",
                "[ ] Evidence warrant was based on false information",
                "[ ] Evidence consent was involuntary or coerced",
                "[ ] Evidence of items NOT found during search",
                "",
            ])

        # Add interrogation-specific items
        interrogation = self.matter.get("interrogation", {})
        if interrogation.get("was_interrogated"):
            lines.extend([
                "CONFESSION/INTERROGATION SPECIFIC:",
                "[ ] Evidence confession was coerced",
                "[ ] Evidence of Miranda violations",
                "[ ] Evidence of promises or threats",
                "[ ] Evidence of mental state affecting reliability",
                "[ ] Full recordings (not just excerpts)",
                "",
            ])

        # Add identification-specific items
        identification = self.matter.get("identification", {})
        if identification.get("identification_procedure") and identification.get("identification_procedure") != "none":
            lines.extend([
                "IDENTIFICATION SPECIFIC:",
                "[ ] Evidence of suggestive procedures",
                "[ ] Prior failures to identify defendant",
                "[ ] Initial descriptions inconsistent with defendant",
                "[ ] Witness uncertainty or hesitation",
                "",
            ])

        if not lines:
            return Section(title="", body="")

        return Section(title="III. Case-Specific Items", body="\n".join(lines))

    def _tracking_section(self) -> Section:
        lines = [
            "| Item Requested | Date Requested | Date Received | Notes |",
            "|----------------|----------------|---------------|-------|",
            "| Police reports | | | |",
            "| Witness statements | | | |",
            "| Officer disciplinary records | | | |",
            "| Lab reports | | | |",
            "| Video/audio recordings | | | |",
            "| | | | |",
            "| | | | |",
            "",
            "NOTES:",
            "- Document all Brady requests in writing",
            "- Preserve all correspondence with prosecution",
            "- File motion to compel if disclosure delayed",
            "- Note any oral disclosures and follow up in writing",
        ]
        return Section(title="IV. Disclosure Tracking", body="\n".join(lines))
