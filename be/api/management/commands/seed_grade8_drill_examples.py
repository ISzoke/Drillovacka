"""
================================================================================
 Module: seed_grade8_drill_examples.py
 Description:
        Seeds grade 8 drill examples:
        - Rovnice
        - Mocniny a odmocniny
        - Percenta
        - Pytagorova veta

        Safe to run multiple times (idempotent per task+example text).
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Answer, Example, ExampleSkill, Skill, Task


class Command(BaseCommand):
    help = "Create grade 8 drill examples grouped by grade 8 skills."

    SKILL_TO_TASK = {
        "Rovnice": "G8 Drill: Rovnice",
        "Mocniny a odmocniny": "G8 Drill: Mocniny odmocniny",
        "Percenta": "G8 Drill: Percenta",
        "Pytagorova veta": "G8 Drill: Pytagorova veta",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def _percent_to_latex(self, percent, base):
        return f"{percent}\\%\\ \\text{{z}}\\ {base}"

    def _pythagorean_to_latex(self, values_text, unknown):
        return f"\\text{{{values_text}. Vypocitaj }} {unknown}"

    def _equations_examples(self):
        return [
            ("3x + 5 = 17", "4"),
            ("2x - 7 = 9", "8"),
            ("5x + 1 = 26", "5"),
            ("4x - 12 = 8", "5"),
            ("7x + 3 = 31", "4"),
            ("6x - 9 = 15", "4"),
            ("8x + 4 = 44", "5"),
            ("9x - 18 = 27", "5"),
            ("10x + 5 = 65", "6"),
            ("12x - 24 = 36", "5"),
            ("x/2 + 3 = 11", "16"),
            ("x/3 - 2 = 4", "18"),
            ("x/4 + 1 = 6", "20"),
            ("x/5 - 3 = 2", "25"),
            ("(x - 2)/3 = 4", "14"),
            ("(x + 6)/2 = 10", "14"),
            ("2(x - 3) = 14", "10"),
            ("3(x + 1) = 21", "6"),
            ("4(x - 2) = 24", "8"),
            ("5(x + 2) = 45", "7"),
        ]

    def _powers_roots_examples(self):
        return [
            ("\\sqrt{64}", "8"),
            ("\\sqrt{81}", "9"),
            ("\\sqrt{121}", "11"),
            ("\\sqrt{144}", "12"),
            ("\\sqrt{169}", "13"),
            ("2^2", "4"),
            ("3^2", "9"),
            ("4^2", "16"),
            ("5^2", "25"),
            ("6^2", "36"),
            ("\\sqrt{49} + 3", "10"),
            ("\\sqrt{100} - 4", "6"),
            ("2^2 + 5", "9"),
            ("3^2 + 4^2", "25"),
            ("\\sqrt{225}", "15"),
            ("\\sqrt{256}", "16"),
            ("7^2", "49"),
            ("8^2", "64"),
            ("9^2", "81"),
            ("10^2", "100"),
        ]

    def _percent_examples(self):
        return [
            (self._percent_to_latex(20, 150), "30"),
            (self._percent_to_latex(10, 240), "24"),
            (self._percent_to_latex(25, 80), "20"),
            (self._percent_to_latex(15, 200), "30"),
            (self._percent_to_latex(5, 360), "18"),
            (self._percent_to_latex(40, 90), "36"),
            (self._percent_to_latex(12, 250), "30"),
            (self._percent_to_latex(30, 70), "21"),
            (self._percent_to_latex(75, 120), "90"),
            (self._percent_to_latex(50, 64), "32"),
            (self._percent_to_latex(8, 500), "40"),
            (self._percent_to_latex(35, 200), "70"),
            (self._percent_to_latex(60, 45), "27"),
            (self._percent_to_latex(18, 150), "27"),
            (self._percent_to_latex(22, 50), "11"),
            (self._percent_to_latex(1, 700), "7"),
            (self._percent_to_latex(2, 350), "7"),
            (self._percent_to_latex(125, 40), "50"),
            (self._percent_to_latex(150, 20), "30"),
            (self._percent_to_latex(90, 30), "27"),
        ]

    def _pythagorean_examples(self):
        return [
            (self._pythagorean_to_latex("a = 6, b = 8", "c"), "10"),
            (self._pythagorean_to_latex("a = 5, b = 12", "c"), "13"),
            (self._pythagorean_to_latex("a = 9, b = 12", "c"), "15"),
            (self._pythagorean_to_latex("a = 8, b = 15", "c"), "17"),
            (self._pythagorean_to_latex("a = 7, b = 24", "c"), "25"),
            (self._pythagorean_to_latex("a = 3, c = 5", "b"), "4"),
            (self._pythagorean_to_latex("a = 12, c = 13", "b"), "5"),
            (self._pythagorean_to_latex("b = 24, c = 25", "a"), "7"),
            (self._pythagorean_to_latex("a = 20, c = 29", "b"), "21"),
            (self._pythagorean_to_latex("b = 40, c = 41", "a"), "9"),
            (self._pythagorean_to_latex("a = 16, b = 12", "c"), "20"),
            (self._pythagorean_to_latex("a = 10, b = 24", "c"), "26"),
            (self._pythagorean_to_latex("a = 11, b = 60", "c"), "61"),
            (self._pythagorean_to_latex("a = 28, b = 45", "c"), "53"),
            (self._pythagorean_to_latex("a = 33, b = 56", "c"), "65"),
            (self._pythagorean_to_latex("a = 9, c = 41", "b"), "40"),
            (self._pythagorean_to_latex("a = 36, c = 39", "b"), "15"),
            (self._pythagorean_to_latex("b = 48, c = 50", "a"), "14"),
            (self._pythagorean_to_latex("b = 84, c = 85", "a"), "13"),
            (self._pythagorean_to_latex("a = 65, c = 97", "b"), "72"),
        ]

    def _build_dataset(self):
        return {
            "Rovnice": self._equations_examples(),
            "Mocniny a odmocniny": self._powers_roots_examples(),
            "Percenta": self._percent_examples(),
            "Pytagorova veta": self._pythagorean_examples(),
        }

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

        dataset = self._build_dataset()
        self.stdout.write("=== Grade 8 drill seed preview ===")

        for skill_name, pairs in dataset.items():
            self.stdout.write(f"- {skill_name}: {len(pairs)} examples")
            for preview in pairs[:3]:
                self.stdout.write(f"    {preview[0]} = {preview[1]}")

        if not apply_changes:
            self.stdout.write("\nDry-run only. Re-run with --apply to create/update examples.")
            return

        created_or_updated = 0
        with transaction.atomic():
            for skill_name, pairs in dataset.items():
                skill = Skill.objects.filter(name=skill_name, deleted=False).first()
                if not skill:
                    self.stdout.write(self.style.WARNING(f"Skill not found, skipping: {skill_name}"))
                    continue

                task_name = self.SKILL_TO_TASK[skill_name]
                task, _ = Task.objects.get_or_create(name=task_name, defaults={"form": "classic"})
                if task.form != "classic":
                    task.form = "classic"
                    task.save(update_fields=["form"])
                task.skills.add(skill)

                expected_texts = {pair[0] for pair in pairs}
                Example.objects.filter(task=task).exclude(example__in=expected_texts).delete()

                for example_text, answer_text in pairs:
                    self._upsert_example(task, skill, example_text, answer_text, input_type="INLINE")
                    created_or_updated += 1

        self.stdout.write(self.style.SUCCESS(f"\n✓ Grade 8 drill seed applied. Processed {created_or_updated} examples."))
