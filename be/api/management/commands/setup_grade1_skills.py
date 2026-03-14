"""
================================================================================
 Module: setup_grade1_skills.py
 Description:
        Creates and assigns a focused set of grade 1 (1. ročník) skills.
        Keeps broad parent skills in DB, but limits grade 1 practice skills
        to specific leaf skills.
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import GradeLevel, Skill


class Command(BaseCommand):
    help = "Prepare grade 1 skills (specific leaf skills only)."

    GRADE_1_SKILLS = [
        {
            "name": "Porovnávanie čísel < > =",
            "skill_type": "NUMBER_DOMAIN",
        },
        {
            "name": "Sčítanie do 10",
            "skill_type": "OPERATION",
        },
        {
            "name": "Sčítanie do 20 bez prechodu cez desiatku",
            "skill_type": "OPERATION",
        },
        {
            "name": "Odčítanie do 10",
            "skill_type": "OPERATION",
        },
        {
            "name": "Odčítanie do 20 bez prechodu cez desiatku",
            "skill_type": "OPERATION",
        },
        {
            "name": "Doplňovanie čísla (7 + ? = 10)",
            "skill_type": "OPERATION",
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, command runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        grade_1 = GradeLevel.objects.filter(grade=1).first()
        if not grade_1:
            self.stdout.write(self.style.ERROR("Grade 1 does not exist. Run seed_grades first."))
            return

        parent = Skill.objects.filter(name="Operace", deleted=False).first()
        target_names = [item["name"] for item in self.GRADE_1_SKILLS]

        leaf_skills_with_grade1 = Skill.objects.filter(
            deleted=False,
            subskills__isnull=True,
            grade_levels=grade_1,
        ).distinct()

        to_unassign = leaf_skills_with_grade1.exclude(name__in=target_names)

        self.stdout.write("=== Grade 1 setup preview ===")
        self.stdout.write(f"Leaf skills currently assigned to grade 1: {leaf_skills_with_grade1.count()}")
        self.stdout.write(f"Leaf skills to unassign from grade 1: {to_unassign.count()}")

        for skill in to_unassign:
            self.stdout.write(f"  - unassign grade 1: {skill.name} (ID {skill.id})")

        for item in self.GRADE_1_SKILLS:
            existing = Skill.objects.filter(name=item["name"], deleted=False).first()
            action = "reuse" if existing else "create"
            self.stdout.write(f"  - {action} target skill: {item['name']}")

        if not apply_changes:
            self.stdout.write("\nDry-run only. Re-run with --apply to persist changes.")
            return

        with transaction.atomic():
            for skill in to_unassign:
                skill.grade_levels.remove(grade_1)

            for item in self.GRADE_1_SKILLS:
                skill = Skill.objects.filter(name=item["name"], deleted=False).first()
                if not skill:
                    parent_height = parent.height if parent else 0
                    skill = Skill.objects.create(
                        name=item["name"],
                        deleted=False,
                        parent_skill=parent,
                        height=parent_height + 1,
                        skill_type=item["skill_type"],
                    )
                else:
                    updates = []
                    if skill.skill_type != item["skill_type"]:
                        skill.skill_type = item["skill_type"]
                        updates.append("skill_type")
                    if skill.parent_skill is None and parent is not None:
                        skill.parent_skill = parent
                        updates.append("parent_skill")
                    if updates:
                        skill.save(update_fields=updates)

                skill.grade_levels.add(grade_1)

        self.stdout.write(self.style.SUCCESS("\n✓ Grade 1 skills setup applied."))
