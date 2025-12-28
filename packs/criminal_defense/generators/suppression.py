"""Motion to suppress evidence generator."""

from __future__ import annotations

from collections.abc import Iterable

from packs.criminal_defense.generators.base import BaseGenerator, Section


class SuppressionMotionGenerator(BaseGenerator):
    """Generates motion to suppress evidence based on constitutional violations."""

    template_name = "Motion to Suppress Evidence"

    def sections(self) -> Iterable[Section]:
        yield self._caption_section()
        yield self._introduction_section()
        yield self._factual_background_section()
        yield self._legal_argument_section()
        yield self._conclusion_section()

    def _caption_section(self) -> Section:
        court = self.metadata.get("court", "SUPERIOR COURT")
        lines = [
            court,
            self.jurisdiction.upper(),
            "",
            self.matter_name,
            f"Case No. {self.case_number}",
            "",
            "DEFENDANT'S MOTION TO SUPPRESS EVIDENCE",
        ]
        return Section(title="", body="\n".join(lines))

    def _introduction_section(self) -> Section:
        client_name = self.client.get("name", "Defendant")
        body = (
            f"COMES NOW the Defendant, {client_name}, by and through undersigned counsel, "
            "and respectfully moves this Court to suppress all evidence obtained as a result "
            "of violations of the Fourth, Fifth, and/or Sixth Amendments to the United States "
            "Constitution and corresponding provisions of the State Constitution."
        )
        return Section(title="Introduction", body=body)

    def _factual_background_section(self) -> Section:
        arrest_date = self.arrest.get("date", "[DATE]")
        arrest_location = self.arrest.get("location", "[LOCATION]")
        agency = self.arrest.get("arresting_agency", "law enforcement")
        circumstances = self.arrest.get("circumstances", "")
        client_name = self.client.get("name", "Defendant")

        lines = [
            f"On or about {arrest_date}, {client_name} was stopped by officers of the "
            f"{agency} near {arrest_location}.",
            "",
        ]

        if circumstances:
            lines.append(f"The stated basis for the stop was: {circumstances}")
            lines.append("")

        # Add search details if present
        search = self.matter.get("search_and_seizure", {})
        if search.get("was_search_conducted"):
            search_type = search.get("search_type", "unknown")
            items = search.get("items_seized", [])
            lines.append(f"A {search_type} search was conducted.")
            if items:
                lines.append(f"Items seized: {', '.join(items)}")
            lines.append("")

        # Add interrogation details if present
        interrogation = self.matter.get("interrogation", {})
        if interrogation.get("was_interrogated"):
            miranda = "was" if interrogation.get("miranda_given") else "was NOT"
            lines.append(f"Defendant was interrogated. Miranda warning {miranda} given.")
            if interrogation.get("statements_made"):
                lines.append("Statements were obtained during this interrogation.")
            lines.append("")

        return Section(title="Factual Background", body="\n".join(lines))

    def _legal_argument_section(self) -> Section:
        issues = self.matter.get("constitutional_issues", [])
        lines: list[str] = []
        arg_num = 1

        for issue in issues:
            if not isinstance(issue, dict):
                continue

            issue_type = issue.get("issue_type", "")
            description = issue.get("description", "")
            evidence = issue.get("evidence", [])

            if "fourth" in issue_type.lower():
                lines.extend([
                    f"{_roman(arg_num)}. THE EVIDENCE MUST BE SUPPRESSED DUE TO FOURTH AMENDMENT VIOLATIONS",
                    "",
                    "The Fourth Amendment protects against unreasonable searches and seizures. "
                    "Evidence obtained in violation of this protection must be suppressed under "
                    "the exclusionary rule. Mapp v. Ohio, 367 U.S. 643 (1961).",
                    "",
                    description,
                    "",
                ])
                if evidence:
                    lines.append("Supporting evidence:")
                    for e in evidence:
                        lines.append(f"  - {e}")
                    lines.append("")
                arg_num += 1

            elif "fifth" in issue_type.lower():
                lines.extend([
                    f"{_roman(arg_num)}. DEFENDANT'S STATEMENTS MUST BE SUPPRESSED DUE TO FIFTH AMENDMENT VIOLATIONS",
                    "",
                    "The Fifth Amendment protects against compelled self-incrimination. "
                    "Statements obtained without proper Miranda warnings or after an invalid "
                    "waiver must be suppressed. Miranda v. Arizona, 384 U.S. 436 (1966).",
                    "",
                    description,
                    "",
                ])
                if evidence:
                    lines.append("Supporting evidence:")
                    for e in evidence:
                        lines.append(f"  - {e}")
                    lines.append("")
                arg_num += 1

            elif "sixth" in issue_type.lower():
                lines.extend([
                    f"{_roman(arg_num)}. EVIDENCE MUST BE SUPPRESSED DUE TO SIXTH AMENDMENT VIOLATIONS",
                    "",
                    "The Sixth Amendment guarantees the right to counsel. Evidence obtained "
                    "in violation of this right must be suppressed.",
                    "",
                    description,
                    "",
                ])
                if evidence:
                    lines.append("Supporting evidence:")
                    for e in evidence:
                        lines.append(f"  - {e}")
                    lines.append("")
                arg_num += 1

        if not lines:
            lines = [
                "I. CONSTITUTIONAL VIOLATIONS",
                "",
                "[Specific constitutional arguments to be developed based on case facts]",
                "",
            ]

        return Section(title="Legal Argument", body="\n".join(lines))

    def _conclusion_section(self) -> Section:
        body = (
            "For the foregoing reasons, Defendant respectfully requests that this Court "
            "grant this Motion to Suppress and exclude all evidence obtained in violation "
            "of Defendant's constitutional rights, together with all fruits of such evidence.\n\n"
            "Respectfully submitted,\n\n"
            "[DEFENSE ATTORNEY NAME]\n"
            "Attorney for Defendant"
        )
        return Section(title="Conclusion", body=body)


def _roman(num: int) -> str:
    """Convert integer to Roman numeral."""
    numerals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    result = ""
    for value, numeral in numerals:
        while num >= value:
            result += numeral
            num -= value
    return result
