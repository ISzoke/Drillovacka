"""
Seed a test classroom (on an existing teacher account) full of students that
have realistic practice history, so the teacher analytics / performance
overview screens can be exercised with real-looking data.

The generated data is shaped so these signals are visible:
  - hardest example      : 2 examples per task are systematically failed by most
  - easiest example      : 2 examples per task are almost always solved
  - improving student     : accuracy climbs over the ~21-day window
  - declining student     : accuracy drops over the window
  - error patterns (AI)   : each weaker student has an error bias (off_by_one /
                            sign / carrying / table_confusion) that shapes their
                            wrong answers; also stored in ExampleAttempt.meta

Creates: 1 Classroom, N Students (login <prefix>_NN / <passphrase>),
ClassroomStudent memberships, ClassroomTask assignments (last = homework),
backdated StudentExample + ExampleAttempt rows, and SkillMastery rows built by
replaying the real api.mastery.update_skill_mastery in chronological order.

Re-runnable with --wipe (drops the previously seeded classroom + its <prefix> students).

  python manage.py seed_test_classroom --wipe
  python manage.py seed_test_classroom --students 10 --grade 3 --task-ids 67,68,44,48
"""

import random
import string
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from api.models import (
    Teacher, Classroom, ClassroomStudent, ClassroomTask,
    Student, Task, Example, StudentExample, ExampleAttempt,
)
from api.mastery import update_skill_mastery


FIRST_NAMES = [
    "Adam", "Ema", "Jakub", "Nina", "Samuel", "Sofia", "Michal", "Lucia",
    "Tomáš", "Klára", "Filip", "Zuzka", "Matej", "Hana", "Peter", "Viktória",
]
ERROR_BIASES = ["off_by_one", "sign", "carrying", "table_confusion"]
WINDOW_DAYS = 21


def _rand_code(n=8):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def _wrong_answer(correct, bias, rnd):
    """Produce a plausible wrong answer that reflects `bias`."""
    c = (correct or "").strip()
    try:
        v = int(c)
        if bias == "off_by_one":
            return str(v + rnd.choice([-1, 1]))
        if bias == "sign":
            return str(-v) if v != 0 else "1"
        if bias == "carrying":
            return str(v + rnd.choice([-10, 10, -20, 9, 11]))
        if bias == "table_confusion":
            return str(v + rnd.choice([-3, -2, 2, 3, 6, -6]))
        s = str(abs(v))                       # default: digit transposition
        if len(s) >= 2:
            i = rnd.randrange(len(s) - 1)
            s = s[:i] + s[i + 1] + s[i] + s[i + 2:]
            return ("-" if v < 0 else "") + s
        return str(v + rnd.choice([-2, -1, 1, 2]))
    except ValueError:
        pass
    if "/" in c:
        p = c.split("/")
        try:
            a, b = int(p[0]), int(p[1])
            return f"{-a}/{b}" if bias == "sign" else f"{a + rnd.choice([-1, 1])}/{b}"
        except ValueError:
            pass
    if c and c[-1].isdigit():
        return c[:-1] + str((int(c[-1]) + rnd.choice([1, 2, 8, 9])) % 10)
    return c + rnd.choice(["?", "x", "0"])


class Command(BaseCommand):
    help = "Create a test classroom with students that have realistic practice results (for analytics testing)."

    def add_arguments(self, parser):
        parser.add_argument('--teacher-email', default='martin.it2442@gmail.com')
        parser.add_argument('--classroom-name', default='Testovacia trieda (demo)')
        parser.add_argument('--students', type=int, default=9)
        parser.add_argument('--grade', type=int, default=3)
        parser.add_argument('--task-ids', default='67,68,44,48',
                            help='Comma-separated Task ids to assign & practice')
        parser.add_argument('--passphrase', default='test1234')
        parser.add_argument('--prefix', default='demo_ziak')
        parser.add_argument('--wipe', action='store_true',
                            help='Delete a previously seeded classroom of the same name (+ its <prefix> students) first')

    @transaction.atomic
    def handle(self, *args, **o):
        rnd = random.Random(42)
        now = timezone.now()

        try:
            teacher = Teacher.objects.get(email=o['teacher_email'])
        except Teacher.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f"No teacher with email {o['teacher_email']!r}. "
                f"Existing: {list(Teacher.objects.values_list('email', flat=True))}"))
            return

        prefix, cname = o['prefix'], o['classroom_name']

        if o['wipe']:
            old = Classroom.objects.filter(teacher=teacher, name=cname)
            cnt = old.count()
            for c in old:
                sids = list(ClassroomStudent.objects.filter(classroom=c)
                            .values_list('student_id', flat=True))
                Student.objects.filter(id__in=sids, username__startswith=prefix).delete()
                c.delete()
            self.stdout.write(self.style.WARNING(f"Wiped {cnt} old classroom(s) named {cname!r}."))

        task_ids = [int(x) for x in o['task_ids'].split(',') if x.strip()]
        tasks = list(Task.objects.filter(id__in=task_ids))
        if len(tasks) != len(task_ids):
            found = {t.id for t in tasks}
            self.stderr.write(self.style.ERROR(f"Missing tasks: {[i for i in task_ids if i not in found]}"))
            return
        tasks.sort(key=lambda t: task_ids.index(t.id))

        task_skills, task_examples, ex_difficulty = {}, {}, {}
        for t in tasks:
            sk = list(t.skills.order_by('id').values_list('id', flat=True))
            task_skills[t.id] = sk[-3:] if len(sk) >= 3 else sk
            exs = list(Example.objects.filter(task=t).order_by('id'))
            if not exs:
                self.stderr.write(self.style.ERROR(f"Task {t.id} {t.name!r} has no examples."))
                return
            task_examples[t.id] = exs
            pool = exs[:20]                    # only the first 20 are ever practiced
            hard = set(rnd.sample(range(len(pool)), k=min(2, len(pool))))
            easy = set(rnd.sample([i for i in range(len(pool)) if i not in hard],
                                  k=min(2, max(0, len(pool) - 2))))
            for i, ex in enumerate(pool):
                ex_difficulty[ex.id] = 'hard' if i in hard else 'easy' if i in easy else 'normal'

        code = _rand_code()
        while Classroom.objects.filter(code=code).exists():
            code = _rand_code()
        classroom = Classroom.objects.create(
            teacher=teacher, name=cname, code=code,
            description="Automaticky vytvorená demo trieda na testovanie štatistík.",
        )
        for i, t in enumerate(tasks):
            last = i == len(tasks) - 1
            ClassroomTask.objects.create(
                classroom=classroom, task=t, assigned_by=teacher,
                is_homework=last, due_date=(now + timedelta(days=3)) if last else None,
            )

        n = o['students']
        names = FIRST_NAMES[:]
        rnd.shuffle(names)
        trends = (['improving', 'declining'] * n)[:max(0, n - 3)] + ['steady'] * 3
        rnd.shuffle(trends)

        se_replay = []          # (when, student_id, skill_id, attempt_number, solved, duration)
        made_se = made_att = 0
        summary_rows = []

        for idx in range(1, n + 1):
            username = f"{prefix}_{idx:02d}"
            competence = rnd.uniform(0.42, 0.95)
            slow = rnd.uniform(0.8, 2.0) * (1.6 - competence)
            inactive = idx <= max(1, n // 5)
            trend = 'steady' if inactive else trends[idx - 1]
            bias = rnd.choice(ERROR_BIASES) if competence < 0.8 else 'off_by_one'

            level = 1 + int(competence * 7) + rnd.randint(0, 2)
            student = Student.objects.create(
                username=username, passphrase=make_password(o['passphrase']),
                grade=o['grade'], language='sk',
                total_xp=level * rnd.randint(80, 140), level=level,
                current_streak=0 if inactive else rnd.randint(2, 11),
                longest_streak=rnd.randint(4, 16),
            )
            ClassroomStudent.objects.create(classroom=classroom, student=student)

            latest_when = None
            for t in tasks:
                exs = task_examples[t.id]
                k = rnd.randint(10, min(20, len(exs)))
                for ex in exs[:k]:
                    # place in time: inactive -> all 9..16d ago, else spread across window
                    if inactive:
                        days_ago = rnd.uniform(9, 16)
                    else:
                        days_ago = rnd.uniform(0, WINDOW_DAYS) ** 1.15 / WINDOW_DAYS ** 0.15
                    r = 1.0 - days_ago / WINDOW_DAYS            # 1 = now, 0 = oldest
                    when = now - timedelta(days=days_ago,
                                           seconds=rnd.randint(0, 86399),
                                           microseconds=rnd.randint(0, 999999))

                    comp = competence
                    if trend == 'improving':
                        comp *= 0.55 + 0.6 * r
                    elif trend == 'declining':
                        comp *= 1.15 - 0.6 * r
                    d = ex_difficulty.get(ex.id, 'normal')
                    if d == 'hard':
                        comp *= 0.4
                    elif d == 'easy':
                        comp = min(0.98, comp + 0.3)

                    solved = rnd.random() < max(0.05, min(0.98, comp))
                    if solved:
                        attempt_number = rnd.choices([1, 2, 3], weights=[70, 22, 8])[0]
                        skipped = False
                    else:
                        skipped = rnd.random() < 0.15
                        attempt_number = 1 if skipped else 3
                    per_attempt = int(rnd.uniform(3500, 11000) * slow)
                    duration = per_attempt * attempt_number
                    latest_when = when if latest_when is None else max(latest_when, when)

                    se = StudentExample.objects.create(
                        student=student, example=ex, task=t, duration=duration,
                        attempts=attempt_number, solved=solved, skipped=skipped,
                    )
                    StudentExample.objects.filter(pk=se.pk).update(date=when)
                    se.practiced_skills.set(task_skills[t.id])
                    made_se += 1

                    ans = ex.answers.first()
                    correct_txt = ans.answer if ans else ''
                    for kk in range(1, attempt_number + 1):
                        is_last = kk == attempt_number
                        att_correct = bool(solved and is_last)
                        action = 'skipped' if (skipped and is_last) else 'evaluated'
                        typed = correct_txt if att_correct else _wrong_answer(correct_txt, bias, rnd)
                        a = ExampleAttempt.objects.create(
                            student_example=se, student=student, example=ex,
                            attempt_number=kk, duration=per_attempt,
                            source='text', input_type='keyboard', language='sk',
                            action=action,
                            is_correct=(att_correct if action == 'evaluated' else None),
                            transcription=typed, parsed_answer=typed,
                            example_text=ex.example, correct_answer=correct_txt,
                            meta={} if att_correct else {'seeded': True, 'error_bias': bias},
                        )
                        ExampleAttempt.objects.filter(pk=a.pk).update(
                            created_at=when + timedelta(seconds=kk))
                        made_att += 1

                    for sid in task_skills[t.id]:
                        se_replay.append((when, student.id, sid, attempt_number, solved, duration))

            if latest_when:
                Student.objects.filter(pk=student.pk).update(
                    last_practice_date=latest_when.date())
            summary_rows.append(f"  {username:<14} comp={competence:.2f} trend={trend:<9} "
                                f"bias={bias:<15} {'INACTIVE' if inactive else ''}")

        se_replay.sort(key=lambda x: x[0])
        for _w, sid_student, skill_id, attempt_number, solved, duration in se_replay:
            update_skill_mastery(sid_student, skill_id, attempt_number, solved, duration)

        self.stdout.write(self.style.SUCCESS(
            f"\nTeacher  : {teacher.email} (id {teacher.id})\n"
            f"Classroom: {classroom.name!r}  code={classroom.code}  (id {classroom.id})\n"
            f"Students : {n}   login {prefix}_01 .. {prefix}_{n:02d}   passphrase={o['passphrase']!r}\n"
            f"Tasks    : {', '.join(f'{t.id}:{t.name}' for t in tasks)}   (last = homework)\n"
            f"Created  : {made_se} StudentExample, {made_att} ExampleAttempt, "
            f"{len(set((r[1], r[2]) for r in se_replay))} SkillMastery rows\n"
            + "\n".join(summary_rows) + "\n"))
