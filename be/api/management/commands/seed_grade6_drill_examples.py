"""
================================================================================
 Module: seed_grade6_drill_examples.py
 Description:
        Seeds grade 6 drill examples:
        - Prirodzene cisla do milionov
    - Delitelnost a prvocisla
    - Rozklad na prvocinitele
    - Najvacsi spolocny delitel (NSD)
    - Najmensi spolocny nasobok (NSN)
        - Desatinne cisla
        - Zlomky + a -
        - Zlomky * a :

        Safe to run multiple times (idempotent per task+example text).
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Answer, Example, ExampleSkill, Skill, Task


class Command(BaseCommand):
    help = "Create grade 6 drill examples grouped by grade 6 skills."

    SKILL_TO_TASK = {
        "Prirodzene cisla do milionov": "G6 Drill: Prirodzene cisla",
        "Delitelnost a prvocisla": "G6 Drill: Delitelnost a prvocisla",
        "Rozklad na prvocinitele": "G6 Drill: Rozklad na prvocinitele",
        "Najvacsi spolocny delitel (NSD)": "G6 Drill: NSD",
        "Najmensi spolocny nasobok (NSN)": "G6 Drill: NSN",
        "Desatinne cisla": "G6 Drill: Desatinne cisla",
        "Zlomky + a -": "G6 Drill: Zlomky plus minus",
        "Zlomky * a :": "G6 Drill: Zlomky krat deleno",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def _frac_example(self, left_num, denominator, right_num, result_num, operator):
        return {
            "example_text": f"\\frac{{{left_num}}}{{{denominator}}} {operator} \\frac{{{right_num}}}{{{denominator}}}",
            "answer_text": f"\\frac{{{result_num}}}{{{denominator}}}",
            "input_type": "FRAC",
            "legacy_text": f"{left_num}/{denominator} {operator} {right_num}/{denominator}",
        }

    def _natural_numbers_examples(self):
        return [
            ("4 567 890 + 345 678", "4913568"),
            ("900 000 - 456 789", "443211"),
            ("7 654 321 + 2 345 679", "10000000"),
            ("1 200 300 + 405 600", "1605900"),
            ("9 999 999 - 8 765 432", "1234567"),
            ("6 500 000 - 499 999", "6000001"),
            ("3 456 789 + 123 456", "3580245"),
            ("8 000 000 - 3 210 987", "4789013"),
            ("5 678 901 + 321 099", "6000000"),
            ("2 222 222 + 3 333 333", "5555555"),
            ("max(4 567 890, 4 567 809)", "4567890"),
            ("max(900 000, 899 999)", "900000"),
            ("max(7 010 001, 7 100 001)", "7100001"),
            ("max(123 456, 654 321)", "654321"),
            ("max(8 000 008, 8 000 080)", "8000080"),
            ("min(4 567 890, 4 567 809)", "4567809"),
            ("min(900 000, 899 999)", "899999"),
            ("min(7 010 001, 7 100 001)", "7010001"),
            ("min(123 456, 654 321)", "123456"),
            ("min(8 000 008, 8 000 080)", "8000008"),
            ("3 450 000 + 2 550 000", "6000000"),
            ("7 700 700 - 700 700", "7000000"),
            ("4 040 404 + 505 050", "4545454"),
            ("6 060 606 - 60 606", "6000000"),
            ("1 111 111 + 8 888 889", "10000000"),
            ("9 876 543 - 1 234 567", "8641976"),
            ("2 468 000 + 3 579 000", "6047000"),
            ("5 000 500 - 500 500", "4500000"),
            ("7 890 123 + 109 877", "8000000"),
            ("4 321 000 - 321 000", "4000000"),
        ]

    def _divisibility_and_primes_examples(self):
        return [
            ("234 mod 3", "0"),
            ("235 mod 3", "1"),
            ("126 mod 9", "0"),
            ("127 mod 9", "1"),
            ("84 mod 7", "0"),
            ("85 mod 7", "1"),
            ("140 mod 5", "0"),
            ("143 mod 5", "3"),
            ("96 mod 8", "0"),
            ("99 mod 8", "3"),
            ("37 \\text{ je prvocislo }(1/0)", "1"),
            ("39 \\text{ je prvocislo }(1/0)", "0"),
            ("97 \\text{ je prvocislo }(1/0)", "1"),
            ("99 \\text{ je prvocislo }(1/0)", "0"),
            ("101 \\text{ je prvocislo }(1/0)", "1"),
            ("121 \\text{ je prvocislo }(1/0)", "0"),
            ("149 \\text{ je prvocislo }(1/0)", "1"),
            ("153 \\text{ je prvocislo }(1/0)", "0"),
            ("211 \\text{ je prvocislo }(1/0)", "1"),
            ("221 \\text{ je prvocislo }(1/0)", "0"),
            ("252 mod 4", "0"),
            ("253 mod 4", "1"),
            ("315 mod 5", "0"),
            ("317 mod 5", "2"),
            ("441 mod 7", "0"),
            ("442 mod 7", "1"),
            ("307 \\text{ je prvocislo }(1/0)", "1"),
            ("309 \\text{ je prvocislo }(1/0)", "0"),
            ("389 \\text{ je prvocislo }(1/0)", "1"),
            ("391 \\text{ je prvocislo }(1/0)", "0"),
        ]

    def _factorization_examples(self):
        return [
            ("36 = ? \\text{(prvocinitele, tvar }2\\times2\\times3\\times3\\text{)}", "2*2*3*3"),
            ("60 = ? \\text{(prvocinitele, tvar }2\\times2\\times3\\times5\\text{)}", "2*2*3*5"),
            ("72 = ? \\text{(prvocinitele, tvar }2\\times2\\times2\\times3\\times3\\text{)}", "2*2*2*3*3"),
            ("84 = ? \\text{(prvocinitele, tvar }2\\times2\\times3\\times7\\text{)}", "2*2*3*7"),
            ("90 = ? \\text{(prvocinitele, tvar }2\\times3\\times3\\times5\\text{)}", "2*3*3*5"),
            ("100 = ? \\text{(prvocinitele, tvar }2\\times2\\times5\\times5\\text{)}", "2*2*5*5"),
            ("108 = ? \\text{(prvocinitele, tvar }2\\times2\\times3\\times3\\times3\\text{)}", "2*2*3*3*3"),
            ("126 = ? \\text{(prvocinitele, tvar }2\\times3\\times3\\times7\\text{)}", "2*3*3*7"),
            ("150 = ? \\text{(prvocinitele, tvar }2\\times3\\times5\\times5\\text{)}", "2*3*5*5"),
            ("196 = ? \\text{(prvocinitele, tvar }2\\times2\\times7\\times7\\text{)}", "2*2*7*7"),
            ("225 = ? \\text{(prvocinitele, tvar }3\\times3\\times5\\times5\\text{)}", "3*3*5*5"),
            ("256 = ? \\text{(prvocinitele, tvar }2\\times2\\times2\\times2\\times2\\times2\\times2\\times2\\text{)}", "2*2*2*2*2*2*2*2"),
            ("270 = ? \\text{(prvocinitele, tvar }2\\times3\\times3\\times3\\times5\\text{)}", "2*3*3*3*5"),
            ("288 = ? \\text{(prvocinitele, tvar }2\\times2\\times2\\times2\\times2\\times3\\times3\\text{)}", "2*2*2*2*2*3*3"),
            ("315 = ? \\text{(prvocinitele, tvar }3\\times3\\times5\\times7\\text{)}", "3*3*5*7"),
            ("324 = ? \\text{(prvocinitele, tvar }2\\times2\\times3\\times3\\times3\\times3\\text{)}", "2*2*3*3*3*3"),
            ("360 = ? \\text{(prvocinitele, tvar }2\\times2\\times2\\times3\\times3\\times5\\text{)}", "2*2*2*3*3*5"),
            ("392 = ? \\text{(prvocinitele, tvar }2\\times2\\times2\\times7\\times7\\text{)}", "2*2*2*7*7"),
            ("405 = ? \\text{(prvocinitele, tvar }3\\times3\\times3\\times3\\times5\\text{)}", "3*3*3*3*5"),
            ("432 = ? \\text{(prvocinitele, tvar }2\\times2\\times2\\times2\\times3\\times3\\times3\\text{)}", "2*2*2*2*3*3*3"),
        ]

    def _nsd_examples(self):
        return [
            ("NSD(12,18)", "6"),
            ("NSD(24,36)", "12"),
            ("NSD(35,49)", "7"),
            ("NSD(42,56)", "14"),
            ("NSD(48,64)", "16"),
            ("NSD(54,72)", "18"),
            ("NSD(75,105)", "15"),
            ("NSD(84,126)", "42"),
            ("NSD(90,150)", "30"),
            ("NSD(96,144)", "48"),
            ("NSD(108,180)", "36"),
            ("NSD(120,168)", "24"),
            ("NSD(140,210)", "70"),
            ("NSD(156,234)", "78"),
            ("NSD(196,294)", "98"),
            ("NSD(144,216)", "72"),
            ("NSD(160,240)", "80"),
            ("NSD(180,252)", "36"),
            ("NSD(198,330)", "66"),
            ("NSD(225,375)", "75"),
            ("NSD(252,378)", "126"),
            ("NSD(270,405)", "135"),
            ("NSD(288,432)", "144"),
            ("NSD(320,480)", "160"),
            ("NSD(360,540)", "180"),
        ]

    def _nsn_examples(self):
        return [
            ("NSN(6,8)", "24"),
            ("NSN(12,18)", "36"),
            ("NSN(14,21)", "42"),
            ("NSN(9,15)", "45"),
            ("NSN(16,20)", "80"),
            ("NSN(18,24)", "72"),
            ("NSN(25,30)", "150"),
            ("NSN(28,42)", "84"),
            ("NSN(32,40)", "160"),
            ("NSN(36,54)", "108"),
            ("NSN(45,60)", "180"),
            ("NSN(48,72)", "144"),
            ("NSN(56,84)", "168"),
            ("NSN(63,90)", "630"),
            ("NSN(75,100)", "300"),
            ("NSN(72,96)", "288"),
            ("NSN(81,108)", "324"),
            ("NSN(90,120)", "360"),
            ("NSN(98,147)", "294"),
            ("NSN(105,140)", "420"),
            ("NSN(112,168)", "336"),
            ("NSN(126,189)", "378"),
            ("NSN(144,216)", "432"),
            ("NSN(150,225)", "450"),
            ("NSN(160,240)", "480"),
        ]

    def _decimal_numbers_examples(self):
        return [
            ("3.5 + 2.7", "6.2"),
            ("7.8 - 4.2", "3.6"),
            ("2.5 * 4", "10"),
            ("8.4 / 2", "4.2"),
            ("1.25 + 0.75", "2"),
            ("9.6 - 3.4", "6.2"),
            ("0.8 * 5", "4"),
            ("6.3 / 3", "2.1"),
            ("4.75 + 2.25", "7"),
            ("10.5 - 0.7", "9.8"),
            ("1.2 * 0.5", "0.6"),
            ("9.9 / 3", "3.3"),
            ("12.34 + 0.66", "13"),
            ("15.0 - 7.25", "7.75"),
            ("2.4 * 2.5", "6"),
            ("7.2 / 1.2", "6"),
            ("0.35 + 0.65", "1"),
            ("5.55 - 2.05", "3.5"),
            ("3.3 * 3", "9.9"),
            ("4.8 / 0.6", "8"),
            ("2.75 + 1.25", "4"),
            ("6.02 - 1.02", "5"),
            ("1.6 * 2.5", "4"),
            ("8.1 / 0.9", "9"),
            ("0.04 + 0.96", "1"),
            ("9.01 - 0.01", "9"),
            ("0.125 * 8", "1"),
            ("3.6 / 0.3", "12"),
            ("14.7 + 5.3", "20"),
            ("20.0 - 12.8", "7.2"),
            ("4.5 * 2", "9"),
            ("18.9 / 3", "6.3"),
            ("1.11 + 2.22", "3.33"),
            ("7.77 - 0.77", "7"),
            ("2.2 * 1.5", "3.3"),
            ("5.6 / 0.7", "8"),
            ("0.9 + 0.09", "0.99"),
            ("1.01 - 0.11", "0.9"),
            ("2.75 * 4", "11"),
            ("16.5 / 5", "3.3"),
        ]

    def _same_denominator_fractions_examples(self):
        return [
            self._frac_example(1, 7, 2, 3, "+"),
            self._frac_example(3, 8, 2, 5, "+"),
            self._frac_example(4, 9, 1, 5, "+"),
            self._frac_example(5, 12, 3, 8, "+"),
            self._frac_example(7, 10, 2, 9, "+"),
            self._frac_example(2, 11, 6, 8, "+"),
            self._frac_example(3, 5, 1, 4, "+"),
            self._frac_example(4, 13, 5, 9, "+"),
            self._frac_example(6, 14, 3, 9, "+"),
            self._frac_example(8, 15, 2, 10, "+"),
            self._frac_example(5, 7, 2, 3, "-"),
            self._frac_example(7, 8, 3, 4, "-"),
            self._frac_example(8, 9, 1, 7, "-"),
            self._frac_example(11, 12, 5, 6, "-"),
            self._frac_example(9, 10, 4, 5, "-"),
            self._frac_example(10, 11, 7, 3, "-"),
            self._frac_example(4, 5, 1, 3, "-"),
            self._frac_example(12, 13, 6, 6, "-"),
            self._frac_example(13, 14, 5, 8, "-"),
            self._frac_example(14, 15, 9, 5, "-"),
            self._frac_example(2, 6, 3, 5, "+"),
            self._frac_example(1, 4, 2, 3, "+"),
            self._frac_example(3, 10, 4, 7, "+"),
            self._frac_example(6, 7, 0, 6, "+"),
            self._frac_example(9, 12, 1, 10, "+"),
            self._frac_example(5, 9, 3, 2, "-"),
            self._frac_example(7, 11, 1, 6, "-"),
            self._frac_example(6, 8, 2, 4, "-"),
            self._frac_example(11, 15, 4, 7, "-"),
            self._frac_example(10, 14, 3, 7, "-"),
        ]

    def _frac_mul_div_example(self, a, b, c, d, result_num, result_den, operator):
        op_text = "\\cdot" if operator == "*" else ":"
        return {
            "example_text": f"\\frac{{{a}}}{{{b}}} {op_text} \\frac{{{c}}}{{{d}}}",
            "answer_text": f"\\frac{{{result_num}}}{{{result_den}}}",
            "input_type": "FRAC",
        }

    def _fractions_mul_div_examples(self):
        return [
            self._frac_mul_div_example(1, 2, 3, 4, 3, 8, "*"),
            self._frac_mul_div_example(2, 3, 3, 5, 2, 5, "*"),
            self._frac_mul_div_example(4, 7, 7, 8, 1, 2, "*"),
            self._frac_mul_div_example(5, 6, 3, 10, 1, 4, "*"),
            self._frac_mul_div_example(3, 8, 16, 9, 2, 3, "*"),
            self._frac_mul_div_example(7, 9, 3, 14, 1, 6, "*"),
            self._frac_mul_div_example(11, 12, 6, 11, 1, 2, "*"),
            self._frac_mul_div_example(5, 8, 4, 15, 1, 6, "*"),
            self._frac_mul_div_example(9, 10, 5, 6, 3, 4, "*"),
            self._frac_mul_div_example(2, 11, 11, 3, 2, 3, "*"),
            self._frac_mul_div_example(3, 4, 2, 5, 15, 8, ":"),
            self._frac_mul_div_example(5, 6, 1, 3, 5, 2, ":"),
            self._frac_mul_div_example(7, 8, 7, 16, 2, 1, ":"),
            self._frac_mul_div_example(9, 10, 3, 5, 3, 2, ":"),
            self._frac_mul_div_example(11, 12, 11, 6, 1, 2, ":"),
            self._frac_mul_div_example(4, 9, 2, 3, 2, 3, ":"),
            self._frac_mul_div_example(5, 14, 15, 7, 1, 6, ":"),
            self._frac_mul_div_example(8, 15, 4, 5, 2, 3, ":"),
            self._frac_mul_div_example(3, 11, 9, 22, 2, 3, ":"),
            self._frac_mul_div_example(6, 13, 3, 26, 4, 1, ":"),
        ]

    def _build_dataset(self):
        return {
            "Prirodzene cisla do milionov": self._natural_numbers_examples(),
            "Delitelnost a prvocisla": self._divisibility_and_primes_examples(),
            "Rozklad na prvocinitele": self._factorization_examples(),
            "Najvacsi spolocny delitel (NSD)": self._nsd_examples(),
            "Najmensi spolocny nasobok (NSN)": self._nsn_examples(),
            "Desatinne cisla": self._decimal_numbers_examples(),
            "Zlomky + a -": self._same_denominator_fractions_examples(),
            "Zlomky * a :": self._fractions_mul_div_examples(),
        }

    def _upsert_example(self, task, skill, example_text, answer_text, input_type="INLINE", legacy_text=None):
        example = Example.objects.filter(task=task, example=example_text).first()
        if not example and legacy_text:
            example = Example.objects.filter(task=task, example=legacy_text).first()
        if not example:
            example = Example.objects.create(
                task=task,
                example=example_text,
                input_type=input_type,
            )
        else:
            update_fields = []
            if example.example != example_text:
                example.example = example_text
                update_fields.append("example")
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
        self.stdout.write("=== Grade 6 drill seed preview ===")

        for skill_name, pairs in dataset.items():
            self.stdout.write(f"- {skill_name}: {len(pairs)} examples")
            for preview in pairs[:3]:
                if isinstance(preview, dict):
                    self.stdout.write(f"    {preview['example_text']} = {preview['answer_text']}")
                else:
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

                for pair in pairs:
                    if isinstance(pair, dict):
                        self._upsert_example(
                            task,
                            skill,
                            pair["example_text"],
                            pair["answer_text"],
                            input_type=pair.get("input_type", "INLINE"),
                            legacy_text=pair.get("legacy_text"),
                        )
                    else:
                        example_text, answer_text = pair
                        self._upsert_example(task, skill, example_text, answer_text)
                    created_or_updated += 1

        self.stdout.write(self.style.SUCCESS(f"\n✓ Grade 6 drill seed applied. Processed {created_or_updated} examples."))
