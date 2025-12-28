"""Shared matter schema for personal injury practice assets."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

SCHEMA_VERSION = "2024.10"


@dataclass(slots=True)
class Party:
    """Party to the litigation."""

    name: str
    role: str
    counsel: str | None = None
    contact: str | None = None


@dataclass(slots=True)
class InsurancePolicy:
    """Insurance coverage information."""

    carrier: str
    policy_number: str | None = None
    coverage_limits: str | None = None
    adjuster: str | None = None
    contact: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class Deadline:
    """Important deadline tied to the matter."""

    name: str
    due: date
    description: str | None = None
    source: str | None = None


@dataclass(slots=True)
class MedicalRecord:
    """Record produced by a medical provider."""

    provider: str
    date_of_service: date | None = None
    description: str | None = None
    balance: float | None = None
    notes: str | None = None


@dataclass(slots=True)
class MedicalProvider:
    name: str
    specialty: str | None = None
    contact: str | None = None
    records: list[MedicalRecord] = field(default_factory=list)


@dataclass(slots=True)
class Injury:
    description: str
    body_parts: list[str] = field(default_factory=list)
    severity: str | None = None
    treatment: str | None = None
    prognosis: str | None = None


@dataclass(slots=True)
class LiabilityTheory:
    name: str
    facts: list[str] = field(default_factory=list)
    defenses: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DamagesProfile:
    specials: float = 0.0
    generals: float = 0.0
    punitive: float = 0.0
    wage_loss: float = 0.0
    future_medical: float = 0.0
    notes: str | None = None

    def total(self) -> float:
        return float(
            (self.specials or 0)
            + (self.generals or 0)
            + (self.punitive or 0)
            + (self.wage_loss or 0)
            + (self.future_medical or 0)
        )


@dataclass(slots=True)
class FactPattern:
    incident_description: str
    timeline: list[dict[str, str]] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    witnesses: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MatterMetadata:
    id: str
    title: str
    jurisdiction: str
    venue: str | None = None
    cause_of_action: str | None = None
    phase: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class PersonalInjuryMatter:
    metadata: MatterMetadata
    parties: list[Party]
    insurance: list[InsurancePolicy]
    deadlines: list[Deadline]
    injuries: list[Injury]
    medical_providers: list[MedicalProvider]
    liability: list[LiabilityTheory]
    damages: DamagesProfile
    fact_pattern: FactPattern
    objectives: dict[str, Any] = field(default_factory=dict)
    notes: dict[str, Any] = field(default_factory=dict)
    source_data: dict[str, Any] = field(default_factory=dict)


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _coerce_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_matter(data: dict[str, Any]) -> PersonalInjuryMatter:
    """Load a matter dictionary into the shared schema dataclasses."""

    envelope = data.get("matter", data)

    metadata_raw = envelope.get("metadata", {})

    summary_value = envelope.get("summary") or envelope.get("description")
    facts_section = envelope.get("facts") or {}
    incident_description = facts_section.get("incident_description")
    if not (summary_value or incident_description):
        raise ValueError("Matter must include a summary or facts.incident_description")

    metadata = MatterMetadata(
        id=str(metadata_raw.get("id", "UNKNOWN")),
        title=str(metadata_raw.get("title", envelope.get("title", "Untitled Matter"))),
        jurisdiction=str(metadata_raw.get("jurisdiction", "California")),
        venue=metadata_raw.get("venue") or envelope.get("venue"),
        cause_of_action=(metadata_raw.get("cause_of_action") or envelope.get("cause_of_action")),
        phase=(metadata_raw.get("phase") or envelope.get("phase")),
        created_at=_parse_datetime(metadata_raw.get("created_at")),
    )

    parties: list[Party] = []
    for party in _ensure_list(envelope.get("parties")):
        if isinstance(party, str):
            parties.append(Party(name=party, role="unknown"))
        elif isinstance(party, dict):
            parties.append(
                Party(
                    name=str(party.get("name") or party.get("party") or "Unknown"),
                    role=str(party.get("role", "unknown")),
                    counsel=party.get("counsel"),
                    contact=party.get("contact"),
                )
            )

    insurance: list[InsurancePolicy] = []
    for policy in _ensure_list(envelope.get("insurance")):
        if isinstance(policy, dict):
            insurance.append(
                InsurancePolicy(
                    carrier=str(policy.get("carrier", "Unknown Carrier")),
                    policy_number=policy.get("policy_number"),
                    coverage_limits=policy.get("coverage_limits"),
                    adjuster=policy.get("adjuster"),
                    contact=policy.get("contact"),
                    notes=policy.get("notes"),
                )
            )

    deadlines: list[Deadline] = []
    for deadline in _ensure_list(envelope.get("deadlines")):
        if isinstance(deadline, dict) and deadline.get("name"):
            due = _parse_date(deadline.get("due"))
            if due:
                deadlines.append(
                    Deadline(
                        name=str(deadline["name"]),
                        due=due,
                        description=deadline.get("description"),
                        source=deadline.get("source"),
                    )
                )

    injuries: list[Injury] = []
    for injury in _ensure_list(envelope.get("injuries")):
        if isinstance(injury, dict) and injury.get("description"):
            injuries.append(
                Injury(
                    description=str(injury["description"]),
                    body_parts=[str(p) for p in _ensure_list(injury.get("body_parts"))],
                    severity=injury.get("severity"),
                    treatment=injury.get("treatment"),
                    prognosis=injury.get("prognosis"),
                )
            )

    medical_providers: list[MedicalProvider] = []
    for provider in _ensure_list(envelope.get("medical")):
        if isinstance(provider, dict) and provider.get("name"):
            records: list[MedicalRecord] = []
            for record in _ensure_list(provider.get("records")):
                if isinstance(record, dict):
                    records.append(
                        MedicalRecord(
                            provider=str(provider.get("name")),
                            date_of_service=_parse_date(record.get("date")),
                            description=record.get("description"),
                            balance=_coerce_float(record.get("balance")),
                            notes=record.get("notes"),
                        )
                    )
            medical_providers.append(
                MedicalProvider(
                    name=str(provider.get("name")),
                    specialty=provider.get("specialty"),
                    contact=provider.get("contact"),
                    records=records,
                )
            )

    liability: list[LiabilityTheory] = []
    for theory in _ensure_list(envelope.get("liability")):
        if isinstance(theory, dict) and theory.get("name"):
            liability.append(
                LiabilityTheory(
                    name=str(theory.get("name")),
                    facts=[str(f) for f in _ensure_list(theory.get("facts"))],
                    defenses=[str(d) for d in _ensure_list(theory.get("defenses"))],
                )
            )

    damages_raw = envelope.get("damages", {})
    damages = DamagesProfile(
        specials=_coerce_float(damages_raw.get("specials")),
        generals=_coerce_float(damages_raw.get("generals")),
        punitive=_coerce_float(damages_raw.get("punitive")),
        wage_loss=_coerce_float(damages_raw.get("wage_loss")),
        future_medical=_coerce_float(damages_raw.get("future_medical")),
        notes=damages_raw.get("notes"),
    )

    fact_raw = envelope.get("facts") or {}
    timeline_entries = []
    for event in _ensure_list(fact_raw.get("timeline") or envelope.get("events")):
        if isinstance(event, dict):
            entry = {
                "date": event.get("date"),
                "description": event.get("description") or event.get("summary"),
            }
            if any(entry.values()):
                timeline_entries.append(entry)
        elif isinstance(event, str):
            timeline_entries.append({"description": event})

    fact_pattern = FactPattern(
        incident_description=str(
            fact_raw.get("incident_description")
            or envelope.get("summary")
            or envelope.get("description")
            or ""
        ),
        timeline=timeline_entries,
        evidence=[str(item) for item in _ensure_list(fact_raw.get("evidence") or envelope.get("documents"))],
        witnesses=[str(w) for w in _ensure_list(fact_raw.get("witnesses") or envelope.get("witnesses"))],
    )

    objectives = envelope.get("goals") or envelope.get("objectives") or {}
    notes = envelope.get("notes") or {}

    return PersonalInjuryMatter(
        metadata=metadata,
        parties=parties,
        insurance=insurance,
        deadlines=deadlines,
        injuries=injuries,
        medical_providers=medical_providers,
        liability=liability,
        damages=damages,
        fact_pattern=fact_pattern,
        objectives=objectives if isinstance(objectives, dict) else {},
        notes=notes if isinstance(notes, dict) else {},
        source_data=data,
    )


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(value, fmt)
                if fmt == "%Y-%m-%d":
                    parsed = datetime.combine(parsed.date(), datetime.min.time())
                return parsed
            except ValueError:
                continue
    return None


def matter_summary(matter: PersonalInjuryMatter) -> dict[str, Any]:
    """Produce a machine-consumable summary for analytics and logging."""

    return {
        "schema_version": SCHEMA_VERSION,
        "matter_id": matter.metadata.id,
        "jurisdiction": matter.metadata.jurisdiction,
        "phase": matter.metadata.phase,
        "cause_of_action": matter.metadata.cause_of_action,
        "party_roles": sorted({party.role for party in matter.parties}),
        "insurance_carriers": [policy.carrier for policy in matter.insurance],
        "deadline_count": len(matter.deadlines),
        "injury_count": len(matter.injuries),
        "medical_provider_count": len(matter.medical_providers),
        "damages_total": matter.damages.total(),
    }


def required_fields() -> dict[str, Iterable[str]]:
    """Return required field hints grouped by area for documentation."""

    return {
        "metadata": ["id", "title", "jurisdiction", "cause_of_action"],
        "parties": ["name", "role"],
        "facts": ["incident_description"],
        "damages": ["specials", "generals"],
        "liability": ["name"],
    }
