"""Document parsing tools for extracting text and metadata from various formats."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from tools.llm_client import get_llm_client


def _format_parties(parties: list) -> str:
    """Format parties list (either strings or dicts) into a comma-separated string."""
    if not parties:
        return "N/A"
    formatted = []
    for p in parties:
        if isinstance(p, dict):
            formatted.append(p.get('name', str(p)))
        else:
            formatted.append(str(p))
    return ', '.join(formatted)


async def parse_document_with_llm(
    document: dict[str, Any],
    matter_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse a document and extract key facts using LLM.

    Args:
        document: Document dict with 'title', 'content', 'file_path', or 'summary'.
        matter_context: Optional context about the matter for better extraction.

    Returns:
        Dict with parsed document including extracted key facts.
    """
    llm = get_llm_client()

    # Extract text content from various sources
    content = ""
    title = document.get("title", "Untitled Document")

    # Try to get content from file path if provided
    file_path = document.get("file_path")
    if file_path and os.path.exists(file_path):
        content = extract_text_from_file(file_path)
    # Otherwise use provided content or summary
    elif document.get("content"):
        content = document["content"]
    elif document.get("summary"):
        content = document["summary"]

    if not content:
        return {
            "document": title,
            "summary": "No content available to parse.",
            "key_facts": [],
            "date": document.get("date"),
        }

    # Truncate very long documents (keep first 10000 chars to stay within token limits)
    content = content[:10000]

    # Build context string if matter context is provided
    context_str = ""
    if matter_context:
        context_str = "\n\nMatter Context:\n"
        if matter_context.get("summary"):
            context_str += f"Summary: {matter_context['summary']}\n"
        if matter_context.get("parties"):
            context_str += f"Parties: {_format_parties(matter_context['parties'])}\n"

    # Create prompt for LLM to extract key facts
    system_prompt = """You are a legal document analyst. Your job is to:
1. Read legal documents carefully
2. Extract key facts that are legally relevant
3. Identify important dates, parties, and events
4. Summarize the document concisely

Be precise and factual. Only include information actually stated in the document."""

    user_prompt = f"""Analyze this legal document and extract key information.

Document Title: {title}
{context_str}

Document Content:
{content}

Please provide:
1. A concise summary (2-3 sentences)
2. A list of key facts (each fact should be one clear sentence)
3. Any dates mentioned
4. Any parties/people mentioned

Respond in JSON format:
{{
  "summary": "concise summary here",
  "key_facts": ["fact 1", "fact 2", "fact 3"],
  "dates": ["YYYY-MM-DD"],
  "parties_mentioned": ["party name"]
}}"""

    response_format = {
        "summary": "string",
        "key_facts": ["string"],
        "dates": ["string"],
        "parties_mentioned": ["string"],
    }

    result = await llm.generate_structured(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format=response_format,
    )

    import logging
    logger = logging.getLogger("themis.tools.document_parser")
    logger.info(f"Document parser LLM response for '{title}': {result}")
    logger.info(f"Extracted {len(result.get('key_facts', []))} key facts")

    # Build the parsed document response
    return {
        "document": title,
        "summary": result.get("summary", "Summary not available."),
        "key_facts": result.get("key_facts", []),
        "date": document.get("date") or next(iter(result.get("dates", [])), None),
        "parties_mentioned": result.get("parties_mentioned", []),
    }


def extract_text_from_file(file_path: str) -> str:
    """Extract text from a file (supports PDF and text files).

    Args:
        file_path: Path to the file.

    Returns:
        Extracted text content.
    """
    path = Path(file_path)

    if not path.exists():
        return ""

    # Handle PDF files
    if path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path)

    # Handle text files
    if path.suffix.lower() in [".txt", ".md", ".json", ".yaml", ".yml"]:
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    return ""


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Extracted text from all pages.
    """
    try:
        reader = PdfReader(file_path)
        text_parts = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        return "\n\n".join(text_parts)
    except Exception as e:
        return f"Error reading PDF: {e!s}"


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes.

    Args:
        pdf_bytes: PDF file content as bytes.

    Returns:
        Extracted text from all pages.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        return "\n\n".join(text_parts)
    except Exception as e:
        return f"Error reading PDF: {e!s}"
