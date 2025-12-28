"""Evidence preservation letter generator."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from packs.criminal_defense.generators.base import BaseGenerator, Section


class PreservationLetterGenerator(BaseGenerator):
    """Generates evidence preservation/spoliation prevention letter."""

    template_name = "Evidence Preservation Letter"

    def sections(self) -> Iterable[Section]:
        yield self._letterhead_section()
        yield self._standard_preservation_section()
        yield self._case_specific_section()
        yield self._warning_section()
        yield self._closing_section()

    def _letterhead_section(self) -> Section:
        today = datetime.now(UTC).strftime("%B %d, %Y")
        agency = self.arrest.get("arresting_agency", "Police Department")
        lines = [
            "[ATTORNEY LETTERHEAD]",
            "",
            today,
            "",
            agency,
            "ATTENTION: Evidence Custodian / Records Division",
            "",
            f"Re: {self.matter_name}",
            f"    Case No. {self.case_number}",
            "    EVIDENCE PRESERVATION DEMAND",
            "",
            "Dear Sir or Madam:",
            "",
            f"This office represents {self.client.get('name', 'the defendant')} in the "
            "above-referenced criminal matter. This letter serves as formal notice and "
            "demand that your agency preserve all evidence related to this case.",
            "",
            "YOU ARE HEREBY DIRECTED TO PRESERVE THE FOLLOWING EVIDENCE:",
        ]
        return Section(title="", body="\n".join(lines))

    def _standard_preservation_section(self) -> Section:
        lines = [
            "1. All video and audio recordings:",
            "   - Dash camera footage",
            "   - Body-worn camera footage",
            "   - Surveillance video",
            "   - Interrogation recordings",
            "   - 911 calls and dispatch recordings",
            "",
            "2. All photographs and digital images",
            "",
            "3. All physical evidence seized or collected",
            "",
            "4. All laboratory tests, reports, and raw data",
            "",
            "5. All written reports, notes, and memoranda",
            "",
            "6. All electronic data:",
            "   - Emails and text messages",
            "   - GPS and location data",
            "   - Computer files and forensic images",
            "   - Cell phone records and extractions",
            "",
            "7. All radio communications and CAD/dispatch logs",
            "",
            "8. All calibration and maintenance records for testing equipment",
        ]
        return Section(title="I. Standard Preservation Items", body="\n".join(lines))

    def _case_specific_section(self) -> Section:
        lines: list[str] = []
        item_num = 9

        # Search-related preservation
        search = self.matter.get("search_and_seizure", {})
        if search.get("was_search_conducted"):
            lines.extend([
                f"{item_num}. All search warrant materials and applications",
                f"{item_num + 1}. All evidence of property damage during search",
                f"{item_num + 2}. All photographs of search location before/during/after search",
                "",
            ])
            item_num += 3

        # Interrogation-related preservation
        interrogation = self.matter.get("interrogation", {})
        if interrogation.get("was_interrogated"):
            lines.extend([
                f"{item_num}. All recordings of interrogation (video and audio)",
                f"{item_num + 1}. All written statements and Miranda waivers",
                f"{item_num + 2}. All notes taken during interrogation",
                "",
            ])
            item_num += 3

        # Identification-related preservation
        identification = self.matter.get("identification", {})
        if identification.get("identification_procedure") and identification.get("identification_procedure") != "none":
            lines.extend([
                f"{item_num}. All lineup/photo array materials",
                f"{item_num + 1}. All witness identification statements",
                f"{item_num + 2}. All recordings of identification procedures",
                "",
            ])
            item_num += 3

        if not lines:
            return Section(title="", body="")

        return Section(title="II. Case-Specific Items", body="\n".join(lines))

    def _warning_section(self) -> Section:
        lines = [
            "FAILURE TO PRESERVE THIS EVIDENCE MAY RESULT IN:",
            "",
            "- Sanctions by the court",
            "- Adverse inference jury instructions",
            "- Dismissal of charges",
            "- Civil liability for spoliation of evidence",
            "- Professional discipline for involved officers",
            "",
            "This preservation demand applies to all officers, agents, employees, and ",
            "contractors of your department who may have access to relevant evidence.",
        ]
        return Section(title="III. Warning", body="\n".join(lines))

    def _closing_section(self) -> Section:
        lines = [
            "Please confirm in writing within seven (7) days that all evidence is being ",
            "preserved and identify the custodian responsible for each category of evidence.",
            "",
            "Respectfully submitted,",
            "",
            "[DEFENSE ATTORNEY NAME]",
            "Attorney for Defendant",
            "",
            "cc: District Attorney's Office",
        ]
        return Section(title="", body="\n".join(lines))
