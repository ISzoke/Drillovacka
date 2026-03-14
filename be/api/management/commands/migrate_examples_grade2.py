"""
================================================================================
 Module: migrate_examples_grade2.py
 Description:
        Migrates examples to grade 2 skills:
        - Sčítanie do 20: all with results 11-20 (including carry/without carry)
        - Odčítanie do 20: all with minuend 11-20 (including borrow/without borrow)
        
        Only whole numbers, excludes fractions (\frac{) and decimals (.).
================================================================================
"""

import re
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import ExampleSkill, Skill


def is_whole_numbers_only(example_text):
    """Check if example contains only whole numbers (no fractions or decimals)."""
    return r'\frac{' not in example_text and '.' not in example_text


def get_addition_result(example_text):
    """Extract result from addition (a+b=result or just a+b)."""
    match = re.match(r'(\d+)\+(\d+)', example_text.strip())
    if not match:
        return None
    a, b = int(match.group(1)), int(match.group(2))
    return a + b


def get_subtraction_minuend(example_text):
    """Extract minuend (first operand) from subtraction (a-b)."""
    match = re.match(r'(\d+)-(\d+)', example_text.strip())
    if not match:
        return None
    a = int(match.group(1))
    return a


class Command(BaseCommand):
    help = "Migrate examples to grade 2 skills (Sčítanie do 20, Odčítanie do 20)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        # Get broad skills
        broad_scitani = Skill.objects.filter(name="Sčítání", deleted=False).first()
        broad_odcitani = Skill.objects.filter(name="Odčítání", deleted=False).first()

        # Get target grade 2 skills
        target_scitani = Skill.objects.filter(name="Sčítanie do 20", deleted=False).first()
        target_odcitani = Skill.objects.filter(name="Odčítanie do 20", deleted=False).first()

        migration_summary = {}

        # === SČÍTANIE DO 20 ===
        if broad_scitani and target_scitani:
            self.stdout.write(f"\nProcessing Sčítání → Sčítanie do 20...")

            example_skills = ExampleSkill.objects.filter(skill=broad_scitani)
            total_count = example_skills.count()

            to_migrate = []
            unclassified = []

            for es in example_skills.values('example__id', 'example__example'):
                ex_text = es['example__example'].strip()

                if not is_whole_numbers_only(ex_text):
                    continue

                result = get_addition_result(ex_text)
                if result and 11 <= result <= 20:
                    to_migrate.append(es['example__id'])
                else:
                    unclassified.append((es['example__id'], ex_text))

            self.stdout.write(f"  Total in Sčítání: {total_count}")
            self.stdout.write(f"  → Sčítanie do 20: {len(to_migrate)} examples")
            self.stdout.write(f"  ⚠ Unclassified: {len(unclassified)} examples")

            if len(to_migrate) > 0:
                migration_summary["Sčítanie do 20"] = len(to_migrate)

            if apply_changes and len(to_migrate) > 0:
                with transaction.atomic():
                    for ex_id in to_migrate:
                        ExampleSkill.objects.filter(example__id=ex_id, skill=broad_scitani).update(skill=target_scitani)

        # === ODČÍTANIE DO 20 ===
        if broad_odcitani and target_odcitani:
            self.stdout.write(f"\nProcessing Odčítání → Odčítanie do 20...")

            example_skills = ExampleSkill.objects.filter(skill=broad_odcitani)
            total_count = example_skills.count()

            to_migrate = []
            unclassified = []

            for es in example_skills.values('example__id', 'example__example'):
                ex_text = es['example__example'].strip()

                if not is_whole_numbers_only(ex_text):
                    continue

                minuend = get_subtraction_minuend(ex_text)
                if minuend and 11 <= minuend <= 20:
                    to_migrate.append(es['example__id'])
                else:
                    unclassified.append((es['example__id'], ex_text))

            self.stdout.write(f"  Total in Odčítání: {total_count}")
            self.stdout.write(f"  → Odčítanie do 20: {len(to_migrate)} examples")
            self.stdout.write(f"  ⚠ Unclassified: {len(unclassified)} examples")

            if len(to_migrate) > 0:
                migration_summary["Odčítanie do 20"] = len(to_migrate)

            if apply_changes and len(to_migrate) > 0:
                with transaction.atomic():
                    for ex_id in to_migrate:
                        ExampleSkill.objects.filter(example__id=ex_id, skill=broad_odcitani).update(skill=target_odcitani)

        # Summary
        self.stdout.write("\n" + "=" * 70)
        if migration_summary:
            for skill_name, count in migration_summary.items():
                self.stdout.write(f"  {skill_name}: {count} examples")

        if not apply_changes:
            self.stdout.write("Dry-run only. Re-run with --apply to migrate examples.")
        else:
            self.stdout.write(self.style.SUCCESS("✓ Grade 2 examples migrated successfully."))
