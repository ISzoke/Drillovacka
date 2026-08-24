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

LANGUAGE_NAMES = {
    'sk': 'Slovak (slovenčina)',
    'cs': 'Czech (čeština)',
    'en': 'English',
}

WORD_EXAMPLE_BY_LANGUAGE = {
    'sk': '{"example": "Vlak ide 80 km/h po dobu 3 hodín. Akú vzdialenosť ujde?", "input_type": "WORD", "answer": "240"}',
    'cs': '{"example": "Vlak jede 80 km/h po dobu 3 hodin. Jakou vzdálenost ujede?", "input_type": "WORD", "answer": "240"}',
    'en': '{"example": "A train travels at 80 km/h for 3 hours. How far does it go?", "input_type": "WORD", "answer": "240"}',
}

FALLBACK_TASK_NAME = {'sk': 'Vygenerovaná úloha', 'cs': 'Vygenerovaná úloha', 'en': 'Generated task'}
FALLBACK_WORKSHEET_PREFIX = {'sk': 'Písomka', 'cs': 'Písemka', 'en': 'Worksheet'}


def _language_name(language: str) -> str:
    return LANGUAGE_NAMES.get(language, LANGUAGE_NAMES['sk'])


SYSTEM_PROMPT = """\
Si generátor matematických príkladov pre žiakov základnej školy.
IMPORTANT: Write every piece of user-facing text in the output (task_name, and the "example" text \
when input_type is WORD) in {language_name}. Keep numbers, mathematical operators and LaTeX syntax unchanged \
regardless of language.
Vygeneruj presne {count} príkladov podľa požiadavky učiteľa.

Typ príkladov: {type_label}
Povinný input_type pre každý príklad: {input_type}

Pravidlá formátu podľa input_type:
- INLINE: čísla a operátory. Príklad: {{"example": "7 × 8", "input_type": "INLINE", "answer": "56"}}
- FRAC: zlomky v LaTeX notácii. Príklad: {{"example": "\\\\frac{{1}}{{2}} + \\\\frac{{1}}{{4}}", "input_type": "FRAC", "answer": "\\\\frac{{3}}{{4}}"}}
- WORD: slovná úloha v jazyku {language_name}, číselná odpoveď. Príklad: {word_example}
- VAR: rovnica s neznámou, odpoveď "x=číslo". Príklad: {{"example": "3x + 2 = 17", "input_type": "VAR", "answer": "x=5"}}

Požiadavka učiteľa: "{description}"

Výstup MUSÍ byť iba JSON bez markdown:
{{
  "task_name": "stručný názov sady v jazyku {language_name} (max 5 slov)",
  "form": "{form}",
  "examples": [
    {{"example": "...", "input_type": "{input_type}", "answer": "..."}}
  ]
}}

Vygeneruj presne {count} príkladov. Každý príklad musí mať vyplnené "example", "input_type" a "answer".
"""



BATCH_SIZE = 10


def _generate_batch(task_type: str, count: int, description: str, language: str = 'sk') -> list:
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
        language_name=_language_name(language),
        word_example=WORD_EXAMPLE_BY_LANGUAGE.get(language, WORD_EXAMPLE_BY_LANGUAGE['sk']),
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


def generate_teacher_task(task_type: str, count: int, description: str, language: str = 'sk') -> dict:
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
            name, f, examples = _generate_batch(task_type, batch, description, language)
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
        'task_name': task_name or FALLBACK_TASK_NAME.get(language, FALLBACK_TASK_NAME['sk']),
        'form': form,
        'examples': all_examples,
    }


SYSTEM_PROMPT_MORE = """\
Si generátor matematických príkladov pre žiakov základnej školy.
IMPORTANT: Write every piece of user-facing text in the output (the "example" text, when it is a word \
problem) in {language_name}. Keep numbers, mathematical operators and LaTeX syntax unchanged regardless of language.
Sada už obsahuje tieto príklady (zachovaj rovnaký štýl, formát a input_type; NEOPAKUJ ich):
{reference_block}

Vygeneruj presne {count} NOVÝCH príkladov v rovnakom štýle ako vyššie.
Doplňujúca požiadavka učiteľa: "{description}"

Výstup MUSÍ byť iba JSON bez markdown:
{{"examples": [{{"example": "...", "input_type": "...", "answer": "..."}}]}}
Vygeneruj presne {count} príkladov. Každý príklad musí mať vyplnené "example", "input_type" a "answer".
"""


def _generate_more_batch(reference_examples: list, count: int, description: str, language: str = 'sk') -> list:
    """Single Gemini call for up to BATCH_SIZE new examples, using reference_examples as a style sample."""
    reference_block = "\n".join(
        json.dumps({'example': ex['example'], 'input_type': ex['input_type'], 'answer': ex['answer']}, ensure_ascii=False)
        for ex in reference_examples
    )
    prompt = SYSTEM_PROMPT_MORE.format(
        reference_block=reference_block, count=count, description=description,
        language_name=_language_name(language),
    )

    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config={
            'response_mime_type': 'application/json',
            'max_output_tokens': 8192,
        },
    )
    response = model.generate_content(prompt)
    return json.loads(response.text).get('examples', [])


def generate_teacher_task_more(reference_examples: list, count: int, description: str, fallback_type: str = 'arithmetic', language: str = 'sk') -> dict:
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
        return {'examples': generate_teacher_task(fallback_type, count, description, language)['examples']}

    all_examples = []
    remaining = count
    while remaining > 0:
        batch = min(remaining, BATCH_SIZE)
        try:
            examples = _generate_more_batch(reference_examples, batch, description, language)
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


def generate_teacher_task_mix(segments: list, description: str, language: str = 'sk') -> dict:
    """Calls generate_teacher_task per segment and combines results."""
    all_examples = []
    task_name = None

    for seg in segments:
        t = seg.get('type', 'arithmetic')
        c = min(max(int(seg.get('count', 5)), 1), 30)
        result = generate_teacher_task(t, c, description, language)
        if task_name is None:
            task_name = result.get('task_name', '')
        all_examples.extend(result.get('examples', []))

    prefix = FALLBACK_WORKSHEET_PREFIX.get(language, FALLBACK_WORKSHEET_PREFIX['sk'])
    return {
        'task_name': task_name or f'{prefix} – {description[:40]}',
        'form': 'classic',
        'examples': all_examples,
    }
