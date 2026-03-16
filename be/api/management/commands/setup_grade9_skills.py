"""
================================================================================
 Module: setup_grade9_skills.py
 Description:
     Creates and assigns grade 9 (9. rocnik) preparation skills for
     Testovanie 9 categories.
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import GradeLevel, Skill


class Command(BaseCommand):
    help = "Prepare grade 9 skills for Testovanie 9 categories."

    PARENT_SKILL_NAME = "Testovanie 9"
    LEGACY_SET_NAMES = [
        "Testovanie 9 - Set 1: Cisla a operacie",
        "Testovanie 9 - Set 2: Percenta",
        "Testovanie 9 - Set 3: Pomery a umernost",
        "Testovanie 9 - Set 4: Algebra a rovnice",
        "Testovanie 9 - Set 5: Geometria",
        "Testovanie 9 - Set 6: Grafy a tabulky",
        "Testovanie 9 - Set 7: Pravdepodobnost",
        "Testovanie 9 - Set 8: Slovne ulohy",
        "Testovanie 9 - Set 9: Narocnejsie ulohy",
    ]

    GRADE_9_SKILLS = [
        {"name": "Testovanie 9 - Priklady", "skill_type": "OPERATION"},
        {"name": "Testovanie 9 - Slovne ulohy", "skill_type": "OPERATION"},
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, command runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        grade_9 = GradeLevel.objects.filter(grade=9).first()
        if not grade_9:
            self.stdout.write(self.style.ERROR("Grade 9 does not exist. Run seed_grades first."))
            return

        operace_parent = Skill.objects.filter(name="Operace", deleted=False).first()
        target_names = [item["name"] for item in self.GRADE_9_SKILLS]

        leaf_skills_with_grade9 = Skill.objects.filter(
            deleted=False,
            subskills__isnull=True,
            grade_levels=grade_9,
        ).distinct()
        to_unassign = leaf_skills_with_grade9.exclude(name__in=target_names)

        self.stdout.write("=== Grade 9 setup preview ===")
        self.stdout.write(f"Leaf skills currently assigned to grade 9: {leaf_skills_with_grade9.count()}")
        self.stdout.write(f"Leaf skills to unassign from grade 9: {to_unassign.count()}")

        for skill in to_unassign:
            self.stdout.write(f"  - unassign grade 9: {skill.name} (ID {skill.id})")

        existing_parent = Skill.objects.filter(name=self.PARENT_SKILL_NAME, deleted=False).first()
        parent_action = "reuse" if existing_parent else "create"
        self.stdout.write(f"  - {parent_action} parent skill: {self.PARENT_SKILL_NAME}")

        for item in self.GRADE_9_SKILLS:
            existing = Skill.objects.filter(name=item["name"], deleted=False).first()
            action = "reuse" if existing else "create"
            self.stdout.write(f"  - {action} target skill: {item['name']}")

        if not apply_changes:
            self.stdout.write("\nDry-run only. Re-run with --apply to persist changes.")
            return

        with transaction.atomic():
            for skill in to_unassign:
                skill.grade_levels.remove(grade_9)

            # Soft-delete old 9-set structure so only category view remains in UI.
            Skill.objects.filter(name__in=self.LEGACY_SET_NAMES, deleted=False).update(deleted=True)

            testovanie_parent = Skill.objects.filter(name=self.PARENT_SKILL_NAME, deleted=False).first()
            if not testovanie_parent:
                parent_height = operace_parent.height if operace_parent else 0
                testovanie_parent = Skill.objects.create(
                    name=self.PARENT_SKILL_NAME,
                    deleted=False,
                    parent_skill=operace_parent,
                    height=parent_height + 1,
                    skill_type="OPERATION",
                )
            else:
                updates = []
                if testovanie_parent.parent_skill is None and operace_parent is not None:
                    testovanie_parent.parent_skill = operace_parent
                    updates.append("parent_skill")
                if testovanie_parent.skill_type != "OPERATION":
                    testovanie_parent.skill_type = "OPERATION"
                    updates.append("skill_type")
                if updates:
                    testovanie_parent.save(update_fields=updates)

            testovanie_parent.grade_levels.add(grade_9)

            for item in self.GRADE_9_SKILLS:
                skill = Skill.objects.filter(name=item["name"], deleted=False).first()
                if not skill:
                    parent_height = testovanie_parent.height if testovanie_parent else 0
                    skill = Skill.objects.create(
                        name=item["name"],
                        deleted=False,
                        parent_skill=testovanie_parent,
                        height=parent_height + 1,
                        skill_type=item["skill_type"],
                    )
                else:
                    updates = []
                    if skill.skill_type != item["skill_type"]:
                        skill.skill_type = item["skill_type"]
                        updates.append("skill_type")
                    if skill.parent_skill != testovanie_parent:
                        skill.parent_skill = testovanie_parent
                        updates.append("parent_skill")
                    if updates:
                        skill.save(update_fields=updates)

                skill.grade_levels.add(grade_9)

        self.stdout.write(self.style.SUCCESS("\n✓ Grade 9 Testovanie 9 skills setup applied."))
