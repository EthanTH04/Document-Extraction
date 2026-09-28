"""
Document in, structured fields out.

Handles the two ingestion paths — a native PDF with a text layer, and a
scan or photo that has to be read visually — then asks a vision model for
the fields defined in schema.py.
"""
from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Optional

from .schema import IntakeForm, prompt_field_list

MODEL = os.environ.get("IDP_MODEL", "claude-sonnet-4-5-20250929")
MAX_PAGES = 4

SYSTEM_PROMPT = """You read client intake forms for a personal injury law firm \
and return the fields as JSON.

Rules:
- Return the value exactly as written on the form. Do not reformat dates, \
phone numbers, or names.
- If a field is blank or absent, return null for its value.
- confidence is your own honest read: 1.0 for clear printed text, lower for \
unclear handwriting, smudged scans, or fields where two readings are possible.
- Use note only when something needs a human's attention: a crossed-out \
value, two conflicting entries, or text you could not make out.
- Never guess at a value to fill a field. A null with a note is better than \
an invented answer.

Return only the JSON object. No preamble, no markdown fences."""


def _user_prompt() -> str:
    return (
        "Extract these fields from the intake form:\n\n"
        f"{prompt_field_list()}\n\n"
        "Return a JSON object where every key above maps to "
        '{"value": string or null, "confidence": number 0-1, '
        '"note": string or null}.'
    )


# --------------------------------------------------------------------------
# Turning a file into something the model can see
# --------------------------------------------------------------------------

def pdf_has_text_layer(data: bytes) -> bool:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        text = "".join((p.extract_text() or "") for p in reader.pages[:2])
        return len(text.strip()) > 100
    except Exception:
        return False


def pdf_to_images(data: bytes, max_pages: int = MAX_PAGES) -> list[bytes]:
    """Rasterize PDF pages to PNG bytes at a resolution the model can read."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(io.BytesIO(data))
    out: list[bytes] = []
    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        # scale 2.0 ~= 144 DPI, enough for handwriting without huge payloads
        pil = page.render(scale=2.0).to_pil()
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        out.append(buf.getvalue())
    return out


def load_as_images(path: Path) -> list[bytes]:
    data = path.read_bytes()
    if path.suffix.lower() == ".pdf":
        return pdf_to_images(data)
    return [data]


def _media_type(img: bytes) -> str:
    if img[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if img[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    return "image/png"


# --------------------------------------------------------------------------
# The model call
# --------------------------------------------------------------------------

def extract(path: Path) -> tuple[dict, dict]:
    """
    Returns (fields, meta).

    fields maps field name -> {"value", "confidence", "note"}.
    meta carries what happened: page count, model used, token usage.
    """
    images = load_as_images(path)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Set it, or run with --offline to "
            "use the stored sample extractions."
        )

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    content: list[dict] = []
    for img in images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": _media_type(img),
                "data": base64.standard_b64encode(img).decode(),
            },
        })
    content.append({"type": "text", "text": _user_prompt()})

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    fields = _parse_json(text)

    # Validate the shape against the Pydantic model so a malformed response
    # fails here rather than three layers down.
    IntakeForm.model_validate(fields)

    meta = {
        "pages": len(images),
        "model": MODEL,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cost_estimate": _estimate_cost(response.usage.input_tokens,
                                        response.usage.output_tokens),
    }
    return fields, meta


def _parse_json(text: str) -> dict:
    """Models occasionally wrap JSON in fences despite being told not to."""
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def _estimate_cost(in_tok: int, out_tok: int) -> float:
    """Rough per-document cost. Verify current rates before quoting a client."""
    return round(in_tok / 1_000_000 * 3.0 + out_tok / 1_000_000 * 15.0, 4)


# --------------------------------------------------------------------------
# Offline path, for demoing without network access
# --------------------------------------------------------------------------

def extract_offline(path: Path) -> tuple[dict, dict]:
    """
    Loads a hand-written test fixture from <name>.fixture.json.

    These are NOT captured model responses. They are fixtures written by hand
    to exercise the validation engine deterministically — the same role unit
    test fixtures play anywhere else. They let the review UI and the rules be
    demonstrated and regression-tested without burning API calls or requiring
    a network.

    Anything presented as real extraction accuracy must come from extract(),
    not from here.
    """
    stored = path.with_suffix(path.suffix + ".fixture.json")
    if not stored.exists():
        raise RuntimeError(
            f"No fixture at {stored.name}. Run with an API key to extract for real."
        )
    payload = json.loads(stored.read_text())
    meta = payload.get("meta", {})
    meta["fixture"] = True
    return payload["fields"], meta
