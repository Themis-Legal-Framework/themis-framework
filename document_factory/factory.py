"""Document Factory - Single-call legal document generation.

This module provides a clean, efficient approach to generating legal documents.
It takes a matter and a document request, and produces the requested document
in a single LLM call.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

from document_factory.registry import (
    DocumentTemplate,
    get_document_template,
    list_document_types,
)
from document_factory.prompts import get_system_prompt

logger = logging.getLogger("themis.document_factory")


@dataclass
class DocumentRequest:
    """A request to generate a specific document type."""

    type: str  # Required - the document type to generate
    addressee: str | None = None  # For correspondence
    from_line: str | None = None  # For correspondence
    structure: list[str] | None = None  # Custom sections
    requirements: list[str] | None = None  # Specific requirements
    tone: str | None = None  # Override default tone

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentRequest:
        """Create a DocumentRequest from a dictionary."""
        return cls(
            type=data.get("document_type") or data.get("type"),
            addressee=data.get("addressee"),
            from_line=data.get("from"),
            structure=data.get("structure"),
            requirements=data.get("requirements"),
            tone=data.get("tone"),
        )


@dataclass
class GeneratedDocument:
    """A generated legal document."""

    document_type: str
    content: str
    word_count: int
    template: DocumentTemplate

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "document_type": self.document_type,
            "content": self.content,
            "word_count": self.word_count,
            "template_name": self.template.name,
            "category": self.template.category.value,
        }


class DocumentFactory:
    """Factory for generating legal documents with a single LLM call.

    This class provides a simple, efficient interface for generating
    professional legal documents. It:

    1. Validates the document request
    2. Loads the appropriate template and prompt
    3. Builds a comprehensive prompt with all context
    4. Makes a single LLM call
    5. Returns the generated document

    Example:
        factory = DocumentFactory()
        doc = await factory.generate(
            matter=case_data,
            request=DocumentRequest(type="client_letter", addressee="Mr. Smith")
        )
        print(doc.content)
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8000,
        api_key: str | None = None,
    ):
        """Initialize the document factory.

        Args:
            model: The Claude model to use
            max_tokens: Maximum tokens for generation
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.model = model
        self.max_tokens = max_tokens
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    async def generate(
        self,
        matter: dict[str, Any],
        request: DocumentRequest | dict[str, Any],
    ) -> GeneratedDocument:
        """Generate a legal document.

        Args:
            matter: The case/matter data including facts, parties, issues, etc.
            request: The document request specifying type and requirements

        Returns:
            A GeneratedDocument containing the produced content

        Raises:
            ValueError: If document type is missing or invalid
        """
        # Convert dict to DocumentRequest if needed
        if isinstance(request, dict):
            request = DocumentRequest.from_dict(request)

        # Validate document type
        if not request.type:
            raise ValueError(
                "document_type is required. Specify what document you want to generate. "
                f"Available types: {list(list_document_types().keys())}"
            )

        # Get template for this document type
        template = get_document_template(request.type)
        logger.info(f"Generating {template.name} ({request.type})")

        # Build prompts
        system_prompt = get_system_prompt(request.type, template.category.value)
        user_prompt = self._build_user_prompt(matter, request, template)

        # Single LLM call - no tools, just generation
        logger.debug(f"Calling {self.model} with max_tokens={self.max_tokens}")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract content
        content = response.content[0].text
        word_count = len(content.split())

        logger.info(f"Generated {word_count} words")

        return GeneratedDocument(
            document_type=request.type,
            content=content,
            word_count=word_count,
            template=template,
        )

    def _build_user_prompt(
        self,
        matter: dict[str, Any],
        request: DocumentRequest,
        template: DocumentTemplate,
    ) -> str:
        """Build the user prompt with all context."""

        sections = []

        # Document type and overview
        sections.append(f"## Document to Generate: {template.name}")
        sections.append(f"Document Type: {request.type}")
        sections.append(f"Category: {template.category.value}")
        sections.append("")

        # Specific requirements from request
        if request.addressee:
            sections.append(f"**Addressee**: {request.addressee}")
        if request.from_line:
            sections.append(f"**From**: {request.from_line}")
        if request.tone:
            sections.append(f"**Tone**: {request.tone}")
        sections.append("")

        # Structure requirements
        if request.structure:
            sections.append("## Required Structure")
            for i, section in enumerate(request.structure, 1):
                sections.append(f"{i}. {section}")
            sections.append("")

        # Specific requirements
        if request.requirements:
            sections.append("## Specific Requirements")
            for req in request.requirements:
                sections.append(f"- {req}")
            sections.append("")

        # Case/Matter Information
        sections.append("## Case Information")

        # Metadata
        metadata = matter.get("metadata", {})
        if metadata:
            if metadata.get("title"):
                sections.append(f"**Case**: {metadata['title']}")
            if metadata.get("jurisdiction"):
                sections.append(f"**Jurisdiction**: {metadata['jurisdiction']}")
            if metadata.get("venue"):
                sections.append(f"**Venue**: {metadata['venue']}")
            if metadata.get("case_number"):
                sections.append(f"**Case Number**: {metadata.get('case_number')}")
            sections.append("")

        # Parties
        parties = matter.get("parties", [])
        if parties:
            sections.append("### Parties")
            for party in parties:
                if isinstance(party, str):
                    sections.append(f"- {party}")
                elif isinstance(party, dict):
                    sections.append(f"- {party.get('name', party)}: {party.get('role', '')}")
            sections.append("")

        # Summary
        if matter.get("summary"):
            sections.append("### Case Summary")
            sections.append(matter["summary"])
            sections.append("")

        # Legal Issues
        issues = matter.get("issues", [])
        if issues:
            sections.append("### Legal Issues")
            for i, issue in enumerate(issues, 1):
                if isinstance(issue, dict):
                    sections.append(f"**Issue {i}**: {issue.get('issue', '')}")
                    facts = issue.get("facts", [])
                    for fact in facts:
                        sections.append(f"  - {fact}")
                else:
                    sections.append(f"- {issue}")
            sections.append("")

        # Timeline/Events
        events = matter.get("events", [])
        if events:
            sections.append("### Timeline of Events")
            for event in events:
                if isinstance(event, dict):
                    date = event.get("date", "")
                    desc = event.get("description", "")
                    sections.append(f"- **{date}**: {desc}")
                else:
                    sections.append(f"- {event}")
            sections.append("")

        # Documents/Evidence
        documents = matter.get("documents", [])
        if documents:
            sections.append("### Key Documents")
            for doc in documents:
                if isinstance(doc, dict):
                    title = doc.get("title", "Untitled")
                    date = doc.get("date", "")
                    summary = doc.get("summary", "")
                    sections.append(f"**{title}** ({date})")
                    sections.append(f"  {summary}")
                    facts = doc.get("facts", [])
                    for fact in facts:
                        sections.append(f"  - {fact}")
                else:
                    sections.append(f"- {doc}")
            sections.append("")

        # Legal Authorities
        authorities = matter.get("authorities", [])
        if authorities:
            sections.append("### Applicable Legal Authorities")
            for auth in authorities:
                if isinstance(auth, dict):
                    cite = auth.get("cite", "")
                    summary = auth.get("summary", "")
                    sections.append(f"**{cite}**")
                    sections.append(f"  {summary}")
                else:
                    sections.append(f"- {auth}")
            sections.append("")

        # Strengths and Weaknesses
        strengths = matter.get("strengths", [])
        if strengths:
            sections.append("### Strengths of Position")
            for s in strengths:
                sections.append(f"- {s}")
            sections.append("")

        weaknesses = matter.get("weaknesses", [])
        if weaknesses:
            sections.append("### Weaknesses/Risks")
            for w in weaknesses:
                sections.append(f"- {w}")
            sections.append("")

        # Goals
        goals = matter.get("goals", {})
        if goals:
            sections.append("### Client Goals")
            if isinstance(goals, dict):
                for key, value in goals.items():
                    sections.append(f"- **{key.title()}**: {value}")
            else:
                sections.append(f"- {goals}")
            sections.append("")

        # Final instruction
        sections.append("---")
        sections.append("")
        sections.append(
            f"Generate the complete {template.name} based on the above information. "
            f"Produce a professional, ready-to-use document that requires minimal revision. "
            f"Follow all formatting requirements for a {template.category.value} document."
        )

        return "\n".join(sections)

    @staticmethod
    def available_document_types() -> dict[str, list[str]]:
        """List all available document types grouped by category."""
        return list_document_types()


# Convenience function for simple usage
async def generate_document(
    matter: dict[str, Any],
    document_type: str,
    **kwargs,
) -> GeneratedDocument:
    """Generate a legal document with minimal configuration.

    Args:
        matter: The case/matter data
        document_type: The type of document to generate
        **kwargs: Additional request parameters (addressee, requirements, etc.)

    Returns:
        The generated document
    """
    factory = DocumentFactory()
    request = DocumentRequest(type=document_type, **kwargs)
    return await factory.generate(matter, request)
