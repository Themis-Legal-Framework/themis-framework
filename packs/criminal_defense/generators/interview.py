"""Witness interview checklist generator."""

from __future__ import annotations

from collections.abc import Iterable

from packs.criminal_defense.generators.base import BaseGenerator, Section


class WitnessInterviewGenerator(BaseGenerator):
    """Generates witness interview checklists."""

    template_name = "Witness Interview Checklist"

    def sections(self) -> Iterable[Section]:
        yield self._header_section()
        yield self._client_interview_section()
        yield self._officer_interview_section()
        yield self._witness_interview_section()
        yield self._expert_section()

    def _header_section(self) -> Section:
        lines = [
            f"Case: {self.matter_name}",
            f"Client: {self.client.get('name', 'Unknown')}",
            "",
            "Track all witness interviews and key questions for each.",
        ]
        return Section(title="Witness Interview Checklist", body="\n".join(lines))

    def _client_interview_section(self) -> Section:
        client_name = self.client.get("name", "Client")
        prior_record = self.client.get("prior_record", "unknown")

        lines = [
            f"[ ] {client_name}",
            f"    Prior record: {prior_record}",
            "",
            "GENERAL QUESTIONS:",
            "    [ ] Complete timeline of events (hour by hour)",
            "    [ ] Whereabouts before, during, after incident",
            "    [ ] All witnesses who can corroborate story",
            "    [ ] Any alibi evidence",
            "",
            "ARREST QUESTIONS:",
            "    [ ] Exact words officers used",
            "    [ ] How client responded",
            "    [ ] Any physical force used",
            "    [ ] What Miranda warnings were given (exact words)",
            "    [ ] Whether client understood rights",
            "",
        ]

        # Add search-specific questions
        search = self.matter.get("search_and_seizure", {})
        if search.get("was_search_conducted"):
            lines.extend([
                "SEARCH QUESTIONS:",
                "    [ ] Was consent requested? How?",
                "    [ ] Did client consent? Why/why not?",
                "    [ ] What areas were searched?",
                "    [ ] What was the condition of property after search?",
                "",
            ])

        # Add interrogation-specific questions
        interrogation = self.matter.get("interrogation", {})
        if interrogation.get("was_interrogated"):
            lines.extend([
                "INTERROGATION QUESTIONS:",
                "    [ ] How long was interrogation?",
                "    [ ] Was client denied food, water, bathroom?",
                "    [ ] Were any promises or threats made?",
                "    [ ] Did client ask for lawyer?",
                "    [ ] Did client ask to stop?",
                "",
            ])

        lines.extend([
            "PERSONAL CIRCUMSTANCES:",
            "    [ ] Any medical conditions relevant to case",
            "    [ ] Any medications that could affect behavior",
            "    [ ] Employment and family situation",
            "    [ ] Immigration status (if relevant)",
        ])

        return Section(title="I. Client Interview", body="\n".join(lines))

    def _officer_interview_section(self) -> Section:
        officers = self.arrest.get("officers", [])
        agency = self.arrest.get("arresting_agency", "Unknown Agency")

        lines = [
            f"Agency: {agency}",
            "",
        ]

        if officers:
            lines.append("OFFICERS TO DEPOSE/CROSS-EXAMINE:")
            for officer in officers:
                lines.extend([
                    f"[ ] {officer}",
                    "    Questions:",
                    "    - Training and experience in this type of case",
                    "    - Exact basis for stop/arrest",
                    "    - Body cam/dash cam activation",
                    "    - Prior testimony in similar cases",
                    "    - Knowledge of defendant prior to incident",
                    "",
                ])
        else:
            lines.extend([
                "[ ] Arresting Officer (name TBD from discovery)",
                "    Questions:",
                "    - Basis for initial stop",
                "    - Observations leading to arrest",
                "    - Handling of evidence",
                "",
            ])

        lines.extend([
            "STANDARD OFFICER QUESTIONS:",
            "    [ ] Exact observations (not conclusions)",
            "    [ ] Time, lighting, distance for observations",
            "    [ ] Notes taken and when",
            "    [ ] Report preparation (when, from what)",
            "    [ ] Prior contact with defendant",
            "    [ ] Discipline or complaint history",
        ])

        return Section(title="II. Law Enforcement Witnesses", body="\n".join(lines))

    def _witness_interview_section(self) -> Section:
        lines = [
            "CIVILIAN WITNESSES (to be identified from discovery):",
            "",
            "[ ] Witness 1: _______________",
            "    Contact: _______________",
            "    Relation to case: _______________",
            "    Key points: _______________",
            "",
            "[ ] Witness 2: _______________",
            "    Contact: _______________",
            "    Relation to case: _______________",
            "    Key points: _______________",
            "",
            "[ ] Witness 3: _______________",
            "    Contact: _______________",
            "    Relation to case: _______________",
            "    Key points: _______________",
            "",
            "STANDARD CIVILIAN WITNESS QUESTIONS:",
            "    [ ] What exactly did you see/hear?",
            "    [ ] Where were you standing?",
            "    [ ] Lighting and weather conditions",
            "    [ ] How long did you observe?",
            "    [ ] Did you know anyone involved?",
            "    [ ] Have you spoken to police?",
            "    [ ] Have you spoken to anyone else about this?",
        ]
        return Section(title="III. Civilian Witnesses", body="\n".join(lines))

    def _expert_section(self) -> Section:
        lines: list[str] = []
        charge_text = " ".join(
            c.get("description", "").lower() for c in self.charges if isinstance(c, dict)
        )

        lines.append("POTENTIAL EXPERT WITNESSES:")
        lines.append("")

        if "dui" in charge_text or "dwi" in charge_text:
            lines.extend([
                "[ ] Toxicologist / Pharmacologist",
                "    - Blood/breath alcohol analysis",
                "    - Absorption rates and timing",
                "    - Retrograde extrapolation issues",
                "",
                "[ ] Breathalyzer Expert",
                "    - Device calibration issues",
                "    - Operator errors",
                "    - Environmental factors",
                "",
            ])

        if "drug" in charge_text or "possession" in charge_text:
            lines.extend([
                "[ ] Forensic Chemist",
                "    - Testing methodology",
                "    - Chain of custody",
                "    - False positive issues",
                "",
            ])

        if "assault" in charge_text or "battery" in charge_text:
            lines.extend([
                "[ ] Medical Expert",
                "    - Injury causation",
                "    - Injury severity",
                "    - Consistency with claims",
                "",
            ])

        lines.extend([
            "[ ] False Confession Expert (if statements at issue)",
            "    - Coercive interrogation techniques",
            "    - Vulnerability factors",
            "",
            "[ ] Eyewitness Identification Expert (if ID at issue)",
            "    - Memory reliability",
            "    - Suggestive procedures",
        ])

        return Section(title="IV. Expert Witnesses", body="\n".join(lines))
