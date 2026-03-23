"""
AI Free Hand Generator — System 1
Uses Gemini to generate a full task+examples JSON from a student's natural language description.
"""

import json
import logging
import os
from be.settings import GEMINI_API_KEY
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)

# Set MOCK_AI_GENERATION=true in .env to bypass the Gemini API (for local dev/testing)
_MOCK_MODE = os.environ.get('MOCK_AI_GENERATION', '').lower() in ('true', '1', 'yes')

_MOCK_RESPONSE = {
    "task_name": "TEST – Násobilka 7",
    "form": "classic",
    "skill_names": [],
    "grade": 3,
    "examples": [
        {"example": "7 × 3",      "input_type": "INLINE", "answer": "21"},
        {"example": "7 × 6",      "input_type": "INLINE", "answer": "42"},
        {"example": "7 × ? = 49", "input_type": "INLINE", "answer": "7"},
        {"example": "? × 7 = 56", "input_type": "INLINE", "answer": "8"},
        {"example": "7 × 8",      "input_type": "INLINE", "answer": "56"},
        {"example": "7 × 4",      "input_type": "INLINE", "answer": "28"},
        {"example": "7 × 9",      "input_type": "INLINE", "answer": "63"},
        {"example": "7 × 7",      "input_type": "INLINE", "answer": "49"},
    ]
}

# ── Grade difficulty descriptions ─────────────────────────────────────────────
GRADE_DESCRIPTIONS = {
    1: "1. ročník: čísla do 20, základné sčítanie a odčítanie, porovnávanie čísel",
    2: "2. ročník: čísla do 100, sčítanie a odčítanie do 100, doplňovanie",
    3: "3. ročník: násobilka do 10×10, delenie, čísla do 1000, jednoduché prevody",
    4: "4. ročník: násobenie dvojcifernými číslami, delenie jednociferným, čísla do 10000",
    5: "5. ročník: násobenie a delenie viacmiestnych čísel, zaokrúhľovanie, poradie operácií, prevody času",
    6: "6. ročník: prvočísla, NSD, NSN, desatinné čísla, zlomky (sčítanie, odčítanie, násobenie, delenie)",
    7: "7. ročník: pomery, priama a nepriama úmernosť, pokročilé zlomky, jednoduché rovnice so slovnými úlohami",
    8: "8. ročník: lineárne rovnice, sústava rovníc, mocniny, odmocniny, pythagorova veta",
    9: "9. ročník: kvadratické rovnice, funkcie, goniometria, objem a povrch telies",
}


SYSTEM_PROMPT = """\
Si generátor matematických príkladov pre slovenských žiakov základnej školy.
Vygeneruj presne 10 príkladov podľa popisu žiaka.

Žiak: {grade}. ročník — {grade_description}

Vyber PRÁVE JEDEN typ (všetky príklady musia mať rovnaký input_type):
INLINE – základné operácie, násobilka, desatinné čísla, prevody. Príklad: {{"example": "7 × 8", "input_type": "INLINE", "answer": "56"}}
FRAC   – zlomky v LaTeX. VŽDY \\frac{{čit}}{{men}} v example aj answer. Príklad: {{"example": "\\\\frac{{1}}{{2}} + \\\\frac{{1}}{{4}}", "input_type": "FRAC", "answer": "\\\\frac{{3}}{{4}}"}}
WORD   – slovné úlohy po slovensky, odpoveď je číslo. input_type MUSÍ byť "WORD". Príklad: {{"example": "Vlak ide 80 km/h, za 3 hodiny ujde?", "input_type": "WORD", "answer": "240"}}
VAR    – rovnice s neznámou. Odpoveď: "x=číslo" alebo "x=číslo;y=číslo". Príklad: {{"example": "3x + 2 = 17", "input_type": "VAR", "answer": "x=5"}}

Dostupné zručnosti (vyber relevantné, alebo nechaj prázdne):
{skill_names_list}

Pravidlá: presne 10 príkladov · rovnaký input_type · obtiažnosť pre {grade}. ročník · jazyk slovenčina · výstup iba JSON.

{{
  "task_name": "krátky názov max 5 slov",
  "form": "classic alebo word-problem",
  "skill_names": [],
  "grade": {grade},
  "examples": [{{"example": "...", "input_type": "INLINE|FRAC|WORD|VAR", "answer": "..."}}]
}}

POPIS OD ŽIAKA: "{description}"
"""


def generate_free(description: str, grade: int, skill_names: list) -> dict:
    """
    Call Gemini to generate a full task+examples JSON from a student description.
    Returns the parsed dict matching the batch raw_json schema.
    Raises ValueError on schema validation failure.
    Raises RuntimeError on Gemini API error.
    """
    if _MOCK_MODE:
        logger.info("MOCK_AI_GENERATION=true — returning mock data (no Gemini call)")
        mock = dict(_MOCK_RESPONSE)
        mock["task_name"] = f"TEST – {description[:40]}"
        mock["grade"] = grade
        return mock

    grade_desc = GRADE_DESCRIPTIONS.get(grade, f"{grade}. ročník")
    skill_list_str = "\n".join(f"- {s}" for s in skill_names) if skill_names else "(žiadne)"

    prompt = SYSTEM_PROMPT.format(
        grade=grade,
        grade_description=grade_desc,
        skill_names_list=skill_list_str,
        description=description,
    )

    try:
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"},
        )
        response = model.generate_content(prompt)
        data = json.loads(response.text)
    except json.JSONDecodeError as e:
        logger.error("Gemini returned invalid JSON: %s", e)
        raise ValueError(f"Gemini returned invalid JSON: {e}")
    except Exception as e:
        logger.error("Gemini API error: %s", e)
        raise RuntimeError(f"Gemini API error: {e}")

    errors = _validate(data)
    if errors:
        raise ValueError(f"Generated JSON failed validation: {errors}")

    return data


def _validate(data: dict) -> list:
    errors = []
    if not isinstance(data, dict):
        return ["Root must be a JSON object"]
    if not data.get("task_name"):
        errors.append("Missing task_name")
    if data.get("form") not in ("classic", "word-problem"):
        errors.append(f"Invalid form: {data.get('form')}")
    examples = data.get("examples")
    if not isinstance(examples, list) or len(examples) == 0:
        errors.append("No examples in output")
        return errors
    valid_input_types = {"INLINE", "FRAC", "WORD", "VAR"}
    for i, ex in enumerate(examples):
        if not ex.get("example"):
            errors.append(f"Example {i}: empty example text")
        if ex.get("input_type") not in valid_input_types:
            errors.append(f"Example {i}: invalid input_type '{ex.get('input_type')}'")
        if not str(ex.get("answer", "")).strip():
            errors.append(f"Example {i}: empty answer")
    return errors
