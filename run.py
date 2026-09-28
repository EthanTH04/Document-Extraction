"""
Run one document through the pipeline and print what a reviewer would see.

    python run.py samples/03_messy.png --fixture
    python run.py samples/01_clean.png            # needs ANTHROPIC_API_KEY

--fixture replays a hand-written test fixture instead of calling the model.
Useful for working on the validation rules without spending API calls.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.extract import extract, extract_offline
from app.validate import document_status, validate

MARK = {"ok": "  ", "warn": " !", "error": " X"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--fixture", action="store_true",
                    help="use the stored test fixture instead of the model")
    args = ap.parse_args()

    if not args.path.exists():
        print(f"No such file: {args.path}", file=sys.stderr)
        return 1

    try:
        fields, meta = (extract_offline if args.fixture else extract)(args.path)
    except Exception as e:
        print(f"Extraction failed: {e}", file=sys.stderr)
        return 1

    results = validate(fields)
    status = document_status(results)

    print()
    print(f"  {args.path.name}")
    if meta.get("fixture"):
        print("  fixture replay — not a real extraction")
    else:
        print(f"  {meta['model']} · {meta['pages']} page(s) · "
              f"{meta['input_tokens']}+{meta['output_tokens']} tokens · "
              f"~${meta['cost_estimate']:.4f}")
    print()

    width = max(len(r.label) for r in results)
    for r in results:
        shown = r.normalized if r.normalized is not None else "—"
        print(f"{MARK[r.severity]} {r.label:<{width}}  {shown}")
        for m in r.messages:
            print(f"{'':>{width + 6}}{m}")
        if r.note:
            print(f"{'':>{width + 6}}model note: {r.note}")

    flagged = [r for r in results if r.needs_review]
    print()
    print(f"  {len(results) - len(flagged)}/{len(results)} fields clean · "
          f"{len(flagged)} need review · {status}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
