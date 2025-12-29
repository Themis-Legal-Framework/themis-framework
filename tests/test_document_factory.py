"""Test the Document Factory with the Jamison v. Sunrise spoliation case.

This test demonstrates the new architecture:
- Single LLM call
- Explicit document type
- Fast execution (< 2 minutes)
"""

import asyncio
import json
import time
from pathlib import Path

from document_factory import (
    DocumentFactory,
    DocumentRequest,
    list_document_types,
)


async def test_client_letter():
    """Generate a client letter for the spoliation case."""

    print("\n" + "=" * 70)
    print("DOCUMENT FACTORY TEST")
    print("Jamison v. Sunrise Ladder Co., Inc. - Client Letter")
    print("=" * 70 + "\n")

    # Load the fixture
    fixture_path = Path("/tmp/themis-framework/packs/personal_injury/fixtures/spoliation_ladder_columbia.json")
    fixture_data = json.loads(fixture_path.read_text())
    matter = fixture_data.get("matter", fixture_data)

    # Extract the document request from output_format
    output_format = matter.get("output_format", {})

    print(f"Document Type Requested: {output_format.get('document_type')}")
    print(f"Addressee: {output_format.get('addressee')}")
    print(f"From: {output_format.get('from')}")
    print()

    # Create the document request
    request = DocumentRequest(
        type=output_format.get("document_type", "client_letter"),
        addressee=output_format.get("addressee"),
        from_line=output_format.get("from"),
        structure=output_format.get("structure"),
        requirements=output_format.get("requirements"),
    )

    # Create factory and generate
    factory = DocumentFactory()

    print("Generating document with single LLM call...")
    start_time = time.time()

    doc = await factory.generate(matter=matter, request=request)

    elapsed = time.time() - start_time
    print(f"Generation complete in {elapsed:.1f} seconds")
    print(f"Document type: {doc.document_type}")
    print(f"Word count: {doc.word_count}")
    print()

    # Save the document
    output_dir = Path("/tmp/spoliation_output")
    output_dir.mkdir(exist_ok=True)

    doc_path = output_dir / "client_letter_v2.txt"
    doc_path.write_text(doc.content)
    print(f"Document saved to: {doc_path}")

    # Print the document
    print("\n" + "=" * 70)
    print("GENERATED CLIENT LETTER")
    print("=" * 70 + "\n")
    print(doc.content)

    return doc


async def test_motion_sanctions():
    """Generate a motion for sanctions for comparison."""

    print("\n" + "=" * 70)
    print("DOCUMENT FACTORY TEST")
    print("Jamison v. Sunrise Ladder Co., Inc. - Motion for Sanctions")
    print("=" * 70 + "\n")

    # Load the fixture
    fixture_path = Path("/tmp/themis-framework/packs/personal_injury/fixtures/spoliation_ladder_columbia.json")
    fixture_data = json.loads(fixture_path.read_text())
    matter = fixture_data.get("matter", fixture_data)

    # Create the document request - explicitly request motion
    request = DocumentRequest(
        type="motion_sanctions",
        requirements=[
            "Apply Brown v. Waldrop four-factor test",
            "Request adverse inference instruction",
            "Include certificate of service"
        ],
    )

    # Create factory and generate
    factory = DocumentFactory()

    print("Generating motion for sanctions...")
    start_time = time.time()

    doc = await factory.generate(matter=matter, request=request)

    elapsed = time.time() - start_time
    print(f"Generation complete in {elapsed:.1f} seconds")
    print(f"Word count: {doc.word_count}")

    # Save the document
    output_dir = Path("/tmp/spoliation_output")
    output_dir.mkdir(exist_ok=True)

    doc_path = output_dir / "motion_sanctions_v2.txt"
    doc_path.write_text(doc.content)
    print(f"Document saved to: {doc_path}")

    return doc


async def list_available_types():
    """Show all available document types."""

    print("\n" + "=" * 70)
    print("AVAILABLE DOCUMENT TYPES")
    print("=" * 70 + "\n")

    types_by_category = list_document_types()

    for category, doc_types in sorted(types_by_category.items()):
        print(f"\n{category.upper()}:")
        for dt in sorted(doc_types):
            print(f"  - {dt}")


async def main():
    """Run the tests."""

    # Show available types
    await list_available_types()

    # Generate client letter (what the fixture requested)
    print("\n\n")
    await test_client_letter()

    # Optionally generate motion for comparison
    # Uncomment to test motion generation:
    # print("\n\n")
    # await test_motion_sanctions()


if __name__ == "__main__":
    asyncio.run(main())
