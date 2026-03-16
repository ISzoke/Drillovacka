"""
================================================================================
 Module: seed_grade3_drill_examples.py
 Description:
        Seeds grade 3 drill examples:
        - Malá násobilka I (do 5×5)
        - Malá násobilka II (do 10×10)
        - Malé delenie I (do 5×5)
        - Malé delenie II (do 10×10)
        - Doplňovanie násobenia a delenia
        - Sčítanie do 1000
        - Odčítanie do 1000

        Safe to run multiple times (idempotent per task+example text).
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Answer, Example, ExampleSkill, Skill, Task


class Command(BaseCommand):
    help = "Create grade 3 drill examples grouped by grade 3 skills."

    SKILL_TO_TASK = {
        "Malá násobilka I (do 5×5)": "G3 Drill: Malá násobilka I",
        "Malá násobilka II (do 10×10)": "G3 Drill: Malá násobilka II",
        "Malé delenie I (do 5×5)": "G3 Drill: Malé delenie I",
        "Malé delenie II (do 10×10)": "G3 Drill: Malé delenie II",
        "Doplňovanie násobenia a delenia": "G3 Drill: Doplňovanie v násobení/delení",
        "Sčítanie do 1000": "G3 Drill: Sčítanie do 1000",
        "Odčítanie do 1000": "G3 Drill: Odčítanie do 1000",
        "Prevody jednotiek dĺžky I": "G3 Drill: Prevody dlzky I",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def _mul_small_i_examples(self):
        examples = []
        for a in range(1, 6):
            for b in range(1, 6):
                examples.append((f"{a} × {b}", str(a * b)))
        return examples

    def _mul_small_ii_examples(self):
        examples = []
        for a in range(1, 11):
            for b in range(1, 11):
                if max(a, b) > 5:
                    examples.append((f"{a} × {b}", str(a * b)))
        return examples

    def _div_small_i_examples(self):
        seen = set()
        examples = []
        for a in range(2, 6):
            for b in range(2, 6):
                dividend = a * b
                key = (dividend, b)
                if key not in seen:
                    seen.add(key)
                    examples.append((f"{dividend} ÷ {b}", str(a)))
        return examples

    def _div_small_ii_examples(self):
        seen = set()
        examples = []
        for a in range(2, 11):
            for b in range(2, 11):
                if max(a, b) > 5:
                    dividend = a * b
                    key = (dividend, b)
                    if key not in seen:
                        seen.add(key)
                        examples.append((f"{dividend} ÷ {b}", str(a)))
        return examples

    def _fill_mul_div_examples(self):
        examples = []

        fill_mul = [
            ("7 × ? = 56", "8"),
            ("6 × ? = 42", "7"),
            ("8 × ? = 40", "5"),
            ("9 × ? = 72", "8"),
            ("? × 7 = 35", "5"),
            ("? × 8 = 56", "7"),
            ("? × 9 = 81", "9"),
            ("? × 6 = 48", "8"),
            ("4 × ? = 36", "9"),
            ("5 × ? = 45", "9"),
        ]

        fill_div = [
            ("56 ÷ ? = 7", "8"),
            ("90 ÷ ? = 10", "9"),
            ("72 ÷ ? = 8", "9"),
            ("63 ÷ ? = 9", "7"),
            ("? ÷ 7 = 8", "56"),
            ("? ÷ 8 = 6", "48"),
            ("? ÷ 9 = 5", "45"),
            ("? ÷ 6 = 7", "42"),
            ("48 ÷ ? = 6", "8"),
            ("64 ÷ ? = 8", "8"),
        ]

        examples.extend(fill_mul)
        examples.extend(fill_div)
        return examples

    def _add_to_1000_examples(self):
        pairs = [
            # bez prechodu cez stovku
            (345, 278), (126, 374), (499, 201), (640, 125), (725, 164),
            (808, 92),  (431, 267), (550, 340), (272, 518), (389, 411),
            (147, 653), (286, 414), (175, 225), (505, 295), (333, 444),
            (219, 381), (620, 180), (470, 230), (128, 772), (356, 244),
            # okrúhle stovky + číslo
            (300, 400), (200, 750), (500, 499), (100, 899), (700, 200),
            (400, 600), (600, 300), (800, 150), (250, 750), (450, 450),
            # prechod cez stovku
            (164, 238), (275, 347), (383, 418), (491, 309), (172, 639),
            (284, 516), (391, 409), (463, 137), (581, 219), (674, 126),
            # trojciferné + dvojciferné
            (734, 85), (629, 71), (847, 53), (538, 62), (924, 76),
            (651, 49), (783, 17), (816, 84), (442, 58), (375, 25),
            # rôzne
            (101, 899), (212, 388), (323, 477), (434, 566), (545, 455),
            (656, 244), (767, 133), (878, 22), (989, 11), (111, 889),
        ]
        return [(f"{a} + {b}", str(a + b)) for a, b in pairs if a + b <= 1000]

    def _sub_to_1000_examples(self):
        pairs = [
            # základ
            (900, 245), (780, 326), (650, 214), (1000, 375), (845, 197),
            (732, 248), (688, 399), (940, 405), (810, 256), (701, 189),
            (620, 274), (555, 238), (930, 472), (804, 199), (760, 333),
            (690, 145), (875, 426), (520, 118), (999, 508), (740, 267),
            # stovky - stovky
            (1000, 100), (900, 300), (800, 500), (700, 400), (600, 200),
            (500, 250), (400, 150), (300, 100), (1000, 750), (800, 350),
            # trojciferné - dvojciferné
            (734, 85), (629, 71), (847, 53), (538, 62), (924, 76),
            (651, 49), (783, 17), (816, 84), (442, 58), (375, 25),
            # prechod cez stovku
            (702, 245), (801, 347), (903, 418), (604, 156), (507, 239),
            (405, 178), (306, 129), (208, 159), (910, 261), (820, 372),
            # rôzne
            (987, 654), (876, 543), (765, 432), (654, 321), (543, 210),
            (432, 199), (321, 188), (219, 117), (108, 76),  (999, 111),
        ]
        return [(f"{a} - {b}", str(a - b)) for a, b in pairs if a - b >= 0]

    def _length_conversions_i_examples(self):
        pairs = [
            ("1 cm = ? mm", "10"),
            ("2 cm = ? mm", "20"),
            ("7 cm = ? mm", "70"),
            ("9 cm = ? mm", "90"),
            ("10 mm = ? cm", "1"),
            ("30 mm = ? cm", "3"),
            ("80 mm = ? cm", "8"),
            ("120 mm = ? cm", "12"),
            ("1 dm = ? cm", "10"),
            ("4 dm = ? cm", "40"),
            ("9 dm = ? cm", "90"),
            ("10 cm = ? dm", "1"),
            ("50 cm = ? dm", "5"),
            ("80 cm = ? dm", "8"),
            ("1 m = ? dm", "10"),
            ("3 m = ? dm", "30"),
            ("6 m = ? dm", "60"),
            ("10 dm = ? m", "1"),
            ("40 dm = ? m", "4"),
            ("90 dm = ? m", "9"),
            ("1 m = ? cm", "100"),
            ("2 m = ? cm", "200"),
            ("7 m = ? cm", "700"),
            ("100 cm = ? m", "1"),
            ("500 cm = ? m", "5"),
            ("900 cm = ? m", "9"),
            ("1 km = ? m", "1000"),
            ("2 km = ? m", "2000"),
            ("5 km = ? m", "5000"),
            ("1000 m = ? km", "1"),
            ("3000 m = ? km", "3"),
            ("7000 m = ? km", "7"),
            ("1 m = ? mm", "1000"),
            ("4 m = ? mm", "4000"),
            ("8 m = ? mm", "8000"),
            ("2000 mm = ? m", "2"),
            ("5000 mm = ? m", "5"),
            ("9000 mm = ? m", "9"),
            ("1 dm = ? mm", "100"),
            ("7 dm = ? mm", "700"),
        ]
        return pairs

    def _build_dataset(self):
        return {
            "Malá násobilka I (do 5×5)": self._mul_small_i_examples(),
            "Malá násobilka II (do 10×10)": self._mul_small_ii_examples(),
            "Malé delenie I (do 5×5)": self._div_small_i_examples(),
            "Malé delenie II (do 10×10)": self._div_small_ii_examples(),
            "Doplňovanie násobenia a delenia": self._fill_mul_div_examples(),
            "Sčítanie do 1000": self._add_to_1000_examples(),
            "Odčítanie do 1000": self._sub_to_1000_examples(),
            "Prevody jednotiek dĺžky I": self._length_conversions_i_examples(),
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
        self.stdout.write("=== Grade 3 drill seed preview ===")

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

        self.stdout.write(self.style.SUCCESS(f"\n✓ Grade 3 drill seed applied. Processed {created_or_updated} examples."))
