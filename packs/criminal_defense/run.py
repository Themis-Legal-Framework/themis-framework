"""Command-line entry point for the State Criminal Defense practice pack."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency guard
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - executed when PyYAML missing
    yaml = None  # type: ignore[assignment]

from orchestrator.service import OrchestratorService
from packs.criminal_defense.generators import (
    BradyChecklistGenerator,
    ConstitutionalAnalysisGenerator,
    DiscoveryDemandGenerator,
    MotionRecommendationsGenerator,
    PreservationLetterGenerator,
    SuppressionMotionGenerator,
    WitnessInterviewGenerator,
)
from packs.criminal_defense.schema import (
    format_validation_errors,
    validate_matter_schema,
)


def load_matter(path: Path) -> dict[str, Any]:
    """Load and normalise a matter payload from YAML or JSON files."""

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Matter file '{path}' does not exist")

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise ValueError(
                "PyYAML is required to load YAML matter files. Install the 'pyyaml' dependency."
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    elif suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError("Matter files must be YAML or JSON")

    if data is None:
        raise ValueError("Matter file is empty")
    if not isinstance(data, dict):
        raise ValueError("Matter file must contain an object at the top level")

    # Validate schema
    is_valid, validation_errors = validate_matter_schema(data)
    if validation_errors and any("REQUIRED" in e for e in validation_errors):
        error_message = format_validation_errors(validation_errors)
        raise ValueError(f"Matter file validation failed:\n{error_message}")

    # Print warnings but continue
    if validation_errors and not is_valid:
        print(format_validation_errors(validation_errors))
        print()

    matter_payload = data.get("matter") if isinstance(data.get("matter"), dict) else data
    return _normalise_matter(matter_payload, source=path)


def persist_outputs(
    matter: dict[str, Any],
    execution_result: dict[str, Any],
    *,
    output_root: Path = Path("outputs"),
) -> list[Path]:
    """Persist derived artifacts from the orchestrator execution."""

    metadata = matter.get("metadata", {}) if isinstance(matter.get("metadata"), dict) else {}
    slug_source = metadata.get("slug") or matter.get("matter_name") or metadata.get("case_number")
    slug = _slugify(str(slug_source or "matter"))

    matter_output_dir = output_root / slug
    matter_output_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []

    # 1. Case Timeline with Constitutional Issues
    timeline_path = matter_output_dir / "case_timeline.csv"
    timeline_content = _generate_timeline(matter, execution_result)
    timeline_path.write_text(timeline_content, encoding="utf-8")
    saved_paths.append(timeline_path)

    # 2. Constitutional Issues Analysis (always generate from matter)
    analysis_path = matter_output_dir / "constitutional_issues_analysis.txt"
    analysis_gen = ConstitutionalAnalysisGenerator(matter, execution_result)
    analysis_path.write_text(analysis_gen.render(), encoding="utf-8")
    saved_paths.append(analysis_path)

    # 3. Discovery Demand Letter
    discovery_path = matter_output_dir / "discovery_demand.txt"
    discovery_gen = DiscoveryDemandGenerator(matter, execution_result)
    discovery_path.write_text(discovery_gen.render(), encoding="utf-8")
    saved_paths.append(discovery_path)

    # 4. Brady/Giglio Checklist
    brady_path = matter_output_dir / "brady_giglio_checklist.txt"
    brady_gen = BradyChecklistGenerator(matter, execution_result)
    brady_path.write_text(brady_gen.render(), encoding="utf-8")
    saved_paths.append(brady_path)

    # 5. Suppression Motion (only if constitutional issues warrant it)
    if _should_generate_suppression_motion(matter, execution_result):
        motion_path = matter_output_dir / "motion_to_suppress.txt"
        motion_gen = SuppressionMotionGenerator(matter, execution_result)
        motion_path.write_text(motion_gen.render(), encoding="utf-8")
        saved_paths.append(motion_path)

    # 6. Evidence Preservation Letter
    preservation_path = matter_output_dir / "evidence_preservation_letter.txt"
    preservation_gen = PreservationLetterGenerator(matter, execution_result)
    preservation_path.write_text(preservation_gen.render(), encoding="utf-8")
    saved_paths.append(preservation_path)

    # 7. Witness Interview Checklist
    witness_path = matter_output_dir / "witness_interview_checklist.txt"
    witness_gen = WitnessInterviewGenerator(matter, execution_result)
    witness_path.write_text(witness_gen.render(), encoding="utf-8")
    saved_paths.append(witness_path)

    # 8. Motion Recommendations
    recommendations_path = matter_output_dir / "pretrial_motion_recommendations.txt"
    recommendations_gen = MotionRecommendationsGenerator(matter, execution_result)
    recommendations_path.write_text(recommendations_gen.render(), encoding="utf-8")
    saved_paths.append(recommendations_path)

    return saved_paths


def _normalise_matter(raw: dict[str, Any], *, source: Path) -> dict[str, Any]:
    """Normalize criminal defense matter data for orchestrator compatibility."""
    if not isinstance(raw, dict):
        raise ValueError("Matter payload must be an object")

    existing_metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}

    # Client information (required)
    client = raw.get("client")
    if not isinstance(client, dict):
        raise ValueError("Matter must include client information")

    # Charges (required)
    charges = raw.get("charges")
    if not isinstance(charges, list) or len(charges) == 0:
        raise ValueError("Matter must include at least one charge")

    # Arrest information (required)
    arrest = raw.get("arrest")
    if not isinstance(arrest, dict):
        raise ValueError("Matter must include arrest information")

    # Generate matter ID and name
    jurisdiction = existing_metadata.get("jurisdiction", "State")
    case_number = existing_metadata.get("case_number") or raw.get("case_number") or source.stem
    client_name = client.get("name", "Unknown Client")
    matter_id = str(case_number).strip() or source.stem
    matter_name = f"{jurisdiction} v. {client_name}"

    slug_value = existing_metadata.get("slug")
    slug = _slugify(str(slug_value)) if isinstance(slug_value, str) and slug_value.strip() else _slugify(matter_id)

    metadata: dict[str, Any] = dict(existing_metadata)
    metadata.update({
        "id": matter_id,
        "case_number": case_number,
        "title": matter_name,
        "slug": slug,
        "source_file": str(source),
    })

    # Build summary for orchestrator compatibility
    charge_descriptions = [c.get("description", "") for c in charges if isinstance(c, dict)]
    summary = f"Criminal defense matter: {matter_name}. Charges: {'; '.join(charge_descriptions)}."
    if raw.get("defense_theory"):
        summary += f" Defense theory: {raw['defense_theory']}"

    # Build parties list for orchestrator compatibility
    parties = [
        {"name": client_name, "role": "Defendant"},
        {"name": jurisdiction, "role": "Prosecution"},
    ]

    # Build documents list from discovery for orchestrator compatibility
    documents: list[dict[str, Any]] = []
    for doc in raw.get("discovery_received", []):
        if isinstance(doc, dict):
            documents.append({
                "title": doc.get("document_type", "Discovery Document"),
                "content": doc.get("summary", ""),
                "date": doc.get("date_received", ""),
            })
    # Add arrest report as a document
    if arrest:
        documents.append({
            "title": "Arrest Report",
            "content": arrest.get("circumstances", "Arrest details"),
            "date": arrest.get("date", ""),
        })
    # Ensure at least one document
    if not documents:
        documents.append({
            "title": "Case File",
            "content": "Criminal case file - discovery pending",
            "date": arrest.get("date", ""),
        })

    normalised: dict[str, Any] = {
        # Orchestrator-required fields
        "summary": summary,
        "parties": parties,
        "documents": documents,
        # Criminal defense specific fields
        "matter_id": matter_id,
        "matter_name": matter_name,
        "metadata": metadata,
        "client": client,
        "charges": charges,
        "arrest": arrest,
    }

    # Optional fields
    optional_fields = [
        "search_and_seizure", "interrogation", "identification",
        "discovery_received", "discovery_outstanding", "constitutional_issues",
        "defense_theory", "goals", "client_narrative"
    ]

    for field in optional_fields:
        if field in raw:
            normalised[field] = raw[field]

    return normalised


def _should_generate_suppression_motion(matter: dict[str, Any], result: dict[str, Any]) -> bool:
    """Determine if a suppression motion should be generated based on constitutional issues."""
    # Check for constitutional issues in the matter
    issues = matter.get("constitutional_issues", [])
    if not isinstance(issues, list) or not issues:
        return False

    # Generate motion if there are Fourth, Fifth, or Sixth Amendment issues
    constitutional_issue_types = {
        issue.get("issue_type") for issue in issues if isinstance(issue, dict)
    }
    return bool(constitutional_issue_types & {"fourth_amendment", "fifth_amendment", "sixth_amendment"})


def _generate_timeline(matter: dict[str, Any], result: dict[str, Any]) -> str:
    """Generate chronological case timeline CSV."""
    lines = ["date,event,constitutional_flag\n"]

    # Add arrest date
    arrest = matter.get("arrest", {})
    if arrest.get("date"):
        lines.append(f"{arrest['date']},Arrest: {arrest.get('circumstances', 'Arrested')},\n")

    # Add discovery dates
    for doc in matter.get("discovery_received", []):
        if isinstance(doc, dict) and doc.get("date_received"):
            lines.append(f"{doc['date_received']},Discovery received: {doc.get('document_type', 'Document')},\n")

    # Add interrogation if present
    interrogation = matter.get("interrogation", {})
    if interrogation.get("was_interrogated"):
        flag = "⚠ Miranda issue" if not interrogation.get("miranda_given") else ""
        lines.append(f"{arrest.get('date', '')},Interrogation conducted,{flag}\n")

    return "".join(lines)


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:100]


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the State Criminal Defense practice pack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with existing matter file
  python -m packs.criminal_defense.run --matter path/to/matter.json

  # Validate matter file without executing
  python -m packs.criminal_defense.run --matter path/to/matter.json --validate-only

  # List available fixtures
  python -m packs.criminal_defense.run --list-fixtures
        """
    )
    parser.add_argument("--matter", type=Path, help="Path to the matter YAML or JSON file")
    parser.add_argument("--validate-only", action="store_true", help="Only validate the matter file without executing")
    parser.add_argument("--list-fixtures", action="store_true", help="List available fixture files")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Output directory for artifacts (default: outputs/)")

    args = parser.parse_args()

    # List fixtures
    if args.list_fixtures:
        fixtures_dir = Path(__file__).parent / "fixtures"
        if fixtures_dir.exists():
            print("Available fixture files:")
            for fixture in sorted(fixtures_dir.glob("*.json")):
                print(f"  - {fixture.name}")
        else:
            print("No fixtures directory found.")
        return

    # Require --matter for other operations
    if not args.matter:
        parser.error("--matter is required (or use --list-fixtures)")

    if not args.matter.exists():
        parser.error(f"Matter file '{args.matter}' was not found")

    # Validate only
    if args.validate_only:
        try:
            matter = load_matter(args.matter)
            print(f"✓ Matter file '{args.matter}' is valid!")
            print(f"  Jurisdiction: {matter.get('metadata', {}).get('jurisdiction', 'Not specified')}")
            print(f"  Client: {matter.get('client', {}).get('name', 'Unknown')}")
            print(f"  Charges: {len(matter.get('charges', []))}")
        except (FileNotFoundError, ValueError) as exc:
            print(f"✗ Validation failed: {exc}")
            return
        return

    # Execute normally
    service = OrchestratorService()
    try:
        matter = load_matter(args.matter)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    print(f"Executing workflow for: {matter.get('matter_name', 'Untitled Matter')}")
    print()

    result = await service.execute(matter)
    saved_paths = persist_outputs(matter, result, output_root=args.output_dir)

    print("Execution complete. Artifacts saved to:")
    for path in saved_paths:
        print(f" - {path}")
    if not saved_paths:
        print(" - No artifacts generated")


if __name__ == "__main__":
    asyncio.run(main())
