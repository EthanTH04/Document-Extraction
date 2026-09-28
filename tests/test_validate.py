"""
Tests for the validation engine. No API key needed: validation is plain
business logic, so it can be tested exhaustively and cheaply.

Dates are built relative to today so the tests don't start failing as the
calendar moves (except test_clean_fixture_auto_accepts, which reads the
fixed dates in samples/ and will need updating once the 01_clean incident
date passes the statute of limitations in 2028).
"""
import json
from datetime import date, timedelta
from pathlib import Path

from app.validate import document_status, validate

SAMPLES = Path(__file__).parent.parent / "samples"
TODAY = date.today()


def us(d: date) -> str:
    return d.strftime("%m/%d/%Y")


def clean_fields() -> dict:
    """A fully valid extraction: every field present, confident, no notes."""
    def f(v):
        return {"value": v, "confidence": 0.97, "note": None}
    return {
        "full_name": f("Maria L. Gutierrez"),
        "date_of_birth": f(us(TODAY - timedelta(days=365 * 35))),
        "phone": f("(310) 555-0142"),
        "email": f("maria@example.com"),
        "street_address": f("1450 E Victoria St"),
        "city": f("Carson"),
        "state": f("CA"),
        "zip_code": f("90745"),
        "case_type": f("auto accident"),
        "date_of_incident": f(us(TODAY - timedelta(days=90))),
        "insurance_carrier": f("State Farm"),
        "policy_number": f("SF-2291"),
        "referral_source": f("Google"),
    }


def by_name(results):
    return {r.name: r for r in results}


# --- whole-document -------------------------------------------------------

def test_clean_form_auto_accepts():
    results = validate(clean_fields())
    assert document_status(results) == "auto_accepted"
    assert all(r.severity == "ok" for r in results)


def test_clean_fixture_auto_accepts():
    payload = json.loads((SAMPLES / "01_clean.png.fixture.json").read_text())
    assert document_status(validate(payload["fields"])) == "auto_accepted"


# --- single-field rules ---------------------------------------------------

def test_phone_is_normalized():
    fields = clean_fields()
    fields["phone"]["value"] = "1-310-555-0142"
    r = by_name(validate(fields))["phone"]
    assert r.severity == "ok"
    assert r.normalized == "(310) 555-0142"


def test_date_is_normalized_to_iso():
    fields = clean_fields()
    fields["date_of_birth"]["value"] = "April 22, 1988"
    r = by_name(validate(fields))["date_of_birth"]
    assert r.severity == "ok"
    assert r.normalized == "1988-04-22"


def test_short_phone_is_error():
    fields = clean_fields()
    fields["phone"]["value"] = "555-0117"
    assert by_name(validate(fields))["phone"].severity == "error"


def test_unparseable_date_is_error():
    fields = clean_fields()
    fields["date_of_birth"]["value"] = "sometime in spring"
    r = by_name(validate(fields))["date_of_birth"]
    assert r.severity == "error"
    assert "Could not read" in r.messages[0]


def test_future_date_is_error():
    fields = clean_fields()
    fields["date_of_incident"]["value"] = us(TODAY + timedelta(days=30))
    r = by_name(validate(fields))["date_of_incident"]
    assert r.severity == "error"
    assert "future" in r.messages[0]


def test_missing_required_field_is_error():
    fields = clean_fields()
    fields["city"]["value"] = None
    r = by_name(validate(fields))["city"]
    assert r.severity == "error"
    assert "required" in r.messages[0]


def test_missing_optional_field_is_ok():
    fields = clean_fields()
    fields["insurance_carrier"]["value"] = None
    results = validate(fields)
    assert by_name(results)["insurance_carrier"].severity == "ok"
    assert document_status(results) == "auto_accepted"


def test_unrecognized_state_is_error():
    fields = clean_fields()
    fields["state"]["value"] = "Calif"
    assert by_name(validate(fields))["state"].severity == "error"


# --- confidence gating ----------------------------------------------------

def test_low_confidence_flags_valid_value():
    fields = clean_fields()
    fields["city"]["confidence"] = 0.60
    r = by_name(validate(fields))["city"]
    assert r.severity == "warn"
    assert "below" in r.messages[0]


def test_model_note_flags_valid_value():
    fields = clean_fields()
    fields["street_address"]["note"] = "Second line crossed out"
    assert by_name(validate(fields))["street_address"].severity == "warn"


def test_fuzzy_case_type_match_warns():
    fields = clean_fields()
    fields["case_type"]["value"] = "Auto accident - rear ended"
    r = by_name(validate(fields))["case_type"]
    assert r.severity == "warn"
    assert r.normalized == "auto accident"


# --- cross-field rules ----------------------------------------------------

def test_minor_is_flagged():
    fields = clean_fields()
    fields["date_of_birth"]["value"] = us(TODAY - timedelta(days=365 * 15))
    r = by_name(validate(fields))["date_of_birth"]
    assert r.severity == "warn"
    assert "minor" in r.messages[0]


def test_incident_before_birth_is_error():
    fields = clean_fields()
    fields["date_of_birth"]["value"] = us(TODAY - timedelta(days=365 * 30))
    fields["date_of_incident"]["value"] = us(TODAY - timedelta(days=365 * 31))
    r = by_name(validate(fields))["date_of_incident"]
    assert r.severity == "error"
    assert any("predates" in m for m in r.messages)


def test_statute_expired_is_error():
    fields = clean_fields()
    fields["date_of_incident"]["value"] = us(TODAY - timedelta(days=365 * 3))
    r = by_name(validate(fields))["date_of_incident"]
    assert r.severity == "error"
    assert any("statute" in m for m in r.messages)


def test_statute_approaching_warns():
    fields = clean_fields()
    fields["date_of_incident"]["value"] = us(TODAY - timedelta(days=700))
    r = by_name(validate(fields))["date_of_incident"]
    assert r.severity == "warn"
    assert any("expires in" in m for m in r.messages)


def test_statute_well_within_is_ok():
    fields = clean_fields()
    fields["date_of_incident"]["value"] = us(TODAY - timedelta(days=200))
    r = by_name(validate(fields))["date_of_incident"]
    assert r.severity == "ok"
    assert r.messages == []
