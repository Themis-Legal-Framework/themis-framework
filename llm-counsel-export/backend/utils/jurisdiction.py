"""
Jurisdiction Detection and Utilities

Utilities for detecting and working with legal jurisdictions.
"""
from __future__ import annotations

import re
from typing import TypedDict


class JurisdictionInfo(TypedDict):
    """Information about a jurisdiction."""
    code: str
    name: str
    type: str  # "federal", "state", "circuit"
    rules: str  # Primary procedural rules
    evidence_rules: str


JURISDICTIONS: dict[str, JurisdictionInfo] = {
    "federal": {
        "code": "federal",
        "name": "Federal District Court",
        "type": "federal",
        "rules": "Federal Rules of Civil Procedure (FRCP)",
        "evidence_rules": "Federal Rules of Evidence (FRE)"
    },
    "ca_state": {
        "code": "ca_state",
        "name": "California State Court",
        "type": "state",
        "rules": "California Code of Civil Procedure",
        "evidence_rules": "California Evidence Code"
    },
    "ny_state": {
        "code": "ny_state",
        "name": "New York State Court",
        "type": "state",
        "rules": "New York Civil Practice Law and Rules (CPLR)",
        "evidence_rules": "New York Evidence Rules"
    },
    "tx_state": {
        "code": "tx_state",
        "name": "Texas State Court",
        "type": "state",
        "rules": "Texas Rules of Civil Procedure",
        "evidence_rules": "Texas Rules of Evidence"
    },
    "fl_state": {
        "code": "fl_state",
        "name": "Florida State Court",
        "type": "state",
        "rules": "Florida Rules of Civil Procedure",
        "evidence_rules": "Florida Evidence Code"
    },
    "il_state": {
        "code": "il_state",
        "name": "Illinois State Court",
        "type": "state",
        "rules": "Illinois Code of Civil Procedure",
        "evidence_rules": "Illinois Rules of Evidence"
    },
    "9th_circuit": {
        "code": "9th_circuit",
        "name": "Ninth Circuit Court of Appeals",
        "type": "circuit",
        "rules": "Federal Rules of Appellate Procedure + 9th Circuit Rules",
        "evidence_rules": "Federal Rules of Evidence (FRE)"
    },
    "2nd_circuit": {
        "code": "2nd_circuit",
        "name": "Second Circuit Court of Appeals",
        "type": "circuit",
        "rules": "Federal Rules of Appellate Procedure + 2nd Circuit Rules",
        "evidence_rules": "Federal Rules of Evidence (FRE)"
    },
    "5th_circuit": {
        "code": "5th_circuit",
        "name": "Fifth Circuit Court of Appeals",
        "type": "circuit",
        "rules": "Federal Rules of Appellate Procedure + 5th Circuit Rules",
        "evidence_rules": "Federal Rules of Evidence (FRE)"
    },
}


# Keywords that suggest specific jurisdictions
JURISDICTION_KEYWORDS = {
    "federal": ["federal court", "district court", "frcp", "federal rules", "28 u.s.c.", "diversity jurisdiction", "federal question"],
    "ca_state": ["california", "cal. civ. proc.", "california code", "superior court of california", "cal. app.", "california supreme"],
    "ny_state": ["new york", "cplr", "supreme court of new york", "n.y.s.", "new york supreme"],
    "tx_state": ["texas", "tex. r. civ. p.", "texas district court", "texas supreme"],
    "fl_state": ["florida", "fla. r. civ. p.", "florida circuit court", "florida supreme"],
    "9th_circuit": ["ninth circuit", "9th circuit", "9th cir.", "california federal"],
    "2nd_circuit": ["second circuit", "2nd circuit", "2nd cir.", "new york federal"],
    "5th_circuit": ["fifth circuit", "5th circuit", "5th cir.", "texas federal"],
}


def detect_jurisdiction(text: str) -> str | None:
    """
    Attempt to detect the jurisdiction from text content.

    Args:
        text: Text that may indicate a jurisdiction

    Returns:
        Jurisdiction code or None if not detected
    """
    text_lower = text.lower()

    # Check for keyword matches
    scores: dict[str, int] = {}

    for jurisdiction, keywords in JURISDICTION_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in text_lower:
                score += 1
        if score > 0:
            scores[jurisdiction] = score

    if not scores:
        return None

    # Return highest scoring jurisdiction
    return max(scores, key=scores.get)


def get_jurisdiction_info(code: str) -> JurisdictionInfo | None:
    """
    Get information about a jurisdiction by code.

    Args:
        code: The jurisdiction code (e.g., "federal", "ca_state")

    Returns:
        JurisdictionInfo or None if not found
    """
    return JURISDICTIONS.get(code)


def get_all_jurisdictions() -> list[dict]:
    """
    Get all available jurisdictions for UI display.

    Returns:
        List of jurisdiction info dicts
    """
    return [
        {"code": code, "name": info["name"], "type": info["type"]}
        for code, info in JURISDICTIONS.items()
    ]
