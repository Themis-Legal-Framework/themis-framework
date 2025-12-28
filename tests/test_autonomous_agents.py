#!/usr/bin/env python3
"""Test autonomous agent workflow end-to-end."""

import asyncio
from agents.lda import LDAAgent
from agents.dea import DEAAgent
from agents.lsa import LSAAgent
from agents.dda import DocumentDraftingAgent


async def test_autonomous_workflow():
    """Test all agents with autonomous tool selection."""

    # Sample matter for testing
    test_matter = {
        "summary": "Car accident personal injury case",
        "description": "Client Alex Benedict was rear-ended by defendant John Smith on Highway 101",
        "parties": [
            {"name": "Alex Benedict", "role": "plaintiff"},
            {"name": "John Smith", "role": "defendant"}
        ],
        "jurisdiction": "California",
        "document_type": "complaint",
        "documents": [
            {
                "title": "Police Report",
                "date": "2024-01-15",
                "content": "Rear-end collision on Highway 101. Defendant admitted fault. Plaintiff transported to hospital with neck and back injuries.",
            }
        ],
        "events": [
            {"date": "2024-01-15", "description": "Accident occurred on Highway 101"},
            {"date": "2024-01-15", "description": "Alex Benedict transported to Mercy Hospital"},
            {"date": "2024-01-16", "description": "Client diagnosed with whiplash and lumbar strain"},
        ],
        "goals": {
            "settlement": "Recover damages for medical expenses and pain & suffering",
            "remedy": "Monetary compensation"
        }
    }

    print("=" * 80)
    print("TESTING AUTONOMOUS AGENT WORKFLOW")
    print("=" * 80)

    # Test LDA Agent
    print("\n[1/4] Testing LDA Agent (autonomous tool selection)...")
    lda = LDAAgent()
    lda_result = await lda.run(test_matter)

    print(f"  ✓ LDA completed in {lda_result['provenance']['tool_rounds']} rounds")
    print(f"  ✓ Tools used: {', '.join(lda_result['provenance']['tools_used'])}")
    print(f"  ✓ Autonomous mode: {lda_result['provenance']['autonomous_mode']}")

    # Add LDA output to matter
    test_matter.update(lda_result)

    # Test DEA Agent
    print("\n[2/4] Testing DEA Agent (autonomous tool selection)...")
    dea = DEAAgent()
    dea_result = await dea.run(test_matter)

    print(f"  ✓ DEA completed in {dea_result['provenance']['tool_rounds']} rounds")
    print(f"  ✓ Tools used: {', '.join(dea_result['provenance']['tools_used'])}")
    print(f"  ✓ Autonomous mode: {dea_result['provenance']['autonomous_mode']}")

    # Add DEA output to matter
    test_matter.update(dea_result)

    # Test LSA Agent
    print("\n[3/4] Testing LSA Agent (autonomous tool selection)...")
    lsa = LSAAgent()
    lsa_result = await lsa.run(test_matter)

    print(f"  ✓ LSA completed in {lsa_result['provenance']['tool_rounds']} rounds")
    print(f"  ✓ Tools used: {', '.join(lsa_result['provenance']['tools_used'])}")
    print(f"  ✓ Autonomous mode: {lsa_result['provenance']['autonomous_mode']}")

    # Add LSA output to matter
    test_matter.update(lsa_result)

    # Test DDA Agent
    print("\n[4/4] Testing DDA Agent (autonomous tool selection)...")
    dda = DocumentDraftingAgent()
    dda_result = await dda.run(test_matter)

    print(f"  ✓ DDA completed in {dda_result['provenance']['tool_rounds']} rounds")
    print(f"  ✓ Tools used: {', '.join(dda_result['provenance']['tools_used'])}")
    print(f"  ✓ Autonomous mode: {dda_result['provenance']['autonomous_mode']}")

    # Verify document was generated
    document = dda_result.get("document", {})
    full_text = document.get("full_text", "")

    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 80)

    print(f"\nDocument Type: {dda_result['metadata']['document_type']}")
    print(f"Jurisdiction: {dda_result['metadata']['jurisdiction']}")
    print(f"Document Length: {len(full_text)} characters")

    if full_text and len(full_text) > 100:
        print("\n✅ SUCCESS: Document generated with substantial content")
        print("\nFirst 500 characters of document:")
        print("-" * 80)
        print(full_text[:500])
        print("-" * 80)
        return True
    else:
        print("\n❌ FAILURE: Document is empty or too short")
        print(f"Document: {document}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_autonomous_workflow())
    exit(0 if success else 1)
