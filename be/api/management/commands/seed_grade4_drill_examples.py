"""
================================================================================
 Module: seed_grade4_drill_examples.py
 Description:
        Seeds grade 4 drill examples:
        - Násobilka do 10×10 (automatizácia)
        - Delenie so zvyškom
        - Násobenie dvojciferným číslom
        - Delenie jednociferným číslom
        - Sčítanie do 10 000
        - Odčítanie do 10 000

        Safe to run multiple times (idempotent per task+example text).
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Answer, Example, ExampleSkill, Skill, Task


class Command(BaseCommand):
    help = "Create grade 4 drill examples grouped by grade 4 skills."

    SKILL_TO_TASK = {
        "Násobilka do 10×10": "G4 Drill: Násobilka do 10x10",
        "Násobenie dvojciferným číslom": "G4 Drill: Násobenie dvojciferným",
        "Delenie jednociferným číslom": "G4 Drill: Delenie jednociferným",
        "Sčítanie do 10 000": "G4 Drill: Sčítanie do 10000",
        "Odčítanie do 10 000": "G4 Drill: Odčítanie do 10000",
        "Prevody jednotiek dĺžky II": "G4 Drill: Prevody dlzky II",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def _mul_10x10_examples(self):
        examples = []
        for a in range(1, 11):
            for b in range(1, 11):
                examples.append((f"{a} × {b}", str(a * b)))
        return examples

    def _mul_two_digit_examples(self):
        pairs = [
            (12, 3), (14, 4), (16, 5), (18, 6), (21, 7), (23, 8),
            (24, 9), (25, 4), (27, 6), (29, 7), (31, 8), (32, 9),
            (34, 5), (36, 7), (38, 4), (39, 6), (42, 8), (43, 7),
            (45, 9), (46, 5), (48, 6), (51, 7), (52, 8), (54, 9),
            (56, 4), (57, 6), (58, 7), (61, 8), (63, 9), (64, 5),
            (67, 6), (68, 7), (72, 8), (73, 9), (74, 6), (76, 5),
            (78, 4), (81, 7), (83, 6), (84, 9),
        ]
        return [(f"{a} × {b}", str(a * b)) for a, b in pairs]

    def _div_one_digit_examples(self):
        pairs = [
            (84, 3), (96, 4), (72, 6), (81, 9), (63, 7), (56, 8),
            (45, 5), (66, 6), (91, 7), (108, 9), (144, 8), (126, 7),
            (132, 6), (156, 4), (168, 3), (175, 5), (192, 8), (216, 9),
            (224, 7), (252, 6), (288, 9), (324, 4), (336, 8), (378, 7),
            (432, 9), (476, 7), (504, 8), (540, 6), (648, 9), (735, 7),
            (864, 8), (972, 9), (385, 5), (546, 7), (693, 9), (812, 4),
            (936, 6), (455, 5), (728, 8), (999, 9),
        ]
        return [(f"{a} ÷ {b}", str(a // b)) for a, b in pairs if a % b == 0]

    def _add_to_10000_examples(self):
        pairs = [
            (1250, 348), (2390, 411), (4875, 512), (6043, 1247), (7520, 2380),
            (3456, 2211), (6789, 1201), (4900, 305), (840, 7160), (5555, 2222),
            (704, 8296), (1299, 6701), (1888, 4112), (3333, 4444), (2567, 1433),
            (6006, 1994), (745, 9255), (3141, 2718), (4321, 1234), (987, 9013),
            (7600, 299), (2480, 3520), (3999, 4001), (4512, 2488), (5199, 1801),
            (6205, 1795), (7108, 892), (8350, 650), (1666, 7334), (2475, 3525),
            (3819, 2181), (4604, 1396), (5733, 2267), (6844, 1156), (7991, 1009),
            (845, 3155), (1960, 2040), (2777, 1223), (3588, 3412), (4399, 5601),
            (520, 9480), (6380, 3620), (7017, 2983), (8124, 876), (925, 6075),
            (1111, 8889), (2222, 7778), (4444, 5556), (678, 9322), (5432, 4568),
            (3700, 4300), (248, 9752), (9050, 450), (7643, 357), (6825, 1175),
            (5310, 2690), (4275, 1725), (3184, 2816), (2093, 3907), (1505, 4495),
        ]
        return [(f"{a} + {b}", str(a + b)) for a, b in pairs if a + b <= 10000]

    def _sub_to_10000_examples(self):
        pairs = [
            (9000, 245), (7800, 1326), (6500, 2140), (10000, 3750), (8450, 1975),
            (7320, 2480), (6880, 3990), (9400, 4050), (8100, 2560), (7010, 1890),
            (6200, 2740), (5550, 2380), (9300, 4720), (8040, 1990), (7600, 3330),
            (6900, 1450), (8750, 4260), (5200, 1180), (9999, 5080), (7400, 2670),
            (10000, 100), (9000, 3000), (8000, 5000), (7000, 4000), (6000, 2000),
            (5000, 2500), (4000, 1500), (3000, 1000), (10000, 7500), (8000, 3500),
            (7340, 850), (6290, 710), (8470, 530), (5380, 620), (9240, 760),
            (6510, 490), (7830, 170), (8160, 840), (4420, 580), (3750, 250),
            (7020, 2450), (8010, 3470), (9030, 4180), (6040, 1560), (5070, 2390),
            (4050, 1780), (3060, 1290), (2080, 1590), (9100, 2610), (8200, 3720),
            (9870, 6540), (8760, 5430), (7650, 4320), (6540, 3210), (5430, 2100),
            (4320, 1990), (3210, 1880), (2190, 1170), (1080, 760), (9999, 1111),
        ]
        return [(f"{a} - {b}", str(a - b)) for a, b in pairs if a - b >= 0]

    def _length_conversions_ii_examples(self):
        return [
            ("10 cm 3 mm = ? mm", "103"),
            ("12 cm 5 mm = ? mm", "125"),
            ("7 cm 8 mm = ? mm", "78"),
            ("2 dm 4 cm = ? cm", "24"),
            ("6 dm 9 cm = ? cm", "69"),
            ("4 dm 3 cm = ? mm", "430"),
            ("1 m 25 cm = ? cm", "125"),
            ("3 m 40 cm = ? cm", "340"),
            ("5 m 7 dm = ? dm", "57"),
            ("2 m 35 cm = ? cm", "235"),
            ("8 m 4 dm = ? cm", "840"),
            ("1 km 250 m = ? m", "1250"),
            ("2 km 75 m = ? m", "2075"),
            ("4 km 300 m = ? m", "4300"),
            ("3 m 6 cm = ? mm", "3060"),
            ("9 m 2 cm = ? mm", "9020"),
            ("5 dm 7 mm = ? mm", "507"),
            ("8 dm 9 mm = ? mm", "809"),
            ("6 cm 4 mm = ? mm", "64"),
            ("11 cm 2 mm = ? mm", "112"),
            ("13 dm 5 cm = ? cm", "135"),
            ("14 dm 8 cm = ? cm", "148"),
            ("4 m 5 cm = ? cm", "405"),
            ("7 m 9 cm = ? cm", "709"),
            ("2 m 8 dm = ? dm", "28"),
            ("9 m 1 dm = ? dm", "91"),
            ("6 m 3 dm = ? cm", "630"),
            ("12 m 7 dm = ? cm", "1270"),
            ("3 km 450 m = ? m", "3450"),
            ("7 km 25 m = ? m", "7025"),
            ("1 km 5 m = ? m", "1005"),
            ("2 km 999 m = ? m", "2999"),
            ("15 cm 6 mm = ? mm", "156"),
            ("18 cm 1 mm = ? mm", "181"),
            ("21 dm 3 cm = ? cm", "213"),
            ("25 dm 9 cm = ? cm", "259"),
            ("10 m 50 cm = ? cm", "1050"),
            ("12 m 75 cm = ? cm", "1275"),
            ("3 m 15 cm = ? mm", "3150"),
            ("4 m 28 cm = ? mm", "4280"),
        ]

    def _build_dataset(self):
        return {
            "Násobilka do 10×10": self._mul_10x10_examples(),
            "Násobenie dvojciferným číslom": self._mul_two_digit_examples(),
            "Delenie jednociferným číslom": self._div_one_digit_examples(),
            "Sčítanie do 10 000": self._add_to_10000_examples(),
            "Odčítanie do 10 000": self._sub_to_10000_examples(),
            "Prevody jednotiek dĺžky II": self._length_conversions_ii_examples(),
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
        self.stdout.write("=== Grade 4 drill seed preview ===")

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

        self.stdout.write(self.style.SUCCESS(f"\n✓ Grade 4 drill seed applied. Processed {created_or_updated} examples."))
