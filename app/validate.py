"""
Validation and confidence gating.

This is the part that makes the difference between a demo and something an
office will actually trust. A vision model will return a wrong date without
hesitating; these rules are what catch it.

Nothing here calls a model. It is ordinary business logic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Optional

from .schema import FIELDS_BY_NAME, FieldSpec

Severity = Literal["ok", "warn", "error"]

# Below this, send it to a human regardless of whether the rules pass.
CONFIDENCE_FLOOR = 0.85

# California personal injury statute of limitations, in years.
SOL_YEARS = 2

DATE_FORMATS = (
    "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y",
    "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y",
)

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}


@dataclass
class FieldResult:
    name: str
    label: str
    value: Optional[str]
    normalized: Optional[str]
    confidence: float
    severity: Severity
    messages: list[str]
    note: Optional[str] = None

    @property
    def needs_review(self) -> bool:
        return self.severity != "ok"


def parse_date(raw: str) -> Optional[date]:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def digits(raw: str) -> str:
    return re.sub(r"\D", "", raw)


def _check_field(spec: FieldSpec, value: Optional[str]) -> tuple[Optional[str], list[str], Severity]:
    """Returns (normalized value, messages, severity) for one field."""
    msgs: list[str] = []

    if value is None or not value.strip():
        if spec.required:
            return None, [f"{spec.label} is required but was not found"], "error"
        return None, [], "ok"

    raw = value.strip()

    if spec.kind == "date":
        parsed = parse_date(raw)
        if parsed is None:
            return raw, [f"Could not read '{raw}' as a date"], "error"
        if parsed > date.today():
            return parsed.isoformat(), ["Date is in the future"], "error"
        if spec.name == "date_of_birth":
            age = (date.today() - parsed).days / 365.25
            if age > 120:
                return parsed.isoformat(), [f"Implies an age of {age:.0f}"], "error"
            if age < 18:
                msgs.append(f"Client is a minor (age {age:.0f}) — guardian info needed")
                return parsed.isoformat(), msgs, "warn"
        return parsed.isoformat(), msgs, "ok"

    if spec.kind == "phone":
        d = digits(raw)
        if len(d) == 11 and d.startswith("1"):
            d = d[1:]
        if len(d) != 10:
            return raw, [f"'{raw}' is not a 10-digit US number"], "error"
        return f"({d[0:3]}) {d[3:6]}-{d[6:]}", [], "ok"

    if spec.kind == "email":
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", raw):
            return raw, [f"'{raw}' is not a valid email address"], "error"
        return raw.lower(), [], "ok"

    if spec.kind == "zip":
        d = digits(raw)
        if len(d) not in (5, 9):
            return raw, [f"'{raw}' is not a valid ZIP code"], "error"
        return d[:5], [], "ok"

    if spec.kind == "state":
        up = raw.upper().strip().rstrip(".")
        if up in US_STATES:
            return up, [], "ok"
        return raw, [f"'{raw}' is not a recognized state code"], "error"

    if spec.kind == "choice":
        low = raw.lower().strip()
        if low in spec.choices:
            return low, [], "ok"
        for c in spec.choices:
            if c in low or low in c:
                return c, [f"Read '{raw}', matched to '{c}'"], "warn"
        return raw, [f"'{raw}' is not one of the expected case types"], "warn"

    return raw, [], "ok"


def _cross_field_checks(results: dict[str, FieldResult]) -> None:
    """Rules that need more than one field. Mutates results in place."""
    dob = results.get("date_of_birth")
    incident = results.get("date_of_incident")

    if dob and incident and dob.normalized and incident.normalized:
        try:
            d_dob = date.fromisoformat(dob.normalized)
            d_inc = date.fromisoformat(incident.normalized)
        except ValueError:
            return

        if d_inc < d_dob:
            incident.messages.append("Incident predates the client's date of birth")
            incident.severity = "error"

        # Statute of limitations — the check a paralegal would do by hand.
        days_elapsed = (date.today() - d_inc).days
        years_elapsed = days_elapsed / 365.25
        if years_elapsed > SOL_YEARS:
            incident.messages.append(
                f"Incident was {years_elapsed:.1f} years ago — past the "
                f"{SOL_YEARS}-year statute of limitations"
            )
            incident.severity = "error"
        elif years_elapsed > SOL_YEARS - 0.25:
            days_left = int(SOL_YEARS * 365.25 - days_elapsed)
            incident.messages.append(
                f"Statute of limitations expires in about {days_left} days"
            )
            if incident.severity == "ok":
                incident.severity = "warn"


def validate(extracted: dict) -> list[FieldResult]:
    """
    Takes the model's raw output, returns one FieldResult per field.

    `extracted` maps field name -> {"value": str|None, "confidence": float, "note": str|None}.
    """
    results: dict[str, FieldResult] = {}

    for name, spec in FIELDS_BY_NAME.items():
        raw = extracted.get(name) or {}
        value = raw.get("value")
        conf = float(raw.get("confidence", 0.0) or 0.0)
        note = raw.get("note")

        normalized, msgs, severity = _check_field(spec, value)

        # A confident-looking model output still goes to review if the model
        # itself hedged, or if it left a note about the page.
        if severity == "ok" and conf < CONFIDENCE_FLOOR:
            severity = "warn"
            msgs.append(f"Model confidence {conf:.0%} — below the {CONFIDENCE_FLOOR:.0%} threshold")
        if note and severity == "ok":
            severity = "warn"

        results[name] = FieldResult(
            name=name,
            label=spec.label,
            value=value,
            normalized=normalized,
            confidence=conf,
            severity=severity,
            messages=msgs,
            note=note,
        )

    _cross_field_checks(results)
    return [results[spec.name] for spec in FIELDS_BY_NAME.values()]


def document_status(results: list[FieldResult]) -> str:
    if any(r.severity == "error" for r in results):
        return "needs_review"
    if any(r.severity == "warn" for r in results):
        return "needs_review"
    return "auto_accepted"
