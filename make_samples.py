"""
Generate the three sample intake forms in samples/ and their ground truth.

    python make_samples.py

Each form exercises a different path through validation:
  01_clean.png  printed, every field valid          -> should auto-accept
  02_stale.png  incident in 2023                    -> past the statute of limitations
  03_messy.png  skewed, noisy, blanks, bad values   -> several fields flagged

Seeded, so the images come out identical every run.
ground_truth.json records what is actually written on each form: the start
of the labeled set that extraction accuracy is measured against.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent / "samples"
SEED = 492

LABELS = [
    ("full_name", "Client name"),
    ("date_of_birth", "Date of birth"),
    ("phone", "Phone"),
    ("email", "Email"),
    ("street_address", "Street address"),
    ("city", "City"),
    ("state", "State"),
    ("zip_code", "ZIP"),
    ("case_type", "Case type"),
    ("date_of_incident", "Date of incident"),
    ("insurance_carrier", "Insurance carrier"),
    ("policy_number", "Policy number"),
    ("referral_source", "How did you hear about us?"),
]

# What is written on each form. None = left blank.
FORMS = {
    "01_clean.png": {
        "full_name": "Maria L. Gutierrez",
        "date_of_birth": "04/22/1988",
        "phone": "(310) 555-0142",
        "email": "maria.gutierrez@gmail.com",
        "street_address": "1450 E Victoria St",
        "city": "Carson",
        "state": "CA",
        "zip_code": "90745",
        "case_type": "Auto accident",
        "date_of_incident": "03/15/2026",
        "insurance_carrier": "State Farm",
        "policy_number": "SF-2291-884-03",
        "referral_source": "Google search",
    },
    "02_stale.png": {
        "full_name": "James T. Whitfield",
        "date_of_birth": "11/03/1974",
        "phone": "562-555-0199",
        "email": "jwhitfield74@yahoo.com",
        "street_address": "3321 Atlantic Ave",
        "city": "Long Beach",
        "state": "CA",
        "zip_code": "90807",
        "case_type": "Slip and fall",
        "date_of_incident": "06/10/2023",
        "insurance_carrier": "Allstate",
        "policy_number": "AL-7730-1156",
        "referral_source": "Former client",
    },
    "03_messy.png": {
        "full_name": "D. Okonkwo",
        "date_of_birth": "07/09/2011",
        "phone": "555-0117",
        "email": "okonkwo.family@outlok.com",
        "street_address": "6620 E Pacific Coast Hwy",
        "city": "Long Beach",
        "state": "Calif",
        "zip_code": "90803",
        "case_type": "Dog bite",
        "date_of_incident": "01/22/2027",
        "insurance_carrier": None,
        "policy_number": None,
        "referral_source": "friend",
    },
}


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)   # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def render(values: dict, rng: random.Random, messy: bool) -> Image.Image:
    img = Image.new("RGB", (1100, 1300), "white")
    d = ImageDraw.Draw(img)
    d.text((60, 50), "Client Intake Form", fill="black", font=_font(40))
    d.text((60, 105), "Please print clearly. All information is confidential.",
           fill="gray", font=_font(18))

    y = 170
    for key, label in LABELS:
        d.text((60, y), label, fill="black", font=_font(20))
        d.line((380, y + 28, 1040, y + 28), fill="gray", width=1)
        val = values.get(key)
        if val:
            dx = rng.randint(-6, 6) if messy else 0
            d.text((390 + dx, y), val, fill=(20, 20, 90), font=_font(24))
        y += 80

    if messy:
        # Speckle noise, a slight blur and a skew: roughly a bad office scan.
        px = img.load()
        for _ in range(9000):
            x, yy = rng.randrange(img.width), rng.randrange(img.height)
            g = rng.randint(90, 200)
            px[x, yy] = (g, g, g)
        img = img.filter(ImageFilter.GaussianBlur(0.8))
        img = img.rotate(rng.uniform(-3.5, -2.0), expand=True, fillcolor="white")
    return img


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rng = random.Random(SEED)
    for name, values in FORMS.items():
        render(values, rng, messy=name.startswith("03")).save(OUT / name)
        print(f"wrote samples/{name}")
    (OUT / "ground_truth.json").write_text(json.dumps(FORMS, indent=2) + "\n")
    print("wrote samples/ground_truth.json")


if __name__ == "__main__":
    main()
