"""Run the Jamison v. Sunrise spoliation case through full orchestration."""

import asyncio
import json
from pathlib import Path

from orchestrator.service import OrchestratorService
from orchestrator.storage.sqlite_repository import SQLiteOrchestratorStateRepository


async def run_spoliation_case():
    """Execute the Jamison v. Sunrise spoliation case."""

    # Load the fixture
    fixture_path = Path("/tmp/themis-framework/packs/personal_injury/fixtures/spoliation_ladder_columbia.json")
    matter_data = json.loads(fixture_path.read_text())
    matter = matter_data.get("matter", matter_data)

    # Create service with SQLite repository
    database_url = "sqlite:////tmp/spoliation_case.db"
    repository = SQLiteOrchestratorStateRepository(database_url=database_url)
    service = OrchestratorService(repository=repository)

    print("\n" + "=" * 60)
    print("JAMISON v. SUNRISE LADDER CO., INC.")
    print("Spoliation of Evidence Analysis")
    print("=" * 60 + "\n")

    # Execute full workflow
    print("Running through all 4 agents and 6 phases...\n")
    execution = await service.execute(matter)

    # Show execution status
    print(f"Execution Status: {execution['status']}\n")

    # Show phases
    print("Phases Completed:")
    for step in execution.get("steps", []):
        phase = step.get("phase")
        status = step.get("status")
        print(f"  {phase:25s} [{status}]")

    # Extract and display artifacts
    artifacts = execution.get("artifacts", {})
    print(f"\nArtifacts produced by agents: {list(artifacts.keys())}")

    # LDA output - Facts analysis
    lda_output = artifacts.get("lda", {})
    if "facts" in lda_output:
        facts = lda_output["facts"]
        print("\n--- LDA (Legal Document Analysis) ---")
        print(f"Fact Pattern Summary items: {len(facts.get('fact_pattern_summary', []))}")
        print(f"Timeline entries: {len(facts.get('timeline', []))}")

    # DEA output - Legal authorities
    dea_output = artifacts.get("dea", {})
    if "authorities" in dea_output:
        authorities = dea_output["authorities"]
        print("\n--- DEA (Document Examination Agent) ---")
        print(f"Controlling authorities: {len(authorities.get('controlling_authorities', []))}")
        for auth in authorities.get("controlling_authorities", []):
            if isinstance(auth, dict):
                print(f"  - {auth.get('cite', auth.get('citation', 'N/A'))}")

    # LSA output - Strategy
    lsa_output = artifacts.get("lsa", {})
    if "strategy" in lsa_output:
        strategy = lsa_output["strategy"]
        print("\n--- LSA (Legal Strategy Agent) ---")
        if isinstance(strategy, dict):
            print(f"Strategy summary length: {len(str(strategy))} chars")
    if "draft" in lsa_output:
        draft = lsa_output["draft"]
        print(f"Draft summary: {len(draft.get('client_safe_summary', ''))} chars")

    # DDA output - Final document
    dda_output = artifacts.get("dda", {})
    if "document" in dda_output:
        document = dda_output["document"]
        full_text = document.get("full_text", "")
        print("\n--- DDA (Document Drafting Agent) ---")
        print(f"Document length: {len(full_text)} characters")

        # Save the document
        output_dir = Path("/tmp/spoliation_output")
        output_dir.mkdir(exist_ok=True)

        doc_path = output_dir / "client_letter.txt"
        doc_path.write_text(full_text)
        print(f"\nDocument saved to: {doc_path}")

        # Also save full execution results
        results_path = output_dir / "execution_results.json"
        results_path.write_text(json.dumps(execution, indent=2, default=str))
        print(f"Full results saved to: {results_path}")

        # Print the client letter
        print("\n" + "=" * 60)
        print("CLIENT LETTER OUTPUT")
        print("=" * 60)
        print(full_text)

    return execution


if __name__ == "__main__":
    asyncio.run(run_spoliation_case())
