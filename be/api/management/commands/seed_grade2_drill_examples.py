"""
================================================================================
 Module: seed_grade2_drill_examples.py
 Description:
        Seeds grade 2 drill examples for mental arithmetic automation to 100.
        Categories:
        - Sčítanie do 100 bez prechodu cez desiatku
        - Sčítanie do 100 s prechodom cez desiatku
        - Odčítanie do 100
        - Doplňovanie do 100

        Safe to run multiple times (idempotent per task+example text).
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Answer, Example, ExampleSkill, Skill, Task


class Command(BaseCommand):
    help = "Create grade 2 drill examples grouped by new grade 2 skills."

    SKILL_TO_TASK = {
        "Sčítanie do 100 bez prechodu cez desiatku": "G2 Drill: Sčítanie bez prechodu",
        "Sčítanie do 100 s prechodom cez desiatku": "G2 Drill: Sčítanie s prechodom",
        "Odčítanie do 100": "G2 Drill: Odčítanie do 100",
        "Doplňovanie do 100": "G2 Drill: Doplňovanie do 100",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def _addition_no_carry_examples(self):
        examples = []
        base_values = [10, 20, 30, 40, 50, 60, 70, 80]
        add_values = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        for a in base_values:
            for b in add_values:
                if a + b <= 100:
                    examples.append((f"{a} + {b}", str(a + b)))

        extras = [(34, 5), (42, 7), (56, 3), (81, 8)]
        for a, b in extras:
            examples.append((f"{a} + {b}", str(a + b)))
        return examples

    def _addition_with_carry_examples(self):
        examples = []
        pairs = [
            (27, 8), (36, 7), (48, 9), (59, 6), (68, 7), (75, 8),
            (14, 9), (25, 7), (37, 6), (46, 8), (58, 7), (69, 5),
            (16, 8), (17, 9), (18, 7), (19, 8),
            (24, 9), (26, 8), (28, 7),
            (35, 8), (38, 6), (39, 7),
            (44, 7), (45, 8), (47, 6), (49, 5),
            (53, 9), (54, 8), (57, 5),
            (62, 9), (63, 8), (64, 7), (66, 6),
            (71, 9), (72, 8), (74, 7), (76, 6),
            (81, 9), (82, 8), (83, 7), (84, 6),
            (91, 8), (92, 7), (93, 6),
        ]
        for a, b in pairs:
            if a + b <= 100:
                examples.append((f"{a} + {b}", str(a + b)))
        return examples

    def _subtraction_examples(self):
        examples = []
        pairs = [
            (56, 4), (70, 20), (84, 3), (90, 30), (67, 5), (52, 8),
            (73, 9), (61, 7), (88, 6), (95, 40), (47, 9), (100, 30),
            (64, 7), (63, 8), (72, 6), (71, 9), (82, 7), (81, 8),
            (75, 9), (74, 8), (83, 9), (92, 8), (91, 7), (99, 6),
            (58, 9), (57, 8), (66, 9), (65, 7), (54, 6), (53, 5),
            (44, 7), (43, 8), (39, 6), (38, 7),
            (86, 9), (87, 8), (96, 7), (97, 6),
            (78, 4), (79, 5), (68, 3), (69, 4),
            (55, 20), (85, 20), (94, 30), (76, 40),
        ]
        for a, b in pairs:
            if a - b >= 0:
                examples.append((f"{a} - {b}", str(a - b)))
        return examples

    def _fill_to_100_examples(self):
        examples = []

        # Doplňovanie do stovky (typické mentálne doplnenie)
        for a in [10, 20, 30, 40, 50, 55, 60, 65, 70, 80, 85, 90]:
            examples.append((f"{a} + ? = 100", str(100 - a)))

        # Doplňovanie do ľubovoľného cieľa (napr. 70 + ? = 85)
        custom_targets = [
            (70, 85),
            (65, 80),
            (45, 60),
            (28, 40),
            (39, 50),
            (76, 90),
            (57, 70),
            (48, 55),
            (24, 35),
        ]
        for a, target in custom_targets:
            if target > a:
                examples.append((f"{a} + ? = {target}", str(target - a)))

        # Explicitne z požiadavky
        examples.append(("30 + ? = 90", "60"))
        return examples

    def _build_dataset(self):
        return {
            "Sčítanie do 100 bez prechodu cez desiatku": self._addition_no_carry_examples(),
            "Sčítanie do 100 s prechodom cez desiatku": self._addition_with_carry_examples(),
            "Odčítanie do 100": self._subtraction_examples(),
            "Doplňovanie do 100": self._fill_to_100_examples(),
        }

    def _upsert_example(self, task, skill, example_text, answer_text):
        example = Example.objects.filter(task=task, example=example_text).first()
        if not example:
            example = Example.objects.create(
                task=task,
                example=example_text,
                input_type="INLINE",
            )

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
        self.stdout.write("=== Grade 2 drill seed preview ===")

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
                task.skills.add(skill)

                for example_text, answer_text in pairs:
                    self._upsert_example(task, skill, example_text, answer_text)
                    created_or_updated += 1

        self.stdout.write(self.style.SUCCESS(f"\n✓ Grade 2 drill seed applied. Processed {created_or_updated} examples."))
