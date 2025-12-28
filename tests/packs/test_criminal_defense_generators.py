"""Tests for criminal defense document generators."""

from __future__ import annotations

import pytest

from packs.criminal_defense.generators import (
    BaseGenerator,
    BradyChecklistGenerator,
    ConstitutionalAnalysisGenerator,
    DiscoveryDemandGenerator,
    MotionRecommendationsGenerator,
    PreservationLetterGenerator,
    Section,
    SuppressionMotionGenerator,
    TimelineGenerator,
    WitnessInterviewGenerator,
)


@pytest.fixture
def sample_matter() -> dict:
    """Sample criminal defense matter for testing."""
    return {
        "matter_name": "State v. John Doe",
        "matter_id": "2024-CR-12345",
        "metadata": {
            "jurisdiction": "California",
            "case_number": "2024-CR-12345",
            "court": "Superior Court of California",
            "case_type": "felony",
        },
        "client": {
            "name": "John Doe",
            "prior_record": "none",
        },
        "charges": [
            {
                "statute": "PC 459",
                "description": "Burglary",
                "severity": "felony",
            },
            {
                "statute": "PC 496",
                "description": "Receiving Stolen Property",
                "severity": "felony",
            },
        ],
        "arrest": {
            "date": "2024-01-15",
            "location": "123 Main St, Los Angeles, CA",
            "arresting_agency": "LAPD",
            "officers": ["Officer Smith #1234", "Officer Jones #5678"],
            "circumstances": "Defendant observed near burglarized premises",
        },
        "search_and_seizure": {
            "was_search_conducted": True,
            "search_type": "consent",
            "items_seized": ["Electronics", "Jewelry"],
        },
        "interrogation": {
            "was_interrogated": True,
            "miranda_given": False,
            "miranda_waived": False,
            "duration": "3 hours",
            "statements_made": ["I was just walking by", "I don't know anything"],
        },
        "identification": {
            "identification_procedure": "photo_lineup",
            "was_counsel_present": False,
            "witness_confidence": "moderate",
        },
        "constitutional_issues": [
            {
                "issue_type": "fourth_amendment",
                "description": "Consent obtained through coercion - officers threatened to impound vehicle",
                "evidence": ["Body cam footage", "Witness statement"],
            },
            {
                "issue_type": "fifth_amendment",
                "description": "Statements obtained without Miranda warnings",
                "evidence": ["Interrogation recording", "Booking records"],
            },
        ],
        "discovery_received": [
            {
                "document_type": "Police Report",
                "date_received": "2024-01-20",
                "summary": "Initial incident report",
            },
        ],
        "discovery_outstanding": [
            "Body camera footage",
            "Dispatch recordings",
            "Lab results",
        ],
    }


@pytest.fixture
def minimal_matter() -> dict:
    """Minimal matter with only required fields."""
    return {
        "matter_name": "State v. Jane Smith",
        "metadata": {"jurisdiction": "Texas"},
        "client": {"name": "Jane Smith"},
        "charges": [{"description": "Misdemeanor Theft"}],
        "arrest": {"date": "2024-02-01"},
    }


class TestSection:
    """Tests for Section dataclass."""

    def test_render_with_title(self) -> None:
        section = Section(title="Test Title", body="Test body content")
        result = section.render()
        assert "TEST TITLE" in result
        assert "=" in result  # Separator
        assert "Test body content" in result

    def test_render_without_title(self) -> None:
        section = Section(title="", body="Just body content")
        result = section.render()
        assert result.strip() == "Just body content"

    def test_render_strips_whitespace(self) -> None:
        section = Section(title="Title", body="  Content with spaces  ")
        result = section.render()
        assert "Content with spaces" in result


class TestBaseGenerator:
    """Tests for BaseGenerator base class."""

    def test_properties_from_matter(self, sample_matter: dict) -> None:
        # Create a concrete generator to test base properties
        gen = SuppressionMotionGenerator(sample_matter)

        assert gen.matter_name == "State v. John Doe"
        assert gen.jurisdiction == "California"
        assert gen.case_number == "2024-CR-12345"
        assert gen.client["name"] == "John Doe"
        assert len(gen.charges) == 2
        assert gen.arrest["date"] == "2024-01-15"

    def test_render_combines_sections(self, sample_matter: dict) -> None:
        gen = SuppressionMotionGenerator(sample_matter)
        result = gen.render()

        # Should contain content from multiple sections
        assert "MOTION TO SUPPRESS" in result
        assert "State v. John Doe" in result
        assert "Fourth Amendment" in result or "FOURTH AMENDMENT" in result


class TestSuppressionMotionGenerator:
    """Tests for SuppressionMotionGenerator."""

    def test_generates_complete_motion(self, sample_matter: dict) -> None:
        gen = SuppressionMotionGenerator(sample_matter)
        result = gen.render()

        assert "MOTION TO SUPPRESS EVIDENCE" in result
        assert "John Doe" in result
        assert "CALIFORNIA" in result.upper()

    def test_includes_fourth_amendment_issues(self, sample_matter: dict) -> None:
        gen = SuppressionMotionGenerator(sample_matter)
        result = gen.render()

        assert "FOURTH AMENDMENT" in result
        assert "Consent obtained through coercion" in result

    def test_includes_fifth_amendment_issues(self, sample_matter: dict) -> None:
        gen = SuppressionMotionGenerator(sample_matter)
        result = gen.render()

        assert "FIFTH AMENDMENT" in result
        assert "Statements obtained without Miranda warnings" in result

    def test_includes_factual_background(self, sample_matter: dict) -> None:
        gen = SuppressionMotionGenerator(sample_matter)
        result = gen.render()

        assert "2024-01-15" in result
        assert "LAPD" in result

    def test_handles_minimal_matter(self, minimal_matter: dict) -> None:
        gen = SuppressionMotionGenerator(minimal_matter)
        result = gen.render()

        assert "State v. Jane Smith" in result
        assert "MOTION TO SUPPRESS" in result


class TestDiscoveryDemandGenerator:
    """Tests for DiscoveryDemandGenerator."""

    def test_generates_discovery_letter(self, sample_matter: dict) -> None:
        gen = DiscoveryDemandGenerator(sample_matter)
        result = gen.render()

        assert "[ATTORNEY LETTERHEAD]" in result
        assert "Discovery Demand" in result or "DISCOVERY" in result

    def test_includes_mandatory_disclosure_items(self, sample_matter: dict) -> None:
        gen = DiscoveryDemandGenerator(sample_matter)
        result = gen.render()

        assert "police reports" in result.lower()
        assert "witness statements" in result.lower()

    def test_includes_brady_giglio_section(self, sample_matter: dict) -> None:
        gen = DiscoveryDemandGenerator(sample_matter)
        result = gen.render()

        assert "Brady" in result or "exculpatory" in result.lower()

    def test_includes_outstanding_discovery(self, sample_matter: dict) -> None:
        gen = DiscoveryDemandGenerator(sample_matter)
        result = gen.render()

        assert "Body camera footage" in result

    def test_handles_dui_charges(self) -> None:
        dui_matter = {
            "matter_name": "State v. Driver",
            "metadata": {"jurisdiction": "Florida"},
            "client": {"name": "Driver"},
            "charges": [{"description": "DUI - First Offense"}],
            "arrest": {"date": "2024-03-01"},
        }
        gen = DiscoveryDemandGenerator(dui_matter)
        result = gen.render()

        # Should include DUI-specific discovery items
        assert "breathalyzer" in result.lower() or "calibration" in result.lower()


class TestPreservationLetterGenerator:
    """Tests for PreservationLetterGenerator."""

    def test_generates_preservation_letter(self, sample_matter: dict) -> None:
        gen = PreservationLetterGenerator(sample_matter)
        result = gen.render()

        assert "EVIDENCE PRESERVATION" in result
        assert "LAPD" in result

    def test_includes_standard_preservation_items(self, sample_matter: dict) -> None:
        gen = PreservationLetterGenerator(sample_matter)
        result = gen.render()

        assert "video" in result.lower() or "recording" in result.lower()
        assert "photograph" in result.lower() or "image" in result.lower()

    def test_includes_search_specific_items_when_search_conducted(
        self, sample_matter: dict
    ) -> None:
        gen = PreservationLetterGenerator(sample_matter)
        result = gen.render()

        # Should have search-related preservation items
        assert "warrant" in result.lower() or "search" in result.lower()

    def test_includes_interrogation_items_when_interrogated(
        self, sample_matter: dict
    ) -> None:
        gen = PreservationLetterGenerator(sample_matter)
        result = gen.render()

        # Should have interrogation-related items
        assert "interrogation" in result.lower() or "statement" in result.lower()


class TestConstitutionalAnalysisGenerator:
    """Tests for ConstitutionalAnalysisGenerator."""

    def test_generates_analysis_memo(self, sample_matter: dict) -> None:
        gen = ConstitutionalAnalysisGenerator(sample_matter)
        result = gen.render()

        assert "Constitutional" in result or "CONSTITUTIONAL" in result
        assert "State v. John Doe" in result

    def test_includes_all_amendment_sections(self, sample_matter: dict) -> None:
        gen = ConstitutionalAnalysisGenerator(sample_matter)
        result = gen.render()

        assert "Fourth Amendment" in result or "FOURTH AMENDMENT" in result
        assert "Fifth Amendment" in result or "FIFTH AMENDMENT" in result
        assert "Sixth Amendment" in result or "SIXTH AMENDMENT" in result

    def test_analyzes_search_issues(self, sample_matter: dict) -> None:
        gen = ConstitutionalAnalysisGenerator(sample_matter)
        result = gen.render()

        assert "consent" in result.lower()

    def test_flags_miranda_violations(self, sample_matter: dict) -> None:
        gen = ConstitutionalAnalysisGenerator(sample_matter)
        result = gen.render()

        # Should flag that Miranda was not given
        assert "miranda" in result.lower()
        assert "NO" in result or "not" in result.lower() or "without" in result.lower()

    def test_includes_recommendations(self, sample_matter: dict) -> None:
        gen = ConstitutionalAnalysisGenerator(sample_matter)
        result = gen.render()

        assert "Motion to Suppress" in result or "suppress" in result.lower()


class TestBradyChecklistGenerator:
    """Tests for BradyChecklistGenerator."""

    def test_generates_brady_checklist(self, sample_matter: dict) -> None:
        gen = BradyChecklistGenerator(sample_matter)
        result = gen.render()

        assert "Brady" in result
        assert "Giglio" in result

    def test_includes_exculpatory_section(self, sample_matter: dict) -> None:
        gen = BradyChecklistGenerator(sample_matter)
        result = gen.render()

        assert "exculpatory" in result.lower() or "Exculpatory" in result

    def test_includes_impeachment_section(self, sample_matter: dict) -> None:
        gen = BradyChecklistGenerator(sample_matter)
        result = gen.render()

        assert "impeachment" in result.lower() or "credibility" in result.lower()

    def test_includes_case_specific_items(self, sample_matter: dict) -> None:
        gen = BradyChecklistGenerator(sample_matter)
        result = gen.render()

        # Should include search-specific items since search was conducted
        assert "search" in result.lower()


class TestWitnessInterviewGenerator:
    """Tests for WitnessInterviewGenerator."""

    def test_generates_interview_checklist(self, sample_matter: dict) -> None:
        gen = WitnessInterviewGenerator(sample_matter)
        result = gen.render()

        assert "Interview" in result or "INTERVIEW" in result
        assert "State v. John Doe" in result

    def test_includes_client_interview_section(self, sample_matter: dict) -> None:
        gen = WitnessInterviewGenerator(sample_matter)
        result = gen.render()

        assert "John Doe" in result
        assert "timeline" in result.lower() or "events" in result.lower()

    def test_includes_officer_interview_section(self, sample_matter: dict) -> None:
        gen = WitnessInterviewGenerator(sample_matter)
        result = gen.render()

        # Should have officer-related content
        assert "Officer" in result or "LAPD" in result or "officer" in result.lower()
        # Should have law enforcement witness section
        assert "Law Enforcement" in result or "officers" in result.lower()

    def test_includes_expert_section_for_relevant_charges(
        self, sample_matter: dict
    ) -> None:
        gen = WitnessInterviewGenerator(sample_matter)
        result = gen.render()

        # Should have expert witness section
        assert "Expert" in result or "expert" in result


class TestMotionRecommendationsGenerator:
    """Tests for MotionRecommendationsGenerator."""

    def test_generates_recommendations(self, sample_matter: dict) -> None:
        gen = MotionRecommendationsGenerator(sample_matter)
        result = gen.render()

        assert "Motion" in result or "MOTION" in result
        assert "Recommendations" in result or "RECOMMENDATIONS" in result

    def test_prioritizes_suppression_motions(self, sample_matter: dict) -> None:
        gen = MotionRecommendationsGenerator(sample_matter)
        result = gen.render()

        # Should recommend suppression due to constitutional issues
        assert "suppress" in result.lower()
        assert "HIGH PRIORITY" in result or "Priority" in result

    def test_includes_discovery_motion(self, sample_matter: dict) -> None:
        gen = MotionRecommendationsGenerator(sample_matter)
        result = gen.render()

        assert "discovery" in result.lower() or "Discovery" in result

    def test_includes_timeline_section(self, sample_matter: dict) -> None:
        gen = MotionRecommendationsGenerator(sample_matter)
        result = gen.render()

        assert "Timeline" in result or "TIMELINE" in result

    def test_includes_standard_motions_for_felony(self, sample_matter: dict) -> None:
        gen = MotionRecommendationsGenerator(sample_matter)
        result = gen.render()

        # Should include bail reduction for felony cases
        assert "bail" in result.lower() or "Bail" in result


class TestTimelineGenerator:
    """Tests for TimelineGenerator."""

    def test_generates_timeline(self, sample_matter: dict) -> None:
        gen = TimelineGenerator(sample_matter)
        result = gen.render()

        assert "Timeline" in result or "TIMELINE" in result
        assert "State v. John Doe" in result

    def test_includes_arrest_event(self, sample_matter: dict) -> None:
        gen = TimelineGenerator(sample_matter)
        result = gen.render()

        assert "2024-01-15" in result
        assert "Arrest" in result

    def test_includes_constitutional_flags(self, sample_matter: dict) -> None:
        gen = TimelineGenerator(sample_matter)
        result = gen.render()

        # Should flag Miranda issue since miranda_given is False
        assert "Miranda" in result or "Fifth Amendment" in result

    def test_includes_discovery_events(self, sample_matter: dict) -> None:
        gen = TimelineGenerator(sample_matter)
        result = gen.render()

        assert "Discovery" in result or "Police Report" in result

    def test_includes_deadlines_section(self, sample_matter: dict) -> None:
        gen = TimelineGenerator(sample_matter)
        result = gen.render()

        assert "Deadline" in result or "DEADLINE" in result

    def test_render_csv(self, sample_matter: dict) -> None:
        gen = TimelineGenerator(sample_matter)
        csv = gen.render_csv()

        # Should be CSV format
        assert "date,event,constitutional_flag,source,action" in csv
        assert "2024-01-15" in csv

    def test_csv_handles_commas_in_content(self, sample_matter: dict) -> None:
        gen = TimelineGenerator(sample_matter)
        csv = gen.render_csv()

        # CSV should use semicolons to replace commas in content
        lines = csv.split("\n")
        for line in lines[1:]:  # Skip header
            if line:
                # Each line should have exactly 4 commas (5 fields)
                assert line.count(",") == 4

    def test_handles_minimal_matter(self, minimal_matter: dict) -> None:
        gen = TimelineGenerator(minimal_matter)
        result = gen.render()

        assert "State v. Jane Smith" in result


class TestGeneratorIntegration:
    """Integration tests for all generators working together."""

    def test_all_generators_produce_output(self, sample_matter: dict) -> None:
        generators = [
            SuppressionMotionGenerator,
            DiscoveryDemandGenerator,
            PreservationLetterGenerator,
            ConstitutionalAnalysisGenerator,
            BradyChecklistGenerator,
            WitnessInterviewGenerator,
            MotionRecommendationsGenerator,
            TimelineGenerator,
        ]

        for gen_class in generators:
            gen = gen_class(sample_matter)
            result = gen.render()
            assert len(result) > 100, f"{gen_class.__name__} produced insufficient output"
            assert "State v. John Doe" in result or "John Doe" in result

    def test_all_generators_handle_minimal_matter(self, minimal_matter: dict) -> None:
        generators = [
            SuppressionMotionGenerator,
            DiscoveryDemandGenerator,
            PreservationLetterGenerator,
            ConstitutionalAnalysisGenerator,
            BradyChecklistGenerator,
            WitnessInterviewGenerator,
            MotionRecommendationsGenerator,
            TimelineGenerator,
        ]

        for gen_class in generators:
            gen = gen_class(minimal_matter)
            # Should not raise an exception
            result = gen.render()
            assert isinstance(result, str)
            assert len(result) > 0

    def test_generators_with_execution_result(self, sample_matter: dict) -> None:
        execution_result = {
            "artifacts": {
                "lda": {"facts": ["Fact 1", "Fact 2"]},
                "dea": {"legal_analysis": "Analysis content"},
            }
        }

        gen = SuppressionMotionGenerator(sample_matter, execution_result)
        result = gen.render()
        assert len(result) > 0
