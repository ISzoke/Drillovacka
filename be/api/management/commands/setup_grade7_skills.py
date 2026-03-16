"""
================================================================================
 Module: setup_grade7_skills.py
 Description:
        Creates and assigns a focused set of grade 7 (7. rocnik) drill skills.
        Grade 7 focus:
        - pomery
        - priama umernost
        - nepriama umernost
        - zlomky (pokrocile operacie)
        - plosne/kubicke prevody a litre
        - jednoducha praca s neznamou
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import GradeLevel, Skill


class Command(BaseCommand):
    help = "Prepare grade 7 skills (drill-oriented leaf skills)."

    GRADE_7_SKILLS = [
        {"name": "Pomery", "skill_type": "OPERATION"},
        {"name": "Priama umernost", "skill_type": "OPERATION"},
        {"name": "Nepriama umernost", "skill_type": "OPERATION"},
        {"name": "Zlomky - pokrocile operacie", "skill_type": "OPERATION"},
        {"name": "Plosne, kubicke a litrove prevody", "skill_type": "OPERATION"},
        {"name": "Jednoducha praca s neznamou", "skill_type": "OPERATION"},
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, command runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        grade_7 = GradeLevel.objects.filter(grade=7).first()
        if not grade_7:
            self.stdout.write(self.style.ERROR("Grade 7 does not exist. Run seed_grades first."))
            return

        parent = Skill.objects.filter(name="Operace", deleted=False).first()
        target_names = [item["name"] for item in self.GRADE_7_SKILLS]
        # Backward compatibility: old Czech skill name that should be translated.
        target_names_with_aliases = target_names + ["Poměry"]

        leaf_skills_with_grade7 = Skill.objects.filter(
            deleted=False,
            subskills__isnull=True,
            grade_levels=grade_7,
        ).distinct()
        to_unassign = leaf_skills_with_grade7.exclude(name__in=target_names_with_aliases)

        self.stdout.write("=== Grade 7 setup preview ===")
        self.stdout.write(f"Leaf skills currently assigned to grade 7: {leaf_skills_with_grade7.count()}")
        self.stdout.write(f"Leaf skills to unassign from grade 7: {to_unassign.count()}")

        for skill in to_unassign:
            self.stdout.write(f"  - unassign grade 7: {skill.name} (ID {skill.id})")

        for item in self.GRADE_7_SKILLS:
            existing = Skill.objects.filter(name=item["name"], deleted=False).first()
            if not existing and item["name"] == "Pomery":
                existing = Skill.objects.filter(name="Poměry", deleted=False).first()
            action = "reuse" if existing else "create"
            self.stdout.write(f"  - {action} target skill: {item['name']}")

        if not apply_changes:
            self.stdout.write("\nDry-run only. Re-run with --apply to persist changes.")
            return

        with transaction.atomic():
            for skill in to_unassign:
                skill.grade_levels.remove(grade_7)

            for item in self.GRADE_7_SKILLS:
                skill = Skill.objects.filter(name=item["name"], deleted=False).first()
                if not skill and item["name"] == "Pomery":
                    skill = Skill.objects.filter(name="Poměry", deleted=False).first()
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
                    if skill.name != item["name"]:
                        skill.name = item["name"]
                        updates.append("name")
                    if skill.skill_type != item["skill_type"]:
                        skill.skill_type = item["skill_type"]
                        updates.append("skill_type")
                    if skill.parent_skill is None and parent is not None:
                        skill.parent_skill = parent
                        updates.append("parent_skill")
                    if updates:
                        skill.save(update_fields=updates)

                skill.grade_levels.add(grade_7)

        self.stdout.write(self.style.SUCCESS("\n✓ Grade 7 skills setup applied."))
