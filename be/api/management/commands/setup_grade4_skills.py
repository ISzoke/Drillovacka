"""
================================================================================
 Module: setup_grade4_skills.py
 Description:
        Creates and assigns a focused set of grade 4 (4. ročník) drill skills.
        Grade 4 focus:
        - násobilka (automatizácia)
        - delenie so zvyškom
        - násobenie dvojciferným číslom
        - delenie jednociferným číslom
        - sčítanie a odčítanie do 10 000
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import GradeLevel, Skill


class Command(BaseCommand):
    help = "Prepare grade 4 skills (drill-oriented leaf skills)."

    GRADE_4_SKILLS = [
        {
            "name": "Násobilka do 10×10",
            "skill_type": "OPERATION",
        },
        {
            "name": "Násobenie dvojciferným číslom",
            "skill_type": "OPERATION",
        },
        {
            "name": "Delenie jednociferným číslom",
            "skill_type": "OPERATION",
        },
        {
            "name": "Sčítanie do 10 000",
            "skill_type": "OPERATION",
        },
        {
            "name": "Odčítanie do 10 000",
            "skill_type": "OPERATION",
        },
        {
            "name": "Prevody jednotiek dĺžky II",
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

        grade_4 = GradeLevel.objects.filter(grade=4).first()
        if not grade_4:
            self.stdout.write(self.style.ERROR("Grade 4 does not exist. Run seed_grades first."))
            return

        parent = Skill.objects.filter(name="Operace", deleted=False).first()
        target_names = [item["name"] for item in self.GRADE_4_SKILLS]

        leaf_skills_with_grade4 = Skill.objects.filter(
            deleted=False,
            subskills__isnull=True,
            grade_levels=grade_4,
        ).distinct()
        to_unassign = leaf_skills_with_grade4.exclude(name__in=target_names)

        self.stdout.write("=== Grade 4 setup preview ===")
        self.stdout.write(f"Leaf skills currently assigned to grade 4: {leaf_skills_with_grade4.count()}")
        self.stdout.write(f"Leaf skills to unassign from grade 4: {to_unassign.count()}")

        for skill in to_unassign:
            self.stdout.write(f"  - unassign grade 4: {skill.name} (ID {skill.id})")

        for item in self.GRADE_4_SKILLS:
            existing = Skill.objects.filter(name=item["name"], deleted=False).first()
            action = "reuse" if existing else "create"
            self.stdout.write(f"  - {action} target skill: {item['name']}")

        if not apply_changes:
            self.stdout.write("\nDry-run only. Re-run with --apply to persist changes.")
            return

        with transaction.atomic():
            for skill in to_unassign:
                skill.grade_levels.remove(grade_4)

            for item in self.GRADE_4_SKILLS:
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

                skill.grade_levels.add(grade_4)

        self.stdout.write(self.style.SUCCESS("\n✓ Grade 4 skills setup applied."))
