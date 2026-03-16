"""
================================================================================
 Module: seed_grade9_drill_examples.py
 Description:
        Seeds grade 9 preparation examples for Testovanie 9 from JSON file.
        Source JSON format follows testovanie9_matematika.json structure.

        Safe to run multiple times (idempotent per task+example text).
================================================================================
"""

import json
import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Answer, Example, ExampleSkill, Skill, Task


class Command(BaseCommand):
    help = "Create grade 9 Testovanie 9 examples from JSON grouped by categories."

    DEFAULT_JSON_PATH = Path(__file__).resolve().parents[3] / "data" / "testovanie9_matematika.json"
    PARENT_PREFIX = "Testovanie 9 - "
    TASK_PREFIX = "G9 Testovanie 9: "
    MAX_EXAMPLE_LENGTH = 255
    EXCLUDED_CATEGORIES = {"Priestorová predstavivosť"}
    BUCKET_PRACTICE = "Priklady"
    BUCKET_WORD = "Slovne ulohy"
    DISALLOWED_PROMPT_MARKERS = (
        "ktoré z tvrdení",
        "ktoré tvrdenie",
        "ktoré z uvedených",
        "ktoré vzťahy",
        "ktorý vzťah",
        "rozhodni o pravdivosti",
        "posúď pravdivosť",
        "v ktorej možnosti",
        "v ktorej z možností",
        "ktorá z možností",
        "ktorú možnosť",
        "vyber možnosť",
        "ani jeden vzťah",
        "platí iba",
        "je pravdivé",
        "je nepravdivé",
    )
    INPUT_TYPE_OVERRIDES = {
        "2022_05": "INLINE",
        "2022_13": "INLINE",
        "2023_11": "INLINE",
        "2025_01": "INLINE",
    }
    INLINE_LATEX_BY_ID = {
        "2022_05": r"\text{[2022_05] Vypocitaj: } (-4)^2 + (-4)^3",
        "2022_13": r"\text{[2022_13] Najdi cislo, ktore je riesenim rovnice: } 6x - (2 - 2x) = 3 \cdot (x - 4)",
        "2023_11": r"\text{[2023_11] Vypocitaj: } 1{,}5^2 + 1{,}6^2 + 1{,}7^2",
        "2025_01": r"\text{[2025_01] Vypocitaj hodnotu vyrazu } 3x + 2y + z \text{, ak } x = 5,\ y = 2,\ z = 8",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )
        parser.add_argument(
            "--json-path",
            default=str(self.DEFAULT_JSON_PATH),
            help="Path to Testovanie 9 JSON dataset.",
        )

    def _slug_ascii(self, value):
        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.replace("-", " ")
        normalized = re.sub(r"[^A-Za-z0-9 ]+", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _skill_name(self, category):
        return f"{self.PARENT_PREFIX}{self._slug_ascii(category)}"

    def _task_name(self, category):
        return f"{self.TASK_PREFIX}{self._slug_ascii(category)}"

    def _is_numeric_answer(self, answer_text):
        answer = (answer_text or "").strip()
        return bool(re.fullmatch(r"-?\d+(?:,\d+)?", answer))

    def _is_supported_answer(self, answer_text):
        return self._is_numeric_answer(answer_text)

    def _is_word_problem_item(self, item, input_type):
        if input_type == "INLINE":
            return False

        category = self._normalize_spaces(item.get("kategoria") or "")
        if category == "Slovné úlohy – pomery, miešanie, pohyb":
            return True

        prompt = self._normalize_spaces(item.get("zadanie") or "")
        word_count = len(re.findall(r"[^\W_]+", prompt, re.UNICODE))
        return word_count >= 8

    def _bucket_for_item(self, item, input_type):
        if self._is_word_problem_item(item, input_type):
            return self.BUCKET_WORD
        return self.BUCKET_PRACTICE

    def _is_selection_style_prompt(self, item):
        prompt = self._normalize_spaces(item.get("zadanie") or "").lower()
        return any(marker in prompt for marker in self.DISALLOWED_PROMPT_MARKERS)

    def _infer_input_type(self, item):
        item_id = self._normalize_spaces(item.get("id") or "")

        if item_id in self.INPUT_TYPE_OVERRIDES:
            return self.INPUT_TYPE_OVERRIDES[item_id]

        return "WORD"

    def _normalize_spaces(self, text):
        return re.sub(r"\s+", " ", (text or "").strip())

    def _escape_latex_text(self, text):
        escaped = (text or "")
        replacements = {
            "\\": r"\backslash{}",
            "{": r"\{",
            "}": r"\}",
            "%": r"\%",
            "&": r"\&",
            "#": r"\#",
            "$": r"\$",
            "_": r"\_",
        }
        for source, target in replacements.items():
            escaped = escaped.replace(source, target)
        return escaped

    def _wrap_text_as_latex(self, text):
        candidate = self._normalize_spaces(text)
        latex = r"\text{" + self._escape_latex_text(candidate) + "}"
        if len(latex) > self.MAX_EXAMPLE_LENGTH:
            return None
        return latex

    def _compose_plain_prompt(self, item):
        parts = []
        item_id = self._normalize_spaces(item.get("id") or "")
        zadanie = self._normalize_spaces(item.get("zadanie") or "")

        if item_id:
            if zadanie:
                parts.append(f"[{item_id}] {zadanie}")
            else:
                parts.append(f"[{item_id}]")
        if zadanie:
            if not item_id:
                parts.append(zadanie)

        dodatocne_info = self._normalize_spaces(item.get("dodatocne_info") or "")
        if dodatocne_info:
            parts.append(f"Udaje: {dodatocne_info}")
        elif item.get("vyzaduje_obrazok"):
            parts.append("Poznamka: povodne s obrazkom.")

        return " ".join(parts)

    def _build_example_text(self, item, input_type):
        item_id = self._normalize_spaces(item.get("id") or "")
        if input_type == "INLINE" and item_id in self.INLINE_LATEX_BY_ID:
            inline_text = self.INLINE_LATEX_BY_ID[item_id]
            if len(inline_text) > self.MAX_EXAMPLE_LENGTH:
                return None
            return inline_text

        prompt = self._compose_plain_prompt(item)
        if input_type == "WORD":
            if len(prompt) > self.MAX_EXAMPLE_LENGTH:
                return None
            return prompt

        return self._wrap_text_as_latex(prompt)

    def _build_dataset(self, payload):
        dataset = {
            self._skill_name(bucket): []
            for bucket in (self.BUCKET_PRACTICE, self.BUCKET_WORD)
        }
        for raw_item in payload.get("priklady", []):
            if (raw_item.get("typ") or "").strip().lower() != "otvorena":
                continue

            if raw_item.get("vyzaduje_obrazok"):
                continue

            raw_answer = self._normalize_spaces(str(raw_item.get("spravna_odpoved") or ""))
            if not self._is_supported_answer(raw_answer):
                continue

            if self._is_selection_style_prompt(raw_item):
                continue

            category = raw_item.get("kategoria") or "Nezaradena kategoria"
            if category in self.EXCLUDED_CATEGORIES:
                continue

            input_type = self._infer_input_type(raw_item)
            skill_name = self._skill_name(self._bucket_for_item(raw_item, input_type))
            example_text = self._build_example_text(raw_item, input_type)
            if not example_text or example_text.endswith("..."):
                continue

            row = {
                "example_text": example_text,
                "answer_text": self._resolve_answer_text(raw_item),
                "input_type": input_type,
            }
            dataset.setdefault(skill_name, []).append(row)

        return dataset

    def _resolve_answer_text(self, item):
        return self._normalize_spaces(str(item.get("spravna_odpoved") or ""))

    def _upsert_example(self, task, skill, example_text, answer_text, input_type="INLINE"):
        example = Example.objects.filter(task=task, example=example_text).first()
        if not example:
            example = Example.objects.create(
                task=task,
                example=example_text,
                input_type=input_type,
            )
        else:
            update_fields = []
            if example.input_type != input_type:
                example.input_type = input_type
                update_fields.append("input_type")
            if update_fields:
                example.save(update_fields=update_fields)

        ans = Answer.objects.filter(example=example).first()
        if not ans:
            Answer.objects.create(example=example, answer=answer_text)
        elif ans.answer != answer_text:
            ans.answer = answer_text
            ans.save(update_fields=["answer"])

        ExampleSkill.objects.get_or_create(example=example, skill=skill)

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        json_path = Path(options["json_path"])

        if not json_path.exists():
            self.stdout.write(self.style.ERROR(f"JSON file not found: {json_path}"))
            self.stdout.write(self.style.WARNING("Provide --json-path or copy JSON to be/data/testovanie9_matematika.json"))
            return

        with json_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        dataset = self._build_dataset(payload)
        self.stdout.write("=== Grade 9 Testovanie 9 seed preview (JSON) ===")

        total = 0
        for skill_name, pairs in dataset.items():
            total += len(pairs)
            self.stdout.write(f"- {skill_name}: {len(pairs)} examples")
            for preview in pairs[:2]:
                self.stdout.write(
                    f"    {preview['example_text']} = {preview['answer_text']} [{preview['input_type']}]"
                )

        self.stdout.write(f"Total examples in JSON dataset: {total}")

        if not apply_changes:
            self.stdout.write("\nDry-run only. Re-run with --apply to create/update examples.")
            return

        created_or_updated = 0
        excluded_skill_names = [self._skill_name(category) for category in self.EXCLUDED_CATEGORIES]
        expected_task_names = {
            self._task_name(skill_name.replace(self.PARENT_PREFIX, "", 1))
            for skill_name in dataset.keys()
        }
        with transaction.atomic():
            for skill_name in excluded_skill_names:
                task_name = self._task_name(skill_name.replace(self.PARENT_PREFIX, "", 1))
                excluded_task = Task.objects.filter(name=task_name).first()
                if excluded_task:
                    Example.objects.filter(task=excluded_task).delete()

            for stale_task in Task.objects.filter(name__startswith=self.TASK_PREFIX).exclude(name__in=expected_task_names):
                Example.objects.filter(task=stale_task).delete()

            for skill_name, pairs in dataset.items():
                skill = Skill.objects.filter(name=skill_name, deleted=False).first()
                if not skill:
                    self.stdout.write(self.style.WARNING(f"Skill not found, skipping: {skill_name}"))
                    continue

                if not pairs:
                    task_name = self._task_name(skill_name.replace(self.PARENT_PREFIX, "", 1))
                    stale_task = Task.objects.filter(name=task_name).first()
                    if stale_task:
                        Example.objects.filter(task=stale_task).delete()
                    continue

                # Word-problem form if category contains at least one word-like prompt.
                desired_form = "word-problem" if any(item["input_type"] == "WORD" for item in pairs) else "classic"
                task_name = self._task_name(skill_name.replace(self.PARENT_PREFIX, "", 1))

                task, _ = Task.objects.get_or_create(name=task_name, defaults={"form": desired_form})
                if task.form != desired_form:
                    task.form = desired_form
                    task.save(update_fields=["form"])
                task.skills.add(skill)

                expected_texts = {pair["example_text"] for pair in pairs}
                Example.objects.filter(task=task).exclude(example__in=expected_texts).delete()

                for pair in pairs:
                    self._upsert_example(
                        task,
                        skill,
                        pair["example_text"],
                        pair["answer_text"],
                        input_type=pair.get("input_type", "INLINE"),
                    )
                    created_or_updated += 1

            # Cleanup stale Testovanie 9 tasks with no examples left.
            Task.objects.filter(name__startswith=self.TASK_PREFIX).exclude(
                id__in=Example.objects.values_list("task_id", flat=True).distinct()
            ).delete()

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Grade 9 Testovanie 9 JSON seed applied. Processed {created_or_updated} examples.")
        )
