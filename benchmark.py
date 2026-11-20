"""Score extraction against the labeled synthetic intake forms."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from datetime import date
from pathlib import Path

from app.extract import MODEL, extract, extract_offline
from app.schema import FIELDS_BY_NAME, IntakeForm
from app.validate import validate

SAMPLES = Path(__file__).resolve().parent / "samples"


def evaluate(
    samples: Path,
    labels: dict[str, dict[str, str | None]],
    extractor: Callable[[Path], tuple[dict, dict]],
) -> dict:
    """Count exact matches and list review flags for each successful extraction."""
    if not labels or any(expected.keys() != FIELDS_BY_NAME.keys() for expected in labels.values()):
        raise ValueError("Ground truth must label every intake field for each sample.")

    documents = {}
    matches = fields_evaluated = documents_failed = 0
    for filename, expected in labels.items():
        try:
            path = samples / filename
            if not path.is_file():
                raise FileNotFoundError(path)
            fields, _ = extractor(path)
            fields = IntakeForm.model_validate(fields).model_dump()
        except Exception as error:
            documents[filename] = {"error": type(error).__name__}
            documents_failed += 1
            continue

        mismatches = {
            name: {"expected": value, "actual": fields[name]["value"]}
            for name, value in expected.items()
            if fields[name]["value"] != value
        }
        document_matches = len(expected) - len(mismatches)
        documents[filename] = {
            "exact_matches": document_matches,
            "mismatches": mismatches,
            "review_fields": [result.name for result in validate(fields) if result.needs_review],
        }
        matches += document_matches
        fields_evaluated += len(expected)

    return {
        "documents": documents,
        "documents_failed": documents_failed,
        "fields_expected": len(labels) * len(FIELDS_BY_NAME),
        "fields_evaluated": fields_evaluated,
        "exact_matches": matches,
        "exact_match_rate_evaluated_fields": matches / fields_evaluated if fields_evaluated else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare the synthetic intake forms with their ground-truth labels."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="call the Claude API instead of replaying hand-written fixtures (may incur charges)",
    )
    args = parser.parse_args()
    if args.live and not os.environ.get("ANTHROPIC_API_KEY"):
        parser.error("--live requires ANTHROPIC_API_KEY in the environment")

    labels = json.loads((SAMPLES / "ground_truth.json").read_text(encoding="utf-8"))
    report = {
        "mode": "live" if args.live else "fixture_replay",
        "model": MODEL if args.live else None,
        "validation_date": date.today().isoformat(),
        **evaluate(SAMPLES, labels, extract if args.live else extract_offline),
    }
    print(json.dumps(report, indent=2))
    return int(report["documents_failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
