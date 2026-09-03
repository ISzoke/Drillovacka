"""
Student Insight Generator
Uses Gemini to turn a student's recent practice attempts into a short,
teacher-facing performance summary (strengths, recurring mistakes, recommendations).

Mirrors api/generators/ai_free_generator.py. Falls back to a canned response when
MOCK_AI_GENERATION is set OR no GEMINI_API_KEY is configured, so it works on a
local stack without a key.
"""

import json
import logging
import os

from be.settings import GEMINI_API_KEY
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash"

_MOCK_MODE = (
    os.environ.get('MOCK_AI_GENERATION', '').lower() in ('true', '1', 'yes')
    or not GEMINI_API_KEY
)


SYSTEM_PROMPT = """\
Si asistent učiteľa matematiky na základnej škole. Dostaneš prehľad pokusov jedného
žiaka pri precvičovaní príkladov. Tvojou úlohou je pre učiteľa stručne zhrnúť, ako
na tom žiak je.

Údaje o žiakovi:
- ročník: {grade}
- celková úspešnosť: {overall_accuracy} %
- zvládnutie zručností (mastery v %): {skill_mastery}

Pokusy (example = zadanie, typed = čo žiak napísal, correct = správna odpoveď,
ok = či to bolo správne):
{attempts}

Vytvor JSON v tomto tvare (po slovensky, konkrétne, bez vaty):
{{
  "strengths": ["čo žiakovi ide dobre", "..."],
  "mistake_patterns": [
    {{"pattern": "konkrétny opakujúci sa typ chyby", "examples": ["2 + 3 → 6", "..."]}}
  ],
  "recommendations": ["konkrétne odporúčanie čo precvičovať", "..."]
}}

Pravidlá: 2-4 body v každej sekcii · v "examples" uvádzaj reálne pokusy žiaka vo
formáte "zadanie → odpoveď žiaka" · ak dát je málo, napíš to v recommendations ·
výstup iba JSON.
"""

_MOCK_RESPONSE = {
    "strengths": [
        "Jednoduché sčítanie do 10 zvláda spoľahlivo.",
        "Pri ľahších príkladoch odpovedá rýchlo a na prvý pokus.",
    ],
    "mistake_patterns": [
        {
            "pattern": "Systematická chyba o jednotku (počíta o 1 viac/menej).",
            "examples": ["8 − 6 → 3", "10 − 2 → 7", "9 − 4 → 6"],
        },
        {
            "pattern": "Odčítanie cez desiatku je menej isté než sčítanie.",
            "examples": ["36 − 15 → 22", "9 − 7 → 3"],
        },
    ],
    "recommendations": [
        "Precvičiť odčítanie do 20 s dôrazom na kontrolu výsledku spätným sčítaním.",
        "Krátke série 5 príkladov s okamžitou spätnou väzbou, aby si všimol chybu o jednotku.",
        "Zopakovať rozklad čísla pri prechode cez desiatku.",
    ],
    "meta": {"mock": True},
}


def _validate(data: dict) -> list:
    errors = []
    if not isinstance(data, dict):
        return ["Root must be a JSON object"]
    for key in ("strengths", "mistake_patterns", "recommendations"):
        if not isinstance(data.get(key), list) or not data[key]:
            errors.append(f"Missing or empty '{key}'")
    for i, mp in enumerate(data.get("mistake_patterns", []) or []):
        if not isinstance(mp, dict) or not mp.get("pattern"):
            errors.append(f"mistake_patterns[{i}]: missing 'pattern'")
    return errors


def generate_student_insight(payload: dict) -> dict:
    """
    payload = {
        "grade": int|None,
        "overall_accuracy": float,
        "skill_mastery": [{"skill_name": str, "mastery": float}, ...],
        "attempts": [{"example": str, "typed": str, "correct": str, "is_correct": bool, "skills": [str]}, ...],
    }
    Returns dict {strengths, mistake_patterns, recommendations, meta}.
    Raises ValueError on schema failure, RuntimeError on API error.
    """
    if _MOCK_MODE:
        logger.info("student_insight: mock mode (MOCK_AI_GENERATION or no GEMINI_API_KEY)")
        return dict(_MOCK_RESPONSE)

    skill_txt = ", ".join(
        f"{s['skill_name']} {round(s['mastery'])}%" for s in payload.get("skill_mastery", [])
    ) or "žiadne dáta"

    attempts_lines = []
    for a in payload.get("attempts", []):
        ok = "ok" if a.get("is_correct") else "zle"
        attempts_lines.append(
            f"- {a.get('example', '')} | typed={a.get('typed', '')} | "
            f"correct={a.get('correct', '')} | {ok}"
        )
    attempts_txt = "\n".join(attempts_lines) or "žiadne pokusy"

    prompt = SYSTEM_PROMPT.format(
        grade=payload.get("grade") or "neuvedený",
        overall_accuracy=round(payload.get("overall_accuracy", 0), 1),
        skill_mastery=skill_txt,
        attempts=attempts_txt,
    )

    try:
        model = genai.GenerativeModel(
            MODEL_NAME,
            generation_config={"response_mime_type": "application/json"},
        )
        response = model.generate_content(prompt)
        data = json.loads(response.text)
    except json.JSONDecodeError as e:
        logger.error("student_insight: Gemini returned invalid JSON: %s", e)
        raise ValueError(f"Gemini returned invalid JSON: {e}")
    except Exception as e:
        logger.error("student_insight: Gemini API error: %s", e)
        raise RuntimeError(f"Gemini API error: {e}")

    errors = _validate(data)
    if errors:
        raise ValueError(f"Generated JSON failed validation: {errors}")

    data.setdefault("meta", {})
    data["meta"]["model"] = MODEL_NAME
    return data
