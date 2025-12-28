"""Jurisdictional and cause-specific rule helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from packs.personal_injury.llm_support import run_structured_prompt
from packs.personal_injury.schema import PersonalInjuryMatter


@dataclass(slots=True)
class JurisdictionProfile:
    """Normalized view of personal-injury rules for a jurisdiction."""

    statute_years: int | None = None
    comparative_fault: dict[str, int] = field(
        default_factory=lambda: {"plaintiff": 0, "defendant": 100}
    )
    jury_instructions: list[str] = field(default_factory=list)
    affirmative_defenses: list[str] = field(default_factory=list)
    damages_multiplier: float | None = None


DEFAULT_PROFILE = JurisdictionProfile(
    statute_years=2,
    comparative_fault={"plaintiff": 0, "defendant": 100},
    jury_instructions=["Model negligence instruction"],
    affirmative_defenses=[],
    damages_multiplier=2.5,
)


SEED_PROFILES: dict[str, JurisdictionProfile] = {
    "california": JurisdictionProfile(
        statute_years=2,
        comparative_fault={"plaintiff": 0, "defendant": 100},
        jury_instructions=["CACI 400 - Negligence", "CACI 3920 - Personal Injury Damages"],
        affirmative_defenses=["Comparative negligence", "Failure to mitigate damages"],
        damages_multiplier=3.0,
    ),
    "new york": JurisdictionProfile(
        statute_years=3,
        comparative_fault={"plaintiff": 0, "defendant": 100},
        jury_instructions=["PJI 2:10 - Negligence", "PJI 2:277 - Damages"],
        affirmative_defenses=["Comparative negligence", "Seat belt defense"],
        damages_multiplier=3.5,
    ),
    "texas": JurisdictionProfile(
        statute_years=2,
        comparative_fault={"plaintiff": 0, "defendant": 100},
        jury_instructions=["PJC 2.1 - Negligence", "PJC 8.1 - Damages"],
        affirmative_defenses=["Proportionate responsibility", "Statute of limitations"],
        damages_multiplier=2.8,
    ),
    "florida": JurisdictionProfile(
        statute_years=4,
        comparative_fault={"plaintiff": 10, "defendant": 90},
        jury_instructions=["FJI 401 - Negligence"],
        affirmative_defenses=["Comparative negligence", "Fabre apportionment"],
        damages_multiplier=2.5,
    ),
    "illinois": JurisdictionProfile(
        statute_years=2,
        comparative_fault={"plaintiff": 5, "defendant": 95},
        jury_instructions=["IPI 10.01 - Negligence", "IPI 30.01 - Damages"],
        affirmative_defenses=["Comparative negligence", "Failure to mitigate"],
        damages_multiplier=3.0,
    ),
}


_PROFILE_CACHE: dict[str, JurisdictionProfile] = dict(SEED_PROFILES)


PLEADING_ELEMENTS: dict[str, dict[str, list[str]]] = {
    "negligence": {
        "Negligence": [
            "Duty of care owed by Defendant",
            "Breach of duty",
            "Causation",
            "Damages suffered by Plaintiff",
        ]
    },
    "motor_vehicle": {
        "Negligence Per Se": [
            "Existence of traffic statute",
            "Violation of statute",
            "Causation of injury",
        ]
    },
    "premises_liability": {
        "Premises Liability": [
            "Possession of premises",
            "Dangerous condition",
            "Defendant had notice",
            "Failure to remedy",
        ]
    },
}


_PROFILE_PROMPT = """You are assisting a personal injury litigation team.\n\n"
"Return concise procedural rules for the requested jurisdiction."""


def _normalize_key(jurisdiction: str | None) -> str | None:
    if jurisdiction is None:
        return None
    cleaned = jurisdiction.strip()
    return cleaned.lower() or None


def _resolve_profile(jurisdiction: str | None, cause: str | None) -> JurisdictionProfile:
    key = _normalize_key(jurisdiction)
    if not key:
        return DEFAULT_PROFILE
    if key in _PROFILE_CACHE:
        return _PROFILE_CACHE[key]

    payload = run_structured_prompt(
        system_prompt=_PROFILE_PROMPT,
        user_prompt=(
            "Jurisdiction: {jurisdiction}\nCause of action: {cause}".format(
                jurisdiction=jurisdiction,
                cause=cause or "personal injury negligence",
            )
        ),
        response_format={
            "statute_years": 0,
            "comparative_fault": {"plaintiff": 0, "defendant": 100},
            "jury_instructions": [],
            "affirmative_defenses": [],
            "damages_multiplier": 0.0,
        },
    )
    profile = _merge_profile(DEFAULT_PROFILE, payload)
    _PROFILE_CACHE[key] = profile
    return profile


def _merge_profile(default: JurisdictionProfile, payload: dict[str, Any]) -> JurisdictionProfile:
    statute_years = _coerce_int(payload.get("statute_years"), default.statute_years)
    multiplier = _coerce_float(payload.get("damages_multiplier"), default.damages_multiplier)
    comparative = _normalize_fault(payload.get("comparative_fault"), default.comparative_fault)
    instructions = _normalize_list(payload.get("jury_instructions"), default.jury_instructions)
    defenses = _normalize_list(payload.get("affirmative_defenses"), default.affirmative_defenses)

    return JurisdictionProfile(
        statute_years=statute_years,
        comparative_fault=comparative,
        jury_instructions=instructions,
        affirmative_defenses=defenses,
        damages_multiplier=multiplier,
    )


def _coerce_int(value: Any, fallback: int | None) -> int | None:
    if value in (None, ""):
        return fallback
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _coerce_float(value: Any, fallback: float | None) -> float | None:
    if value in (None, ""):
        return fallback
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _normalize_fault(
    payload: Any, fallback: dict[str, int]
) -> dict[str, int]:
    if not isinstance(payload, dict):
        return dict(fallback)
    plaintiff = _coerce_int(payload.get("plaintiff"), fallback.get("plaintiff"))
    defendant = _coerce_int(payload.get("defendant"), fallback.get("defendant"))
    result = {
        "plaintiff": plaintiff if plaintiff is not None else fallback.get("plaintiff", 0),
        "defendant": defendant if defendant is not None else fallback.get("defendant", 100),
    }
    if result["plaintiff"] + result["defendant"] == 0:
        return dict(fallback)
    return result


def _normalize_list(payload: Any, fallback: list[str]) -> list[str]:
    if isinstance(payload, list) and payload:
        return [str(item) for item in payload if str(item).strip()]
    return list(fallback)


def statute_of_limitations(matter: PersonalInjuryMatter) -> date | None:
    profile = _resolve_profile(matter.metadata.jurisdiction, matter.metadata.cause_of_action)
    years = profile.statute_years
    if years is None:
        return None
    timeline = matter.fact_pattern.timeline
    if not timeline:
        return None
    first_event = timeline[0].get("date")
    if not first_event:
        return None
    try:
        event_date = date.fromisoformat(first_event)
    except ValueError:
        return None
    return event_date + timedelta(days=365 * years)


def damages_multiplier(matter: PersonalInjuryMatter) -> float:
    profile = _resolve_profile(matter.metadata.jurisdiction, matter.metadata.cause_of_action)
    return profile.damages_multiplier or DEFAULT_PROFILE.damages_multiplier or 2.5


def jury_instructions_for(matter: PersonalInjuryMatter) -> list[str]:
    profile = _resolve_profile(matter.metadata.jurisdiction, matter.metadata.cause_of_action)
    instructions = profile.jury_instructions or DEFAULT_PROFILE.jury_instructions
    return instructions or ["Model negligence instruction"]


def pleading_elements(matter: PersonalInjuryMatter) -> dict[str, list[str]]:
    cause = matter.metadata.cause_of_action or "negligence"
    return PLEADING_ELEMENTS.get(cause, PLEADING_ELEMENTS["negligence"])


def affirmative_defenses(matter: PersonalInjuryMatter) -> list[str]:
    profile = _resolve_profile(matter.metadata.jurisdiction, matter.metadata.cause_of_action)
    return profile.affirmative_defenses or []


def comparative_fault_apportionment(matter: PersonalInjuryMatter) -> dict[str, int]:
    profile = _resolve_profile(matter.metadata.jurisdiction, matter.metadata.cause_of_action)
    return profile.comparative_fault or DEFAULT_PROFILE.comparative_fault
