"""
Field definitions for a client intake form.

This is the only file that changes per client. The pipeline, validation
engine, review UI and storage are all schema-agnostic — point them at a
different FieldSpec list and they process a different document type.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# What the model is asked to return
# --------------------------------------------------------------------------

class ExtractedField(BaseModel):
    """One field pulled off the page, with the model's own read on it."""
    value: Optional[str] = Field(
        description="Exactly as written on the form. null if not present."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="0.0-1.0. Low when handwriting is unclear or the field is ambiguous.",
    )
    note: Optional[str] = Field(
        default=None,
        description="Only when something is odd: crossed out, illegible, two values, etc.",
    )


class IntakeForm(BaseModel):
    """A personal-injury client intake form."""
    full_name: ExtractedField
    date_of_birth: ExtractedField
    phone: ExtractedField
    email: ExtractedField
    street_address: ExtractedField
    city: ExtractedField
    state: ExtractedField
    zip_code: ExtractedField
    case_type: ExtractedField
    date_of_incident: ExtractedField
    insurance_carrier: ExtractedField
    policy_number: ExtractedField
    referral_source: ExtractedField


# --------------------------------------------------------------------------
# What the rest of the system needs to know about each field
# --------------------------------------------------------------------------

FieldKind = Literal["text", "date", "phone", "email", "zip", "state", "choice"]


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: FieldKind = "text"
    required: bool = False
    choices: tuple[str, ...] = field(default_factory=tuple)


INTAKE_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("full_name", "Client name", required=True),
    FieldSpec("date_of_birth", "Date of birth", kind="date", required=True),
    FieldSpec("phone", "Phone", kind="phone", required=True),
    FieldSpec("email", "Email", kind="email"),
    FieldSpec("street_address", "Street address", required=True),
    FieldSpec("city", "City", required=True),
    FieldSpec("state", "State", kind="state", required=True),
    FieldSpec("zip_code", "ZIP", kind="zip", required=True),
    FieldSpec(
        "case_type", "Case type", kind="choice", required=True,
        choices=("auto accident", "slip and fall", "medical malpractice",
                 "workers compensation", "product liability", "other"),
    ),
    FieldSpec("date_of_incident", "Date of incident", kind="date", required=True),
    FieldSpec("insurance_carrier", "Insurance carrier"),
    FieldSpec("policy_number", "Policy number"),
    FieldSpec("referral_source", "Referral source"),
)

FIELDS_BY_NAME = {f.name: f for f in INTAKE_FIELDS}


def prompt_field_list() -> str:
    """Field descriptions injected into the extraction prompt."""
    lines = []
    for f in INTAKE_FIELDS:
        bits = [f"- {f.name}: {f.label}"]
        if f.kind == "date":
            bits.append("(a date; return it exactly as written)")
        elif f.kind == "phone":
            bits.append("(a phone number)")
        elif f.kind == "choice":
            bits.append(f"(one of: {', '.join(f.choices)})")
        lines.append(" ".join(bits))
    return "\n".join(lines)
