# Universal Business Auditor

**Status: early prototype — document extraction and field validation implemented; business auditing not yet implemented.**

## Purpose

The Universal Business Auditor is a planned modular system that independently checks a business's existing records for costly errors, omissions, and inconsistencies. It is intended to work alongside the software a business already uses, rather than replace its accounting or job-management systems.

This repository documents the design, implementation, and evaluation of a modular auditing system. Development begins with **one focused auditing workflow** so that its accuracy, limitations, and reliability can be measured before additional modules are introduced. "Universal" describes the longer-term architecture, not the current capabilities.

## First planned auditing module: unbilled work

**Target workflow (hypothesis):** Small service contractors may record parts, labor, or additional work in work orders or technician notes but omit some of those charges from customer invoices.

The first audit module will aim to:

1. Read work orders, job notes, material records, and invoices.
2. Extract structured fields using the existing extraction pipeline.
3. Link records that refer to the same job.
4. Compare documented work with invoice line items.
5. **Flag potentially unbilled items**, showing the source records supporting each finding.
6. Let a human confirm or dismiss each finding before any correction.

This is a **planned module**, not a working feature. The proposed workflow has not yet been evaluated on real service records. Early versions will be **read-only** and will not post financial transactions or modify accounting systems.

## What is implemented today

The existing prototype is a **personal-injury intake-form extraction experiment**. It is being retained as the starting point for the auditor; it has **not** yet been converted to work orders or invoices.

- Takes sample PNG/JPEG images or PDF documents (PDF pages are rendered to images; up to four pages in the current code).
- Contains an Anthropic Claude vision-model extraction path returning 13 defined intake fields and model-reported confidence values.
- Validates extracted fields with deterministic rules for required values, formats, dates, and some cross-field conditions.
- Flags fields needing human review based on validation outcomes, low model-reported confidence, or extraction notes.
- Provides a command-line report and an offline fixture mode for reproducible demonstrations.
- Includes three synthetic sample forms and **18 passing validation tests** (verified against the uploaded repository snapshot).

**Current limitations:** The live Claude extraction path has not been verified end-to-end in this repository snapshot; model extraction accuracy has not been measured. The offline fixtures are hand-written examples, **not** outputs from the model. Confidence scores are model-reported and have not been calibrated. There is no database, web dashboard, accounting integration, job matching, or unbilled-work detection yet.

## Architecture and development direction

```text
CURRENT (implemented)
Document (image/PDF)
   -> Claude extraction OR offline fixture
   -> Intake-form field validation
   -> CLI review report

NEXT (planned)
Work order / invoice / job notes
   -> Document-specific extraction schemas
   -> Normalized job, material, labor, and invoice records
   -> Record linking and deterministic audit rules
   -> Evidence-backed, read-only findings for human review

LATER (planned expansion)
Reusable system connectors -> additional audit modules -> review dashboard
```

Document extraction is only one input to the future auditing engine. Reliable record linking, rule-based comparisons, explainable findings, and manageable integrations will be equally important.

## Development roadmap

| Phase | Deliverable | Status |
|---|---|---|
| Project foundation | Scope, GitHub project tracking, Wiki, LaTeX paper skeleton | In progress |
| Extraction pipeline | Verify live extraction; add work-order and invoice schemas | Planned |
| Unbilled Work Auditor | Link job records to invoices; flag potential missing charges | Planned |
| Testing and evaluation | Measure precision, recall, false positives, and runtime on labeled cases | Planned |
| MVP and documentation | Working end-to-end demonstration, reproducible results, research paper | Planned |

Possible later modules include duplicate-document detection, incomplete-paperwork checks, delayed-invoice checks, document reconciliation, and reminders. These are **not committed MVP features**.

## Run the current extraction prototype

Requires Python and the packages in `requirements.txt`.

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux; on Windows PowerShell use .venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m pytest -q
python run.py samples/03_messy.png --fixture
```

To attempt a live extraction, set the `ANTHROPIC_API_KEY` environment variable in your own environment and run:

```bash
python run.py samples/01_clean.png
```

The live path makes a paid external API call and needs to be independently tested. Do not submit sensitive or third-party documents without appropriate authorization and data-handling safeguards.

## Repository guide

| Path | Purpose |
|---|---|
| `app/schema.py` | Intake-form fields and types used by the current prototype |
| `app/extract.py` | Image/PDF ingestion, Claude extraction, offline fixture replay |
| `app/validate.py` | Intake-field validation and confidence-based review rules |
| `run.py` | Command-line demonstration |
| `make_samples.py` | Generates synthetic sample intake forms |
| `samples/` | Sample images, hand-written fixtures, and ground truth |
| `tests/` | Validation unit tests |
| `AGENTS.md` | Coding-agent instructions |
| `AGENT-LOG.md` | Agent contributions and verification history |

## Research and evaluation

**Initial research direction:** Can an auditor identify potentially unbilled materials or services by reconciling recorded work with customer invoices, while producing a manageable number of false alerts?

We will compare detected findings with labeled examples and evaluate, at minimum, precision, recall, false positives, and processing time. The evaluation plan and any claims of effectiveness will be updated only after real experiments. No real-world detection accuracy or recovered-charge results are claimed at present.

## Safety and operating boundaries

This prototype is not an accounting system and should not be used to make automatic financial decisions. Audit alerts represent **potential discrepancies**, not proven errors. Human reviewers must verify findings against source evidence. Real business data should be used only with permission and appropriate security controls.
