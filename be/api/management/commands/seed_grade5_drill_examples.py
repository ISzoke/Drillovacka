"""
================================================================================
 Module: seed_grade5_drill_examples.py
 Description:
        Seeds grade 5 drill examples:
        - Násobenie viacmiestnych čísel
        - Delenie viacmiestnych čísel
        - Zaokrúhľovanie čísel
        - Poradie operácií
        - Prevody času

        Safe to run multiple times (idempotent per task+example text).
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Answer, Example, ExampleSkill, Skill, Task


class Command(BaseCommand):
    help = "Create grade 5 drill examples grouped by grade 5 skills."

    SKILL_TO_TASK = {
        "Násobenie viacmiestnych čísel": "G5 Drill: Nasobenie viacmiestnych",
        "Delenie viacmiestnych čísel": "G5 Drill: Delenie viacmiestnych",
        "Zaokrúhľovanie čísel": "G5 Drill: Zaokruhlovanie",
        "Poradie operácií": "G5 Drill: Poradie operacii",
        "Prevody času": "G5 Drill: Prevody casu",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def _mul_multi_digit_examples(self):
        pairs = [
            (123, 4), (245, 3), (316, 5), (428, 6), (539, 7),
            (642, 8), (754, 9), (867, 4), (978, 3), (109, 7),
            (234, 12), (315, 14), (426, 11), (537, 13), (648, 12),
            (759, 15), (864, 14), (975, 16), (386, 12), (497, 13),
            (1250, 6), (2375, 4), (3490, 5), (4560, 7), (5680, 8),
            (6725, 9), (7840, 6), (8965, 4), (905, 12), (1111, 11),
            (2222, 12), (3333, 13), (4444, 14), (5555, 15), (6789, 12),
            (7890, 13), (8901, 14), (9012, 15), (2468, 16), (1357, 17),
        ]
        return [(f"{a} × {b}", str(a * b)) for a, b in pairs]

    def _div_multi_digit_examples(self):
        pairs = [
            (492, 4), (735, 3), (1260, 5), (2568, 6), (3773, 7),
            (5136, 8), (6804, 9), (3468, 4), (2934, 3), (763, 7),
            (2808, 12), (4410, 14), (4686, 11), (6981, 13), (7776, 12),
            (11385, 15), (12096, 14), (15600, 16), (4632, 12), (6461, 13),
            (7500, 6), (9500, 4), (17450, 5), (31920, 7), (45440, 8),
            (60525, 9), (47040, 6), (35860, 4), (10860, 12), (12221, 11),
            (26664, 12), (43329, 13), (62216, 14), (83325, 15), (81468, 12),
            (102570, 13), (124614, 14), (135180, 15), (39488, 16), (23069, 17),
        ]
        return [(f"{a} ÷ {b}", str(a // b)) for a, b in pairs if a % b == 0]

    def _rounding_examples(self):
        return [
            ("347 \\; \\text{zaokrúhli na desiatky}", "350"),
            ("684 \\; \\text{zaokrúhli na desiatky}", "680"),
            ("995 \\; \\text{zaokrúhli na desiatky}", "1000"),
            ("1423 \\; \\text{zaokrúhli na desiatky}", "1420"),
            ("8765 \\; \\text{zaokrúhli na desiatky}", "8770"),
            ("347 \\; \\text{zaokrúhli na stovky}", "300"),
            ("684 \\; \\text{zaokrúhli na stovky}", "700"),
            ("995 \\; \\text{zaokrúhli na stovky}", "1000"),
            ("1423 \\; \\text{zaokrúhli na stovky}", "1400"),
            ("8765 \\; \\text{zaokrúhli na stovky}", "8800"),
            ("347 \\; \\text{zaokrúhli na tisícky}", "0"),
            ("684 \\; \\text{zaokrúhli na tisícky}", "1000"),
            ("1499 \\; \\text{zaokrúhli na tisícky}", "1000"),
            ("1500 \\; \\text{zaokrúhli na tisícky}", "2000"),
            ("8765 \\; \\text{zaokrúhli na tisícky}", "9000"),
            ("12345 \\; \\text{zaokrúhli na stovky}", "12300"),
            ("12850 \\; \\text{zaokrúhli na stovky}", "12900"),
            ("12049 \\; \\text{zaokrúhli na desiatky}", "12050"),
            ("12044 \\; \\text{zaokrúhli na desiatky}", "12040"),
            ("9999 \\; \\text{zaokrúhli na tisícky}", "10000"),
            ("1001 \\; \\text{zaokrúhli na stovky}", "1000"),
            ("1050 \\; \\text{zaokrúhli na stovky}", "1100"),
            ("5499 \\; \\text{zaokrúhli na stovky}", "5500"),
            ("5501 \\; \\text{zaokrúhli na stovky}", "5500"),
            ("64999 \\; \\text{zaokrúhli na tisícky}", "65000"),
            ("65001 \\; \\text{zaokrúhli na tisícky}", "65000"),
            ("65499 \\; \\text{zaokrúhli na tisícky}", "65000"),
            ("65500 \\; \\text{zaokrúhli na tisícky}", "66000"),
            ("749 \\; \\text{zaokrúhli na stovky}", "700"),
            ("750 \\; \\text{zaokrúhli na stovky}", "800"),
            ("1749 \\; \\text{zaokrúhli na stovky}", "1700"),
            ("1750 \\; \\text{zaokrúhli na stovky}", "1800"),
            ("4444 \\; \\text{zaokrúhli na tisícky}", "4000"),
            ("4500 \\; \\text{zaokrúhli na tisícky}", "5000"),
            ("540 \\; \\text{zaokrúhli na desiatky}", "540"),
            ("545 \\; \\text{zaokrúhli na desiatky}", "550"),
            ("15440 \\; \\text{zaokrúhli na stovky}", "15400"),
            ("15450 \\; \\text{zaokrúhli na stovky}", "15500"),
            ("25440 \\; \\text{zaokrúhli na tisícky}", "25000"),
            ("25540 \\; \\text{zaokrúhli na tisícky}", "26000"),
        ]

    def _order_of_operations_examples(self):
        return [
            ("3 + 4 × 5", "23"),
            ("6 × 7 - 8", "34"),
            ("48 ÷ 6 + 9", "17"),
            ("5 + 6 × 3", "23"),
            ("72 ÷ 8 + 4", "13"),
            ("9 × 9 - 27", "54"),
            ("14 + 3 × 8", "38"),
            ("64 ÷ 8 + 7", "15"),
            ("45 - 5 × 6", "15"),
            ("100 - 36 ÷ 6", "94"),
            ("(3 + 4) × 5", "35"),
            ("6 × (7 - 2)", "30"),
            ("48 ÷ (6 + 2)", "6"),
            ("(5 + 6) × 3", "33"),
            ("72 ÷ (8 + 4)", "6"),
            ("9 × (9 - 3)", "54"),
            ("(14 + 10) × 2", "48"),
            ("64 ÷ (8 - 4)", "16"),
            ("(45 - 5) × 2", "80"),
            ("(100 - 36) ÷ 8", "8"),
            ("8 + 12 ÷ 3 × 2", "16"),
            ("40 - 18 ÷ 3 + 5", "39"),
            ("7 × 6 + 24 ÷ 4", "48"),
            ("90 ÷ 9 + 8 × 2", "26"),
            ("5 × 5 + 5 × 3", "40"),
            ("(8 + 12) ÷ 4 × 3", "15"),
            ("40 - (18 ÷ 3 + 5)", "29"),
            ("7 × (6 + 24 ÷ 4)", "84"),
            ("(90 ÷ 9 + 8) × 2", "36"),
            ("5 × (5 + 5) - 3", "47"),
            ("120 ÷ 6 ÷ 2", "10"),
            ("120 ÷ (6 ÷ 2)", "40"),
            ("18 - 6 + 4", "16"),
            ("18 - (6 + 4)", "8"),
            ("2 × 3 × 4 + 5", "29"),
            ("2 × (3 × (4 + 5))", "54"),
            ("81 ÷ 9 × 2 + 1", "19"),
            ("81 ÷ (9 × 2) + 1", "5"),
            ("7 + 7 + 7 × 7", "63"),
            ("(7 + 7 + 7) × 7", "147"),
        ]

    def _time_conversion_examples(self):
        return [
            ("1 h = ? min", "60"),
            ("2 h = ? min", "120"),
            ("3 h = ? min", "180"),
            ("90 min = ? s", "5400"),
            ("120 min = ? h", "2"),
            ("150 min = ? s", "9000"),
            ("1 min = ? s", "60"),
            ("5 min = ? s", "300"),
            ("12 min = ? s", "720"),
            ("180 s = ? min", "3"),
            ("600 s = ? min", "10"),
            ("3600 s = ? h", "1"),
            ("2 h 15 min = ? min", "135"),
            ("3 h 40 min = ? min", "220"),
            ("4 h 5 min = ? min", "245"),
            ("1 deň = ? h", "24"),
            ("2 dni = ? h", "48"),
            ("7 dní = ? h", "168"),
            ("48 h = ? dni", "2"),
            ("72 h = ? dni", "3"),
            ("1 týždeň = ? dní", "7"),
            ("2 týždne = ? dní", "14"),
            ("3 týždne = ? dní", "21"),
            ("14 dní = ? týždne", "2"),
            ("21 dní = ? týždne", "3"),
            ("1 h 30 min = ? min", "90"),
            ("2 h 45 min = ? min", "165"),
            ("5 h 20 min = ? min", "320"),
            ("75 min = ? s", "4500"),
            ("45 min = ? s", "2700"),
            ("30 min = ? s", "1800"),
            ("5400 s = ? min", "90"),
            ("9000 s = ? min", "150"),
            ("2700 s = ? min", "45"),
            ("10800 s = ? h", "3"),
            ("36 h = ? min", "2160"),
            ("60 h = ? min", "3600"),
            ("96 h = ? dni", "4"),
            ("240 min = ? h", "4"),
            ("600 min = ? h", "10"),
        ]

    def _build_dataset(self):
        return {
            "Násobenie viacmiestnych čísel": self._mul_multi_digit_examples(),
            "Delenie viacmiestnych čísel": self._div_multi_digit_examples(),
            "Zaokrúhľovanie čísel": self._rounding_examples(),
            "Poradie operácií": self._order_of_operations_examples(),
            "Prevody času": self._time_conversion_examples(),
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
        self.stdout.write("=== Grade 5 drill seed preview ===")

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

        self.stdout.write(self.style.SUCCESS(f"\n✓ Grade 5 drill seed applied. Processed {created_or_updated} examples."))
