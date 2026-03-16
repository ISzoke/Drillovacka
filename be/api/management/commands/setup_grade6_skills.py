"""
================================================================================
 Module: setup_grade6_skills.py
 Description:
        Creates and assigns a focused set of grade 6 (6. rocnik) drill skills.
        Grade 6 focus:
        - prirodzene cisla (velke cisla, pisomne pocitanie, porovnavanie)
        - delitelnost a prvocisla
        - rozklad na prvocinitele
        - Najvacsi spolocny delitel (NSD)
        - Najmensi spolocny nasobok (NSN)
        - desatinne cisla (scitanie, odcitanie, nasobenie, delenie)
        - zlomky: scitanie/odcitanie
        - zlomky: nasobenie/delenie
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import GradeLevel, Skill


class Command(BaseCommand):
    help = "Prepare grade 6 skills (drill-oriented leaf skills)."

    GRADE_6_SKILLS = [
        {
            "name": "Prirodzene cisla do milionov",
            "skill_type": "OPERATION",
        },
        {
            "name": "Delitelnost a prvocisla",
            "skill_type": "OPERATION",
        },
        {
            "name": "Rozklad na prvocinitele",
            "skill_type": "OPERATION",
        },
        {
            "name": "Najvacsi spolocny delitel (NSD)",
            "skill_type": "OPERATION",
        },
        {
            "name": "Najmensi spolocny nasobok (NSN)",
            "skill_type": "OPERATION",
        },
        {
            "name": "Desatinne cisla",
            "skill_type": "OPERATION",
        },
        {
            "name": "Zlomky + a -",
            "skill_type": "OPERATION",
        },
        {
            "name": "Zlomky * a :",
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

        grade_6 = GradeLevel.objects.filter(grade=6).first()
        if not grade_6:
            self.stdout.write(self.style.ERROR("Grade 6 does not exist. Run seed_grades first."))
            return

        parent = Skill.objects.filter(name="Operace", deleted=False).first()
        target_names = [item["name"] for item in self.GRADE_6_SKILLS]

        leaf_skills_with_grade6 = Skill.objects.filter(
            deleted=False,
            subskills__isnull=True,
            grade_levels=grade_6,
        ).distinct()
        to_unassign = leaf_skills_with_grade6.exclude(name__in=target_names)

        self.stdout.write("=== Grade 6 setup preview ===")
        self.stdout.write(f"Leaf skills currently assigned to grade 6: {leaf_skills_with_grade6.count()}")
        self.stdout.write(f"Leaf skills to unassign from grade 6: {to_unassign.count()}")

        for skill in to_unassign:
            self.stdout.write(f"  - unassign grade 6: {skill.name} (ID {skill.id})")

        for item in self.GRADE_6_SKILLS:
            existing = Skill.objects.filter(name=item["name"], deleted=False).first()
            action = "reuse" if existing else "create"
            self.stdout.write(f"  - {action} target skill: {item['name']}")

        if not apply_changes:
            self.stdout.write("\nDry-run only. Re-run with --apply to persist changes.")
            return

        with transaction.atomic():
            for skill in to_unassign:
                skill.grade_levels.remove(grade_6)

            for item in self.GRADE_6_SKILLS:
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

                skill.grade_levels.add(grade_6)

        self.stdout.write(self.style.SUCCESS("\n✓ Grade 6 skills setup applied."))
