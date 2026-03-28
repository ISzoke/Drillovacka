"""
Management command: propagate grade levels from Skills to Tasks.

For each Task that has linked Skills, unions the grade_levels of all
those Skills and assigns them directly to the Task (additive, idempotent).

Run once after the initial deploy; safe to re-run at any time.
"""

from django.core.management.base import BaseCommand
from api.models import Task, GradeLevel


class Command(BaseCommand):
    help = "Propagate grade_levels from linked Skills to Tasks that have none."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]

        tasks = Task.objects.prefetch_related("skills__grade_levels", "grade_levels").all()

        updated = 0
        already_had = 0
        no_skills = 0

        for task in tasks:
            # Collect leaf skills from task.skills AND from ExampleSkill on the task's examples
            # This handles both direct task→skill links and example-level skill links
            from api.models import ExampleSkill as ES
            leaf_skill_ids = set()

            # From task.skills (leaf only)
            for s in task.skills.filter(subskills__isnull=True, deleted=False):
                leaf_skill_ids.add(s.id)

            # From examples → ExampleSkill (leaf only)
            ex_ids = task.example_set.values_list('id', flat=True)
            for es in ES.objects.filter(example_id__in=ex_ids).select_related('skill'):
                s = es.skill
                if not s.deleted and not s.subskills.exists():
                    leaf_skill_ids.add(s.id)

            if not leaf_skill_ids:
                no_skills += 1
                continue

            # Union of grade_levels from all found leaf skills
            from api.models import Skill as S
            grade_ids = set()
            for skill in S.objects.filter(id__in=leaf_skill_ids).prefetch_related('grade_levels'):
                for gl in skill.grade_levels.all():
                    grade_ids.add(gl.id)

            if not grade_ids:
                no_skills += 1
                continue

            existing_ids = set(task.grade_levels.values_list("id", flat=True))
            new_ids = grade_ids - existing_ids

            if existing_ids:
                already_had += 1

            if new_ids:
                grades = GradeLevel.objects.filter(id__in=new_ids)
                grade_nums = sorted(g.grade for g in grades)
                self.stdout.write(
                    f"  {'[DRY]' if not apply else '[ADD]'} \"{task.name}\" "
                    f"← grades {grade_nums}"
                )
                if apply:
                    task.grade_levels.add(*grades)
                updated += 1
            else:
                self.stdout.write(f"  [SKIP] \"{task.name}\" — already has all grades")

        self.stdout.write("\n" + "=" * 60)
        if apply:
            self.stdout.write(self.style.SUCCESS(
                f"Done. Updated: {updated}  |  Already complete: {already_had}  |  No skills: {no_skills}"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Dry-run. Would update: {updated}  |  Already complete: {already_had}  |  No skills: {no_skills}"
            ))
            self.stdout.write("Re-run with --apply to make changes.")
