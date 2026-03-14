"""
================================================================================
 Module: setup_grade2_skills.py
 Description:
        Creates grade 2 (2. ročník) skills:
        - Sčítanie do 20 (all results from 11-20, including carry)
        - Odčítanie do 20 (all results with minuend 11-20, including borrow)
        
        Only whole numbers, excludes fractions (\frac{) and decimals (.).
================================================================================
"""

import re
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import GradeLevel, Skill, ExampleSkill


class Command(BaseCommand):
    help = "Setup grade 2 skills (Sčítanie do 20, Odčítanie do 20)."

    GRADE_2_SKILLS = [
        {
            "name": "Sčítanie do 20",
            "skill_type": "OPERATION",
        },
        {
            "name": "Odčítanie do 20",
            "skill_type": "OPERATION",
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        grade_2 = GradeLevel.objects.filter(grade=2).first()
        if not grade_2:
            self.stdout.write(self.style.ERROR("Grade 2 does not exist. Run seed_grades first."))
            return

        parent = Skill.objects.filter(name="Operace", deleted=False).first()

        self.stdout.write("=== Grade 2 setup preview ===")

        # Process each skill
        for item in self.GRADE_2_SKILLS:
            target_skill, created = Skill.objects.get_or_create(
                name=item["name"],
                deleted=False,
                defaults={
                    "skill_type": item["skill_type"],
                    "parent_skill": parent,
                    "height": (parent.height if parent else 0) + 1,
                }
            )

            action = "created" if created else "reused"
            self.stdout.write(f"  {action}: {item['name']} (ID {target_skill.id})")

            # Assign to grade 2
            target_skill.grade_levels.add(grade_2)

        if not apply_changes:
            self.stdout.write("\nDry-run only. Re-run with --apply to persist changes.")
            return

        with transaction.atomic():
            for item in self.GRADE_2_SKILLS:
                skill = Skill.objects.get(name=item["name"], deleted=False)
                skill.grade_levels.add(grade_2)

        self.stdout.write(self.style.SUCCESS("\n✓ Grade 2 skills setup applied."))
