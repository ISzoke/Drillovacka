"""
================================================================================
 Module: mastery.py
 Description:
        Incremental skill mastery tracking using an EWMA model.
        Tracks accuracy (A) and fluency (F) per student per skill.
        Final mastery = (0.65·A + 0.35·F) × confidence(n).
================================================================================
"""

from .models import SkillMastery, StudentExample

# ── EWMA learning rates ──────────────────────────────────────────────────────
ALPHA_A = 0.10   # accuracy update rate
ALPHA_F = 0.08   # fluency update rate

# ── Mastery aggregation weights ──────────────────────────────────────────────
W_A = 0.65       # weight of accuracy component
W_F = 0.35       # weight of fluency component

# ── Confidence formula: confidence = n / (n + K_CONF) ───────────────────────
K_CONF = 4

# ── Fluency response bounds ──────────────────────────────────────────────────
F_CLAMP_MIN = 0.20   # floor: very slow students are not fully penalised

# ── Median time: how many recent solved examples to sample per skill ─────────
MEDIAN_SAMPLE_SIZE = 200

# ── Accuracy response by attempt number (only when solved) ───────────────────
_ACCURACY_RESPONSE = {1: 1.00, 2: 0.65, 3: 0.35}


def _accuracy_response(attempt_number: int, solved: bool) -> float:
    if not solved:
        return 0.0
    return _ACCURACY_RESPONSE.get(attempt_number, 0.35)


def _get_median_time(skill_id: int) -> float | None:
    """
    Returns median StudentExample.duration (ms) over the last MEDIAN_SAMPLE_SIZE
    solved task-based examples for this skill (via task's skill M2M), across all registered students.
    Returns None if no data is available yet.
    """
    durations = list(
        StudentExample.objects
        .filter(
            solved=True,
            task__isnull=False,
            task__skills__id=skill_id,
            student__isnull=False,
        )
        .order_by('-date')
        .values_list('duration', flat=True)[:MEDIAN_SAMPLE_SIZE]
    )
    if not durations:
        return None
    durations.sort()
    mid = len(durations) // 2
    if len(durations) % 2 == 0:
        return (durations[mid - 1] + durations[mid]) / 2.0
    return float(durations[mid])


def compute_final_mastery(obj: SkillMastery) -> dict:
    """
    Compute the current mastery output from a SkillMastery object.
    Does NOT modify the object.
    """
    raw  = W_A * obj.accuracy_mastery + W_F * obj.fluency_mastery
    n    = obj.example_count
    conf = n / (n + K_CONF) if n > 0 else 0.0
    return {
        'accuracy_mastery': round(obj.accuracy_mastery, 4),
        'fluency_mastery':  round(obj.fluency_mastery, 4),
        'example_count':    n,
        'raw_mastery':      round(raw, 4),
        'confidence':       round(conf, 4),
        'final_mastery':    round(raw * conf, 4),
    }


def update_skill_mastery(
    student_id: int,
    skill_id: int,
    attempt_number: int,
    solved: bool,
    student_time_ms: int,
) -> dict:
    """
    Incrementally update mastery state for a student/skill pair after one
    completed example (solved or exhausted all 3 attempts).

    - Always updates accuracy_mastery.
    - Only updates fluency_mastery when solved=True and timing data is available.
    - Increments example_count.
    - Returns the new compute_final_mastery() dict.
    """
    obj, _ = SkillMastery.objects.get_or_create(
        student_id=student_id,
        skill_id=skill_id,
        defaults={
            'accuracy_mastery': 0.05,
            'fluency_mastery':  0.50,
            'example_count':    0,
        },
    )

    r_a = _accuracy_response(attempt_number, solved)
    obj.accuracy_mastery += ALPHA_A * (r_a - obj.accuracy_mastery)

    if solved and student_time_ms and student_time_ms > 0:
        median_time = _get_median_time(skill_id)
        if median_time:
            r_f = max(F_CLAMP_MIN, min(1.0, median_time / student_time_ms))
            obj.fluency_mastery += ALPHA_F * (r_f - obj.fluency_mastery)

    obj.example_count += 1
    obj.save()

    return compute_final_mastery(obj)
