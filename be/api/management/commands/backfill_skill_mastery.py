"""
Backfills SkillMastery from existing StudentExample records.

Only task-based examples (task__isnull=False) for registered students are used.
Skills come from Task.skills (leaf skills only), matching the live update logic.

Run:
    python manage.py backfill_skill_mastery
    python manage.py backfill_skill_mastery --dry-run
    python manage.py backfill_skill_mastery --reset   # clears existing rows before rebuild
"""

from django.core.management.base import BaseCommand
from api.models import StudentExample, SkillMastery
from api.mastery import ALPHA_A, ALPHA_F, F_CLAMP_MIN, MEDIAN_SAMPLE_SIZE, _accuracy_response


class Command(BaseCommand):
    help = 'Backfill SkillMastery from historical StudentExample data (task-based, registered students only)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be written without saving')
        parser.add_argument('--reset', action='store_true', help='Delete all existing SkillMastery rows before backfilling')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        reset = options['reset']

        if reset and not dry_run:
            deleted, _ = SkillMastery.objects.all().delete()
            self.stdout.write(f'Deleted {deleted} existing SkillMastery rows.')

        # ── Precompute median duration per skill (task-based solved examples) ──
        self.stdout.write('Precomputing median times per skill...')
        from collections import defaultdict
        import statistics

        skill_durations = defaultdict(list)
        solved_examples = (
            StudentExample.objects
            .filter(solved=True, task__isnull=False, student__isnull=False)
            .prefetch_related('task__skills')
            .values('duration', 'task__skills__id', 'task__skills__deleted',
                    'task__skills__subskills')
        )
        # Efficient: gather durations per skill from task skills
        raw = list(
            StudentExample.objects
            .filter(solved=True, task__isnull=False, student__isnull=False)
            .prefetch_related('task__skills')
            .order_by('-date')[:MEDIAN_SAMPLE_SIZE * 50]   # broad sample cap
            .values('duration', 'task_id')
        )

        # Build skill→durations via task skills queryset
        from api.models import Task, Skill
        task_leaf_skills = {}   # task_id -> [skill_id, ...]
        task_ids = {r['task_id'] for r in raw}
        for task in Task.objects.filter(id__in=task_ids).prefetch_related('skills'):
            task_leaf_skills[task.id] = list(
                task.skills.filter(subskills__isnull=True, deleted=False).values_list('id', flat=True)
            )

        for r in raw:
            for skill_id in task_leaf_skills.get(r['task_id'], []):
                skill_durations[skill_id].append(r['duration'])

        precomputed_medians = {}
        for skill_id, durations in skill_durations.items():
            if durations:
                precomputed_medians[skill_id] = statistics.median(durations)

        self.stdout.write(f'Median times computed for {len(precomputed_medians)} skills.')

        # ── Fetch all relevant StudentExample records in chronological order ──
        records = list(
            StudentExample.objects
            .filter(task__isnull=False, student__isnull=False, skipped=False, attempts__gt=0)
            .select_related('student', 'task')
            .prefetch_related('task__skills')
            .order_by('date')
        )
        self.stdout.write(f'Processing {len(records)} StudentExample records...')

        # ── Run EWMA in memory ──────────────────────────────────────────────
        mastery_state = {}   # (student_id, skill_id) -> {'A': float, 'F': float, 'n': int}

        for record in records:
            # Reuse the already-computed task_leaf_skills dict (no extra DB queries)
            leaf_skill_ids_for_record = task_leaf_skills.get(record.task_id, [])

            for skill_id in leaf_skill_ids_for_record:
                key = (record.student_id, skill_id)
                if key not in mastery_state:
                    mastery_state[key] = {'A': 0.05, 'F': 0.50, 'n': 0}

                state = mastery_state[key]
                r_a = _accuracy_response(record.attempts, record.solved)
                state['A'] += ALPHA_A * (r_a - state['A'])

                if record.solved and record.duration and record.duration > 0:
                    median_time = precomputed_medians.get(skill_id)
                    if median_time:
                        r_f = max(F_CLAMP_MIN, min(1.0, median_time / record.duration))
                        state['F'] += ALPHA_F * (r_f - state['F'])

                state['n'] += 1

        self.stdout.write(f'Computed mastery for {len(mastery_state)} (student, skill) pairs.')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — nothing saved.'))
            for (student_id, skill_id), state in list(mastery_state.items())[:10]:
                raw = 0.65 * state['A'] + 0.35 * state['F']
                conf = state['n'] / (state['n'] + 4)
                self.stdout.write(
                    f'  student={student_id} skill={skill_id} '
                    f"A={state['A']:.3f} F={state['F']:.3f} n={state['n']} "
                    f'final={raw * conf:.3f}'
                )
            return

        # ── Bulk upsert ─────────────────────────────────────────────────────
        to_upsert = [
            SkillMastery(
                student_id=student_id,
                skill_id=skill_id,
                accuracy_mastery=state['A'],
                fluency_mastery=state['F'],
                example_count=state['n'],
            )
            for (student_id, skill_id), state in mastery_state.items()
        ]

        # MySQL bulk upsert: update_conflicts without unique_fields uses ON DUPLICATE KEY UPDATE
        SkillMastery.objects.bulk_create(
            to_upsert,
            update_conflicts=True,
            update_fields=['accuracy_mastery', 'fluency_mastery', 'example_count', 'updated_at'],
        )
        self.stdout.write(self.style.SUCCESS(f'Done. Upserted {len(to_upsert)} SkillMastery rows.'))
