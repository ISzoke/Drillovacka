"""
================================================================================
 Module: xp_service.py
 Description:
        Awards XP to students after correct answers.

        Formula:
            final_xp = round(BASE_XP * grade_multiplier) + voice_bonus

        Grade multiplier:
            same grade  → 1.0x
            lower grade → 0.5x  (student is doing easier work)
            higher grade → 1.5x (student is doing harder work)

        Voice bonus: +5 XP when answer was submitted by speech.

        Updates student.total_xp, level, streak and triggers badge checks.
        Returns a dict with gamification fields to merge into the API response,
        including an xp_breakdown for UI display.
================================================================================
"""

import math
from datetime import date, timedelta

BASE_XP = 10
VOICE_BONUS = 5


def _get_example_grade(attempt):
    """Return the lowest grade level of the example's task, or None."""
    if not attempt:
        return None
    try:
        grades = list(
            attempt.example.task.grade_levels.values_list('grade', flat=True)
        )
        return min(grades) if grades else None
    except Exception:
        return None


def _grade_multiplier(student_grade, example_grade):
    """Return (multiplier, comparison_label) for the grade pair."""
    if student_grade is None or example_grade is None:
        return 1.0, 'same'
    if example_grade < student_grade:
        return 0.5, 'lower'
    if example_grade > student_grade:
        return 1.5, 'higher'
    return 1.0, 'same'


def award_xp(student_id, attempt):
    """
    Award XP after a correct answer.
    Updates student.total_xp, level, streak.
    Returns a dict with gamification fields to merge into the response.
    attempt may be None (text answers without a saved attempt object).
    """
    from .models import Student, Badge
    from .badge_checker import check_badges
    from django.db.models import Sum

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return {}

    # --- Grade multiplier ---
    example_grade = _get_example_grade(attempt)
    multiplier, grade_comparison = _grade_multiplier(student.grade, example_grade)

    # --- Voice bonus ---
    is_voice = bool(attempt and attempt.source == 'speech')
    voice_bonus = VOICE_BONUS if is_voice else 0

    # --- Final XP ---
    xp_gained = round(BASE_XP * multiplier) + voice_bonus

    # --- Update streak ---
    today = date.today()
    last = student.last_practice_date

    if last is None or last < today - timedelta(days=1):
        student.current_streak = 1
    elif last == today - timedelta(days=1):
        student.current_streak += 1
    # elif last == today: unchanged — already practiced today

    student.longest_streak = max(student.longest_streak, student.current_streak)
    student.last_practice_date = today

    # --- Update XP & level ---
    student.total_xp += xp_gained
    student.level = math.floor(math.sqrt(student.total_xp / 50)) + 1

    student.save(update_fields=[
        'total_xp', 'level', 'current_streak', 'longest_streak', 'last_practice_date'
    ])

    # --- Check badges ---
    new_badge_keys = check_badges(student, attempt)

    # Add XP rewards from newly earned badges
    if new_badge_keys:
        badge_xp = Badge.objects.filter(key__in=new_badge_keys).aggregate(
            total=Sum('xp_reward')
        )['total'] or 0
        if badge_xp:
            student.total_xp += badge_xp
            student.level = math.floor(math.sqrt(student.total_xp / 50)) + 1
            student.save(update_fields=['total_xp', 'level'])

    # --- Store breakdown in attempt meta ---
    if attempt:
        try:
            if not isinstance(attempt.meta, dict):
                attempt.meta = {}
            attempt.meta['xp_breakdown'] = {
                'base': BASE_XP,
                'multiplier': multiplier,
                'voice_bonus': voice_bonus,
                'grade_comparison': grade_comparison,
                'example_grade': example_grade,
                'student_grade': student.grade,
                'total': xp_gained,
            }
            attempt.save(update_fields=['meta'])
        except Exception:
            pass

    return {
        'xp_awarded': xp_gained,
        'xp_breakdown': {
            'base': BASE_XP,
            'multiplier': multiplier,
            'voice_bonus': voice_bonus,
            'grade_comparison': grade_comparison,
            'example_grade': example_grade,
            'student_grade': student.grade,
        },
        'new_badges': new_badge_keys,
        'total_xp': student.total_xp,
        'level': student.level,
        'streak': student.current_streak,
    }
