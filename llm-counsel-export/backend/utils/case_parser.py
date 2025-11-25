"""
Case Citation Parser

Utilities for parsing and formatting legal case citations.
"""
from __future__ import annotations

import re
from typing import TypedDict


class ParsedCitation(TypedDict, total=False):
    """Parsed components of a legal citation."""
    case_name: str
    volume: str
    reporter: str
    page: str
    court: str
    year: str
    pinpoint: str | None
    raw: str


# Common reporter abbreviations
REPORTERS = {
    # Federal
    "U.S.": "United States Reports",
    "S. Ct.": "Supreme Court Reporter",
    "L. Ed.": "Lawyers' Edition",
    "L. Ed. 2d": "Lawyers' Edition, Second Series",
    "F.": "Federal Reporter",
    "F.2d": "Federal Reporter, Second Series",
    "F.3d": "Federal Reporter, Third Series",
    "F.4th": "Federal Reporter, Fourth Series",
    "F. Supp.": "Federal Supplement",
    "F. Supp. 2d": "Federal Supplement, Second Series",
    "F. Supp. 3d": "Federal Supplement, Third Series",
    "F.R.D.": "Federal Rules Decisions",
    # State
    "Cal.": "California Reports",
    "Cal. 2d": "California Reports, Second Series",
    "Cal. 3d": "California Reports, Third Series",
    "Cal. 4th": "California Reports, Fourth Series",
    "Cal. 5th": "California Reports, Fifth Series",
    "Cal. App.": "California Appellate Reports",
    "Cal. App. 2d": "California Appellate Reports, Second Series",
    "Cal. App. 3d": "California Appellate Reports, Third Series",
    "Cal. App. 4th": "California Appellate Reports, Fourth Series",
    "Cal. App. 5th": "California Appellate Reports, Fifth Series",
    "Cal. Rptr.": "California Reporter",
    "Cal. Rptr. 2d": "California Reporter, Second Series",
    "Cal. Rptr. 3d": "California Reporter, Third Series",
    "N.Y.": "New York Reports",
    "N.Y.2d": "New York Reports, Second Series",
    "N.Y.3d": "New York Reports, Third Series",
    "A.D.": "Appellate Division Reports",
    "A.D.2d": "Appellate Division Reports, Second Series",
    "A.D.3d": "Appellate Division Reports, Third Series",
    "N.Y.S.": "New York Supplement",
    "N.Y.S.2d": "New York Supplement, Second Series",
    "N.Y.S.3d": "New York Supplement, Third Series",
}


def parse_case_citation(citation: str) -> ParsedCitation | None:
    """
    Parse a legal case citation into components.

    Args:
        citation: The citation string (e.g., "Brown v. Board of Education, 347 U.S. 483 (1954)")

    Returns:
        ParsedCitation dict or None if parsing fails
    """
    # Pattern for standard case citations
    # Case Name, Volume Reporter Page (Court Year)
    pattern = r"""
        ^(.+?)\s*,\s*                      # Case name
        (\d+)\s+                            # Volume
        ([A-Za-z.\s]+\d*[a-z]*)\s+          # Reporter
        (\d+)                               # Starting page
        (?:\s*,\s*(\d+))?                   # Optional pinpoint page
        \s*\(([^)]+)\s+(\d{4})\)            # Court and year
    """

    match = re.match(pattern, citation.strip(), re.VERBOSE | re.IGNORECASE)

    if match:
        return ParsedCitation(
            case_name=match.group(1).strip(),
            volume=match.group(2),
            reporter=match.group(3).strip(),
            page=match.group(4),
            pinpoint=match.group(5) if match.group(5) else None,
            court=match.group(6).strip(),
            year=match.group(7),
            raw=citation
        )

    # Try simpler pattern without court
    simple_pattern = r"""
        ^(.+?)\s*,\s*                      # Case name
        (\d+)\s+                            # Volume
        ([A-Za-z.\s]+\d*[a-z]*)\s+          # Reporter
        (\d+)                               # Starting page
        \s*\((\d{4})\)                      # Year only
    """

    match = re.match(simple_pattern, citation.strip(), re.VERBOSE | re.IGNORECASE)

    if match:
        return ParsedCitation(
            case_name=match.group(1).strip(),
            volume=match.group(2),
            reporter=match.group(3).strip(),
            page=match.group(4),
            year=match.group(5),
            raw=citation
        )

    return None


def format_bluebook_citation(parsed: ParsedCitation) -> str:
    """
    Format a parsed citation in proper Bluebook format.

    Args:
        parsed: The parsed citation components

    Returns:
        Formatted citation string
    """
    parts = [
        f"{parsed['case_name']},",
        parsed['volume'],
        parsed['reporter'],
        parsed['page'],
    ]

    if parsed.get('pinpoint'):
        parts.append(f", {parsed['pinpoint']}")

    if parsed.get('court'):
        parts.append(f"({parsed['court']} {parsed['year']})")
    else:
        parts.append(f"({parsed['year']})")

    return " ".join(parts)


def extract_citations_from_text(text: str) -> list[str]:
    """
    Extract case citations from a block of text.

    Args:
        text: Text that may contain case citations

    Returns:
        List of citation strings found
    """
    # Pattern to find citations
    pattern = r"""
        [A-Z][a-zA-Z\s.,']+           # Case name starting with capital
        v\.\s+                         # "v." separator
        [A-Z][a-zA-Z\s.,']+           # Other party
        ,\s*                          # Comma
        \d+\s+                        # Volume
        [A-Za-z.\s]+\d*[a-z]*\s+      # Reporter
        \d+                           # Page
        \s*\([^)]+\)                  # Parenthetical
    """

    matches = re.findall(pattern, text, re.VERBOSE)
    return [m.strip() for m in matches]
