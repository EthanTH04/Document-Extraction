# Document Extraction Pipeline

Reads scanned intake forms with an AI model (Claude), then checks every answer with validation rules. Anything wrong or uncertain goes to a person instead of straight into a records system.

**Research question:** How accurately does the AI read the forms, and how many of its mistakes do the validation rules and confidence scores catch?

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                              # validation tests, no API key needed
python run.py samples/03_messy.png --fixture     # demo with a hand-written stand-in answer
python run.py samples/01_clean.png               # real run, needs ANTHROPIC_API_KEY
```

## Files

| File | What it does |
|---|---|
| `app/schema.py` | The 13 fields to extract and their types |
| `app/extract.py` | Sends the form to Claude and gets the answers back |
| `app/validate.py` | Checks each answer against the rules |
| `run.py` | Runs one form through the pipeline and prints the results |
| `make_samples.py` | Draws the three sample forms |
| `samples/` | Sample forms, hand-written stand-in answers, and the correct answers |
| `tests/` | Tests for the validation rules |
| `AGENTS.md` | Rules for the coding agent |
| `AGENT-LOG.md` | What the AI did and what I checked |

## Status

Validation tested (18 tests pass). The reading step (Claude) is written but not yet run live. Accuracy not yet measured.
