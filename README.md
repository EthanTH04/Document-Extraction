# Document Extraction Pipeline

Reads scanned client intake forms with a vision-language model and returns structured fields, then applies deterministic validation rules and a confidence gate so that uncertain or implausible values go to a human reviewer instead of straight into a records system.

**Research question:** How accurately does a vision model extract fields from scanned intake forms, and how many of its errors do rule-based validation and model confidence catch?

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                              # validation tests, no API key needed
python run.py samples/03_messy.png --fixture     # demo using a hand-written fixture
python run.py samples/01_clean.png               # real extraction, needs ANTHROPIC_API_KEY
```

## Status

Pipeline scaffold and validation engine in place; 18 validation tests pass. Not yet run against a live model. Extraction accuracy not yet measured. The fixtures in `samples/` are hand-written test data, not model output.
