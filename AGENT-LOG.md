# Agent log

What an AI agent produced, and what I checked before accepting it.

| Date | Issue | What the agent did | What I checked |
|---|---|---|---|
| 2026-09-28 | — | Claude generated the core pipeline (app/schema.py, app/extract.py, app/validate.py, run.py) in an earlier session, then rebuilt the tests, sample generator, sample forms, fixtures and config in this session | 18/18 tests pass locally; fixture demo on 03_messy.png flags 6 of 13 fields, matching the design document |
