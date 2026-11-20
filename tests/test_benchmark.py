import json

from app.extract import extract_offline
from benchmark import SAMPLES, evaluate


def test_evaluate_compares_verbatim_fields_and_reports_review_flags():
    labels = json.loads((SAMPLES / "ground_truth.json").read_text(encoding="utf-8"))
    name = "03_messy.png"

    def extract_with_mismatches(path):
        fields, meta = extract_offline(path)
        fields["case_type"]["value"] = "dog bite"
        fields["policy_number"]["value"] = "invented"
        return fields, meta

    report = evaluate(SAMPLES, {name: labels[name]}, extract_with_mismatches)
    document = report["documents"][name]
    assert report["fields_expected"] == 13
    assert report["fields_evaluated"] == 13
    assert report["exact_matches"] == 11
    assert document["mismatches"] == {
        "case_type": {"expected": "Dog bite", "actual": "dog bite"},
        "policy_number": {"expected": None, "actual": "invented"},
    }
    assert "phone" in document["review_fields"]


def test_evaluate_reports_failed_extractions_and_score_coverage():
    labels = json.loads((SAMPLES / "ground_truth.json").read_text(encoding="utf-8"))
    name = "01_clean.png"

    def extract_other_samples(path):
        if path.name == name:
            raise RuntimeError("extraction failed")
        return extract_offline(path)

    report = evaluate(SAMPLES, labels, extract_other_samples)
    assert report["documents"][name] == {"error": "RuntimeError"}
    assert report["documents_failed"] == 1
    assert report["fields_expected"] == 39
    assert report["fields_evaluated"] == 26
    assert report["exact_matches"] == 26
    assert report["exact_match_rate_evaluated_fields"] == 1.0
