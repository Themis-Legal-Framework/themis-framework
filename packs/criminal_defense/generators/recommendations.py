"""Pretrial motion recommendations generator."""

from __future__ import annotations

from collections.abc import Iterable

from packs.criminal_defense.generators.base import BaseGenerator, Section


class MotionRecommendationsGenerator(BaseGenerator):
    """Generates pretrial motion recommendations based on case analysis."""

    template_name = "Pretrial Motion Recommendations"

    def sections(self) -> Iterable[Section]:
        yield self._header_section()
        yield self._priority_motions_section()
        yield self._standard_motions_section()
        yield self._timeline_section()

    def _header_section(self) -> Section:
        lines = [
            f"Case: {self.matter_name}",
            f"Client: {self.client.get('name', 'Unknown')}",
            f"Charges: {self._format_charges()}",
            "",
            "This memorandum recommends pretrial motions based on case analysis.",
            "Motions are prioritized by likelihood of success and impact on case.",
        ]
        return Section(title="Pretrial Motion Recommendations", body="\n".join(lines))

    def _format_charges(self) -> str:
        if not self.charges:
            return "Unknown"
        descriptions = [c.get("description", "Unknown") for c in self.charges if isinstance(c, dict)]
        return "; ".join(descriptions[:2]) + ("..." if len(descriptions) > 2 else "")

    def _priority_motions_section(self) -> Section:
        lines: list[str] = []
        priority = 1

        # Check for suppression motion opportunities
        constitutional_issues = self.matter.get("constitutional_issues", [])
        fourth_issues = [i for i in constitutional_issues if isinstance(i, dict) and "fourth" in i.get("issue_type", "").lower()]
        fifth_issues = [i for i in constitutional_issues if isinstance(i, dict) and "fifth" in i.get("issue_type", "").lower()]
        sixth_issues = [i for i in constitutional_issues if isinstance(i, dict) and "sixth" in i.get("issue_type", "").lower()]

        if fourth_issues:
            lines.extend([
                f"{priority}. MOTION TO SUPPRESS EVIDENCE [HIGH PRIORITY]",
                "",
                "   Basis: Fourth Amendment - Unlawful search/seizure",
                "   Issues identified:",
            ])
            for issue in fourth_issues:
                lines.append(f"     - {issue.get('description', 'Unknown issue')}")
            lines.extend([
                "",
                "   Status: Draft motion generated",
                "   Action: Review facts, research case law, file within 30 days",
                "",
            ])
            priority += 1

        if fifth_issues:
            lines.extend([
                f"{priority}. MOTION TO SUPPRESS STATEMENTS [HIGH PRIORITY]",
                "",
                "   Basis: Fifth Amendment - Miranda/voluntariness",
                "   Issues identified:",
            ])
            for issue in fifth_issues:
                lines.append(f"     - {issue.get('description', 'Unknown issue')}")
            lines.extend([
                "",
                "   Status: Requires review of interrogation details",
                "   Action: Obtain interrogation recording, file motion",
                "",
            ])
            priority += 1

        if sixth_issues:
            lines.extend([
                f"{priority}. MOTION TO SUPPRESS IDENTIFICATION [HIGH PRIORITY]",
                "",
                "   Basis: Sixth Amendment - Right to counsel / Due process",
                "   Issues identified:",
            ])
            for issue in sixth_issues:
                lines.append(f"     - {issue.get('description', 'Unknown issue')}")
            lines.extend([
                "",
                "   Status: Requires review of identification procedures",
                "   Action: Obtain lineup materials, depose witnesses",
                "",
            ])
            priority += 1

        # Always recommend discovery motion
        outstanding = self.matter.get("discovery_outstanding", [])
        lines.extend([
            f"{priority}. MOTION TO COMPEL DISCOVERY [HIGH PRIORITY]",
            "",
            "   Basis: Discovery rules / Brady obligations",
        ])
        if outstanding:
            lines.append("   Outstanding items:")
            for item in outstanding[:5]:
                if isinstance(item, str):
                    lines.append(f"     - {item}")
            if len(outstanding) > 5:
                lines.append(f"     - ... and {len(outstanding) - 5} more items")
        lines.extend([
            "",
            "   Status: Discovery demand letter generated",
            "   Action: File motion if prosecution fails to respond within deadline",
            "",
        ])

        if not lines:
            lines = ["No high-priority motions identified at this time."]

        return Section(title="I. High Priority Motions", body="\n".join(lines))

    def _standard_motions_section(self) -> Section:
        lines = []
        motion_num = 1

        # Determine case type for relevant motions
        case_type = self.metadata.get("case_type", "").lower()
        is_felony = case_type == "felony"
        prior_record = self.client.get("prior_record", "none")

        lines.extend([
            f"{motion_num}. MOTION FOR BILL OF PARTICULARS [MEDIUM PRIORITY]",
            "",
            "   Purpose: Obtain specific details about charges",
            "   When: File if charges are vague or ambiguous",
            "",
        ])
        motion_num += 1

        # Bail reduction if felony
        if is_felony:
            lines.extend([
                f"{motion_num}. MOTION TO REDUCE BAIL [CASE DEPENDENT]",
                "",
                "   Purpose: Reduce excessive bail / obtain pretrial release",
                f"   Factors: Prior record ({prior_record}), community ties, employment",
                "",
            ])
            motion_num += 1

        lines.extend([
            f"{motion_num}. MOTION FOR SPEEDY TRIAL [CASE DEPENDENT]",
            "",
            "   Purpose: Enforce constitutional right to speedy trial",
            "   When: File if prosecution causing unreasonable delays",
            "",
        ])
        motion_num += 1

        lines.extend([
            f"{motion_num}. MOTION IN LIMINE [PRE-TRIAL]",
            "",
            "   Purpose: Exclude prejudicial evidence before trial",
            "   Topics to consider:",
            "     - Prior bad acts (Rule 404(b))",
            "     - Character evidence",
            "     - Hearsay statements",
            "     - Inflammatory photographs",
            "",
        ])
        motion_num += 1

        # Dismissal motion if strong case
        if self.matter.get("constitutional_issues"):
            lines.extend([
                f"{motion_num}. MOTION TO DISMISS [AFTER SUPPRESSION]",
                "",
                "   Purpose: Seek dismissal if suppression leaves insufficient evidence",
                "   When: File after successful suppression motion",
                "",
            ])

        return Section(title="II. Standard Pretrial Motions", body="\n".join(lines))

    def _timeline_section(self) -> Section:
        arrest_date = self.arrest.get("date", "Unknown")

        lines = [
            f"Arrest date: {arrest_date}",
            "",
            "RECOMMENDED TIMELINE:",
            "",
            "Week 1-2:",
            "  [ ] File evidence preservation letter",
            "  [ ] Send discovery demand",
            "  [ ] Interview client in detail",
            "",
            "Week 2-4:",
            "  [ ] Review discovery received",
            "  [ ] Identify suppression issues",
            "  [ ] Begin motion research",
            "",
            "Week 4-6:",
            "  [ ] File suppression motions (if applicable)",
            "  [ ] File motion to compel discovery (if needed)",
            "  [ ] Prepare for preliminary hearing (if felony)",
            "",
            "Pre-trial:",
            "  [ ] File motions in limine",
            "  [ ] Prepare trial brief",
            "  [ ] Finalize witness list",
            "",
            "DEADLINES TO TRACK:",
            "  [ ] Motion filing deadline: _____________",
            "  [ ] Discovery deadline: _____________",
            "  [ ] Preliminary hearing: _____________",
            "  [ ] Trial date: _____________",
        ]
        return Section(title="III. Motion Timeline", body="\n".join(lines))
