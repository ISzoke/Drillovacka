"""
================================================================================
 Module: badge_checker.py
 Description:
        Checks badge conditions after each correct attempt and awards new badges.
================================================================================
"""

from datetime import date


def check_badges(student, attempt):
    """
    Check all badge conditions for the given student after a correct attempt.
    Creates StudentBadge records for any newly earned badges.
    Returns a list of newly earned badge keys.
    attempt may be None (text answers without a saved attempt object).
    """
    from .models import Badge, StudentBadge, ExampleAttempt, StudentExample

    new_badges = []
    existing_keys = set(
        StudentBadge.objects.filter(student=student).values_list('badge__key', flat=True)
    )

    def try_award(key):
        if key not in existing_keys:
            try:
                badge = Badge.objects.get(key=key)
                StudentBadge.objects.create(student=student, badge=badge)
                new_badges.append(key)
                existing_keys.add(key)
            except Badge.DoesNotExist:
                pass
            except Exception:
                pass

    # ── Activity: correct answer counts ──────────────────────────────────────
    total_correct = ExampleAttempt.objects.filter(student=student, is_correct=True).count()

    if total_correct >= 1:
        try_award('first_correct')
    if total_correct >= 25:
        try_award('ten_correct')          # key kept for backwards compat, threshold raised
    if total_correct >= 100:
        try_award('hundred_correct')
    if total_correct >= 300:
        try_award('three_hundred_correct')
    if total_correct >= 500:
        try_award('five_hundred_correct')
    if total_correct >= 1000:
        try_award('thousand_correct')

    # ── Activity: skill variety ───────────────────────────────────────────────
    needs_skill_check = not {'five_skills', 'ten_skills', 'twenty_skills'}.issubset(existing_keys)
    if needs_skill_check:
        skill_count = (
            StudentExample.objects
            .filter(student=student)
            .values_list('practiced_skills', flat=True)
            .exclude(practiced_skills=None)
            .distinct()
            .count()
        )
        if skill_count >= 5:
            try_award('five_skills')
        if skill_count >= 10:
            try_award('ten_skills')
        if skill_count >= 20:
            try_award('twenty_skills')

    # ── Streak ────────────────────────────────────────────────────────────────
    if student.current_streak >= 3:
        try_award('streak_3')
    if student.current_streak >= 7:
        try_award('streak_7')
    if student.current_streak >= 14:
        try_award('streak_14')
    if student.current_streak >= 30:
        try_award('streak_30')

    # ── Level milestones ──────────────────────────────────────────────────────
    if student.level >= 5:
        try_award('level_5')
    if student.level >= 10:
        try_award('level_10')
    if student.level >= 20:
        try_award('level_20')

    # ── Speed: individual answer times (only if we have attempt data) ─────────
    if attempt and attempt.duration and attempt.duration > 0:
        if attempt.duration < 5000:
            fast_count = ExampleAttempt.objects.filter(
                student=student, is_correct=True, duration__gt=0, duration__lt=5000
            ).count()
            if fast_count >= 10:
                try_award('fast_answer')

        if attempt.duration < 3000:
            lightning_count = ExampleAttempt.objects.filter(
                student=student, is_correct=True, duration__gt=0, duration__lt=3000
            ).count()
            if lightning_count >= 10:
                try_award('lightning')
            if lightning_count >= 25:
                try_award('speed_demon')

    # ── Speed session: 10 correct today with total duration < 90 s ───────────
    if 'speed_session' not in existing_keys:
        today_attempts = list(
            ExampleAttempt.objects.filter(
                student=student,
                is_correct=True,
                action='evaluated',
                created_at__date=date.today(),
                duration__gt=0,
            ).order_by('-created_at')[:10]
        )
        if len(today_attempts) >= 10 and sum(a.duration for a in today_attempts) < 90000:
            try_award('speed_session')

    # ── Accuracy master / legend ──────────────────────────────────────────────
    needs_accuracy = not {'accuracy_master', 'accuracy_legend'}.issubset(existing_keys)
    if needs_accuracy:
        total_eval = ExampleAttempt.objects.filter(
            student=student, action='evaluated', is_correct__isnull=False
        ).count()
        if total_eval >= 100:
            accuracy = total_correct / total_eval
            if accuracy >= 0.9:
                try_award('accuracy_master')
        if total_eval >= 250:
            accuracy = total_correct / total_eval
            if accuracy >= 0.95:
                try_award('accuracy_legend')

    # ── Ten / twenty-five in a row ────────────────────────────────────────────
    needs_row = not {'ten_in_a_row', 'twenty_five_in_a_row'}.issubset(existing_keys)
    if needs_row:
        recent = list(
            ExampleAttempt.objects.filter(
                student=student, action='evaluated', is_correct__isnull=False
            ).order_by('-created_at')[:25]
        )
        if len(recent) >= 10 and all(a.is_correct for a in recent[:10]):
            try_award('ten_in_a_row')
        if len(recent) >= 25 and all(a.is_correct for a in recent):
            try_award('twenty_five_in_a_row')

    # ── Mastery: any skill at 85%+ (min 20 examples) ─────────────────────────
    if 'mastery_skill' not in existing_keys:
        practiced_skill_ids = (
            StudentExample.objects
            .filter(student=student)
            .values_list('practiced_skills', flat=True)
            .exclude(practiced_skills=None)
            .distinct()
        )
        for skill_id in practiced_skill_ids:
            ses = StudentExample.objects.filter(student=student, practiced_skills=skill_id)
            total_s = ses.count()
            if total_s >= 20:
                solved_s = ses.filter(solved=True).count()
                if solved_s / total_s >= 0.85:
                    try_award('mastery_skill')
                    break

    # ── Comeback: correct after 3+ wrong on same example ─────────────────────
    if attempt and attempt.is_correct and 'comeback' not in existing_keys:
        prev_wrong = ExampleAttempt.objects.filter(
            student=student,
            example=attempt.example,
            is_correct=False,
        ).count()
        if prev_wrong >= 3:
            try_award('comeback')

    # ── Perfect session: all of today's examples solved (min 10) ─────────────
    if 'perfect_session' not in existing_keys:
        today_ses = StudentExample.objects.filter(student=student, date__date=date.today())
        total_today = today_ses.count()
        if total_today >= 10 and today_ses.filter(solved=True).count() == total_today:
            try_award('perfect_session')

    # ── Voice answer badges ─────────────────────────────────────────────────
    needs_voice = not {'voice_first', 'voice_10', 'voice_50', 'voice_100', 'voice_250'}.issubset(existing_keys)
    if needs_voice and attempt and attempt.source == 'speech':
        voice_correct = ExampleAttempt.objects.filter(
            student=student, is_correct=True, source='speech'
        ).count()
        if voice_correct >= 1:
            try_award('voice_first')
        if voice_correct >= 10:
            try_award('voice_10')
        if voice_correct >= 50:
            try_award('voice_50')
        if voice_correct >= 100:
            try_award('voice_100')
        if voice_correct >= 250:
            try_award('voice_250')

    # ── Leaderboard rank ──────────────────────────────────────────────────────
    needs_lb = not {'top10_leaderboard', 'top3_leaderboard'}.issubset(existing_keys)
    if needs_lb:
        from .models import Student
        rank = Student.objects.filter(total_xp__gt=student.total_xp).count() + 1
        if rank <= 10:
            try_award('top10_leaderboard')
        if rank <= 3:
            try_award('top3_leaderboard')

    return new_badges
