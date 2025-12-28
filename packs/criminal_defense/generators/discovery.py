"""Discovery demand letter generator."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from packs.criminal_defense.generators.base import BaseGenerator, Section


class DiscoveryDemandGenerator(BaseGenerator):
    """Generates discovery demand letter for criminal cases."""

    template_name = "Discovery Demand Letter"

    def sections(self) -> Iterable[Section]:
        yield self._letterhead_section()
        yield self._mandatory_disclosure_section()
        yield self._brady_giglio_section()
        yield self._case_specific_section()
        yield self._closing_section()

    def _letterhead_section(self) -> Section:
        today = datetime.now(UTC).strftime("%B %d, %Y")
        client_name = self.client.get("name", "Unknown")
        lines = [
            "[ATTORNEY LETTERHEAD]",
            "",
            today,
            "",
            "District Attorney's Office",
            self.jurisdiction,
            "",
            f"Re: {self.matter_name}",
            f"    Case No. {self.case_number}",
            "",
            "Dear Prosecutor:",
            "",
            f"Pursuant to applicable discovery rules in {self.jurisdiction} and "
            f"Brady v. Maryland, defendant {client_name} requests immediate disclosure "
            "of the following discovery materials:",
        ]
        return Section(title="", body="\n".join(lines))

    def _mandatory_disclosure_section(self) -> Section:
        lines = [
            "1. All police reports and investigative materials",
            "2. All witness statements (recorded and written)",
            "3. All physical evidence seized or obtained",
            "4. All scientific reports and laboratory results",
            "5. All photographs and video/audio recordings",
            "6. All dispatch logs and radio communications",
            "7. All officer notes and memoranda",
            "8. Criminal histories of all witnesses",
        ]
        return Section(title="I. Mandatory Disclosure", body="\n".join(lines))

    def _brady_giglio_section(self) -> Section:
        lines = [
            "1. Any evidence favorable to the defendant on guilt or punishment",
            "2. Any impeachment evidence regarding prosecution witnesses",
            "3. Any evidence of other suspects or alternative perpetrators",
            "4. Any prior inconsistent statements by witnesses",
            "5. Any promises, deals, or benefits given to witnesses",
            "6. Any complaints or disciplinary records for officers involved",
            "7. Any evidence of investigative misconduct",
        ]
        return Section(title="II. Exculpatory Evidence (Brady/Giglio)", body="\n".join(lines))

    def _case_specific_section(self) -> Section:
        lines: list[str] = []
        charges = self.charges

        # Determine charge type for specific requests
        charge_text = " ".join(
            c.get("description", "").lower() for c in charges if isinstance(c, dict)
        )

        if "dui" in charge_text or "dwi" in charge_text or "influence" in charge_text:
            lines.extend([
                "1. Breathalyzer/blood test calibration records (past 12 months)",
                "2. Breathalyzer/blood test maintenance logs",
                "3. Officer training and certification records for DUI enforcement",
                "4. Dash cam and body cam footage of stop and arrest",
                "5. Field sobriety test training materials",
                "6. Title 17 (or equivalent) compliance documentation",
                "7. Chain of custody for all blood/breath samples",
            ])

        elif "drug" in charge_text or "controlled substance" in charge_text or "possession" in charge_text:
            lines.extend([
                "1. Laboratory analysis and chain of custody for substances",
                "2. Confidential informant identity and reliability records",
                "3. Search warrant and supporting affidavit (if applicable)",
                "4. All surveillance recordings and photographs",
                "5. Informant payment records and benefits provided",
                "6. Prior cases involving the confidential informant",
            ])

        elif "assault" in charge_text or "battery" in charge_text or "domestic" in charge_text:
            lines.extend([
                "1. All 911 calls and recordings",
                "2. Medical records of alleged victim",
                "3. Photographs of alleged injuries",
                "4. Prior domestic violence calls to this address",
                "5. History of complaints by alleged victim",
                "6. Any recantation or inconsistent statements by alleged victim",
            ])

        elif "theft" in charge_text or "burglary" in charge_text or "robbery" in charge_text:
            lines.extend([
                "1. Surveillance video from alleged crime scene",
                "2. Inventory of allegedly stolen items with values",
                "3. Evidence of ownership of allegedly stolen items",
                "4. Any identification procedure documentation",
                "5. Fingerprint and DNA evidence (or lack thereof)",
            ])

        else:
            lines.extend([
                "1. All evidence specific to the charged offense(s)",
                "2. All expert witness reports and qualifications",
                "3. All documentary evidence to be used at trial",
            ])

        # Add outstanding discovery from matter
        outstanding = self.matter.get("discovery_outstanding", [])
        if outstanding:
            lines.append("")
            lines.append("Additionally, we specifically request:")
            for item in outstanding:
                if isinstance(item, str):
                    lines.append(f"  - {item}")

        return Section(title="III. Case-Specific Discovery", body="\n".join(lines))

    def _closing_section(self) -> Section:
        lines = [
            "Please provide this discovery within the time required by law. Failure to ",
            "disclose exculpatory evidence may result in sanctions, dismissal, or reversal ",
            "of any conviction obtained.",
            "",
            "We reserve the right to supplement this request as additional information ",
            "becomes available.",
            "",
            "Respectfully submitted,",
            "",
            "[DEFENSE ATTORNEY NAME]",
            "Attorney for Defendant",
        ]
        return Section(title="", body="\n".join(lines))
