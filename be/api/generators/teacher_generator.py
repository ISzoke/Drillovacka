"""
Teacher Task Generator
Generates task+examples JSON from teacher's type/count/description input.
"""

import json
import logging
import os
from be.settings import GEMINI_API_KEY
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)

_MOCK_MODE = os.environ.get('MOCK_AI_GENERATION', '').lower() in ('true', '1', 'yes')

TYPE_TO_INPUT = {
    'arithmetic': 'INLINE',
    'fractions':  'FRAC',
    'word':       'WORD',
    'algebra':    'VAR',
}

TYPE_LABELS = {
    'arithmetic': 'aritmetické príklady (sčítanie, odčítanie, násobenie, delenie)',
    'fractions':  'zlomky',
    'word':       'slovné úlohy',
    'algebra':    'algebra a rovnice s neznámou',
}

SYSTEM_PROMPT = """\
Si generátor matematických príkladov pre slovenských žiakov základnej školy.
Vygeneruj presne {count} príkladov podľa požiadavky učiteľa.

Typ príkladov: {type_label}
Povinný input_type pre každý príklad: {input_type}

Pravidlá formátu podľa input_type:
- INLINE: čísla a operátory. Príklad: {{"example": "7 × 8", "input_type": "INLINE", "answer": "56"}}
- FRAC: zlomky v LaTeX notácii. Príklad: {{"example": "\\\\frac{{1}}{{2}} + \\\\frac{{1}}{{4}}", "input_type": "FRAC", "answer": "\\\\frac{{3}}{{4}}"}}
- WORD: slovenská slovná úloha, číselná odpoveď. Príklad: {{"example": "Vlak ide 80 km/h po dobu 3 hodín. Akú vzdialenosť ujde?", "input_type": "WORD", "answer": "240"}}
- VAR: rovnica s neznámou, odpoveď "x=číslo". Príklad: {{"example": "3x + 2 = 17", "input_type": "VAR", "answer": "x=5"}}

Požiadavka učiteľa: "{description}"

Výstup MUSÍ byť iba JSON bez markdown:
{{
  "task_name": "stručný názov sady (max 5 slov)",
  "form": "{form}",
  "examples": [
    {{"example": "...", "input_type": "{input_type}", "answer": "..."}}
  ]
}}

Vygeneruj presne {count} príkladov. Každý príklad musí mať vyplnené "example", "input_type" a "answer".
"""



BATCH_SIZE = 10


def _generate_batch(task_type: str, count: int, description: str) -> list:
    """Single Gemini call for up to BATCH_SIZE examples. Returns list of examples."""
    input_type = TYPE_TO_INPUT.get(task_type, 'INLINE')
    type_label = TYPE_LABELS.get(task_type, 'matematické príklady')
    form = 'word-problem' if task_type == 'word' else 'classic'

    prompt = SYSTEM_PROMPT.format(
        count=count,
        type_label=type_label,
        input_type=input_type,
        form=form,
        description=description,
    )

    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config={
            'response_mime_type': 'application/json',
            'max_output_tokens': 8192,
        },
    )
    response = model.generate_content(prompt)
    data = json.loads(response.text)
    return data.get('task_name', ''), data.get('form', form), data.get('examples', [])


def generate_teacher_task(task_type: str, count: int, description: str) -> dict:
    if _MOCK_MODE:
        input_type = TYPE_TO_INPUT.get(task_type, 'INLINE')
        return {
            'task_name': f'Testovacia sada – {description[:30]}',
            'form': 'word-problem' if task_type == 'word' else 'classic',
            'examples': [
                {'example': f'Príklad {i + 1}', 'input_type': input_type, 'answer': str(i + 1)}
                for i in range(count)
            ],
        }

    all_examples = []
    task_name = None
    form = 'word-problem' if task_type == 'word' else 'classic'

    remaining = count
    while remaining > 0:
        batch = min(remaining, BATCH_SIZE)
        try:
            name, f, examples = _generate_batch(task_type, batch, description)
        except json.JSONDecodeError as e:
            logger.error('Gemini returned invalid JSON: %s', e)
            raise ValueError(f'Gemini returned invalid JSON: {e}')
        except Exception as e:
            logger.error('Gemini API error: %s', e)
            raise RuntimeError(f'Gemini API error: {e}')

        if not examples:
            raise ValueError('No examples in Gemini response')

        if task_name is None:
            task_name = name
            form = f
        all_examples.extend(examples)
        remaining -= batch

    return {
        'task_name': task_name or description[:40],
        'form': form,
        'examples': all_examples,
    }


SYSTEM_PROMPT_MORE = """\
Si generátor matematických príkladov pre slovenských žiakov základnej školy.
Sada už obsahuje tieto príklady (zachovaj rovnaký štýl, formát a input_type; NEOPAKUJ ich):
{reference_block}

Vygeneruj presne {count} NOVÝCH príkladov v rovnakom štýle ako vyššie.
Doplňujúca požiadavka učiteľa: "{description}"

Výstup MUSÍ byť iba JSON bez markdown:
{{"examples": [{{"example": "...", "input_type": "...", "answer": "..."}}]}}
Vygeneruj presne {count} príkladov. Každý príklad musí mať vyplnené "example", "input_type" a "answer".
"""


def _generate_more_batch(reference_examples: list, count: int, description: str) -> list:
    """Single Gemini call for up to BATCH_SIZE new examples, using reference_examples as a style sample."""
    reference_block = "\n".join(
        json.dumps({'example': ex['example'], 'input_type': ex['input_type'], 'answer': ex['answer']}, ensure_ascii=False)
        for ex in reference_examples
    )
    prompt = SYSTEM_PROMPT_MORE.format(reference_block=reference_block, count=count, description=description)

    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config={
            'response_mime_type': 'application/json',
            'max_output_tokens': 8192,
        },
    )
    response = model.generate_content(prompt)
    return json.loads(response.text).get('examples', [])


def generate_teacher_task_more(reference_examples: list, count: int, description: str, fallback_type: str = 'arithmetic') -> dict:
    """Generate `count` additional examples matching the style of reference_examples (last examples in the sada)."""
    if _MOCK_MODE:
        input_type = reference_examples[0]['input_type'] if reference_examples else TYPE_TO_INPUT.get(fallback_type, 'INLINE')
        return {
            'examples': [
                {'example': f'Nový príklad {i + 1}', 'input_type': input_type, 'answer': str(i + 1)}
                for i in range(count)
            ],
        }

    if not reference_examples:
        # Empty sada — no style to imitate yet, degrade to the plain generator.
        return {'examples': generate_teacher_task(fallback_type, count, description)['examples']}

    all_examples = []
    remaining = count
    while remaining > 0:
        batch = min(remaining, BATCH_SIZE)
        try:
            examples = _generate_more_batch(reference_examples, batch, description)
        except json.JSONDecodeError as e:
            logger.error('Gemini returned invalid JSON: %s', e)
            raise ValueError(f'Gemini returned invalid JSON: {e}')
        except Exception as e:
            logger.error('Gemini API error: %s', e)
            raise RuntimeError(f'Gemini API error: {e}')

        if not examples:
            raise ValueError('No examples in Gemini response')

        all_examples.extend(examples)
        remaining -= batch

    return {'examples': all_examples}


def generate_teacher_task_mix(segments: list, description: str) -> dict:
    """Calls generate_teacher_task per segment and combines results."""
    all_examples = []
    task_name = None

    for seg in segments:
        t = seg.get('type', 'arithmetic')
        c = min(max(int(seg.get('count', 5)), 1), 30)
        result = generate_teacher_task(t, c, description)
        if task_name is None:
            task_name = result.get('task_name', '')
        all_examples.extend(result.get('examples', []))

    return {
        'task_name': task_name or f'Písomka – {description[:40]}',
        'form': 'classic',
        'examples': all_examples,
    }
