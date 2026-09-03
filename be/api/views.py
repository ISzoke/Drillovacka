"""
================================================================================
 Module: views.py
 Description:
        Contains API views that serve the frontend with data manipulation functionality.
        It includes CRUD operations for tasks, examples, skills, and student records.
        It also handles user authentication and answer checking.

 Author: Dominik Horut (xhorut01)
================================================================================
"""

from rest_framework import generics
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.hashers import make_password, check_password
from django.http import JsonResponse, FileResponse
from django.db import transaction
from django.db.models import Count, Sum, Avg, Max, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
import math
import shutil
from .models import Task, Example, Answer, Student, Skill, ExampleSkill, StudentExample, ExampleAttempt, ExampleReport, SurveyFeedback, Admin, Step, GradeLevel, AnonymousSession, ExampleRequest, GeneratedTaskBatch, GeneratedTaskBatchSurvey, Teacher, Classroom, ClassroomStudent, ClassroomTask, SkillMastery, DuelGame, DuelParticipant, QuizGame, QuizParticipant, QuizAnswer, StudentInsight
from .serializers import ExampleSerializer, SkillSerializer, RecordInitSerializer, ExampleAttemptSerializer
from .utils import get_height, build_skill_tree, get_skill_paths, get_skill_names_string_sync
from .answerChecker import InlineAnswerChecker, FractionAnswerChecker, VariableAnswerChecker
from .example_report_cloud_sync import retry_pending_report_uploads, sync_report_to_mega
from .attempt_cloud_sync import ensure_attempt_sidecar, sync_write_attempt_to_mega, retry_pending_write_uploads
from .mega_cloud import download_file_from_mega_to_temp
from .survey_feedback_sync import create_survey_feedback, retry_pending_survey_feedback_uploads, sync_survey_feedback_to_mega
import json
import csv
import io
import random
import threading
from datetime import datetime
import uuid
import os
import json as pyjson
import logging
from django.core.mail import EmailMessage
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

# Helper function to get student or anonymous session from request
def get_user_identity(request):
    """
    Returns (student_obj, anonymous_session_obj) tuple.
    One will be None, the other will have a value.
    """
    student_id = request.data.get('student_id')
    session_id = request.data.get('session_id')
    
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            return (student, None)
        except Student.DoesNotExist:
            return (None, None)
    elif session_id:
        try:
            session = AnonymousSession.objects.get(session_id=session_id)
            return (None, session)
        except AnonymousSession.DoesNotExist:
            return (None, None)

def get_user_identity_any(request):
    """Like get_user_identity but also checks query_params (for GET requests)."""
    student_id = request.data.get('student_id') or request.query_params.get('student_id')
    session_id = request.data.get('session_id') or request.query_params.get('session_id')
    if student_id:
        try:
            return (Student.objects.get(id=student_id), None)
        except Student.DoesNotExist:
            return (None, None)
    elif session_id:
        try:
            return (None, AnonymousSession.objects.get(session_id=session_id))
        except AnonymousSession.DoesNotExist:
            return (None, None)
    return (None, None)
    
    return (None, None)


def _serialize_attempt_answer(value):
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        return pyjson.dumps(value, ensure_ascii=False)
    return str(value)


def _existing_nonempty_file(path):
    return bool(path) and os.path.exists(path) and os.path.isfile(path) and os.path.getsize(path) > 0


class _DeleteOnCloseFile:
    def __init__(self, path, temp_dir=""):
        self._file = open(path, "rb")
        self._path = path
        self._temp_dir = temp_dir

    def __getattr__(self, attr):
        return getattr(self._file, attr)

    def close(self):
        try:
            self._file.close()
        finally:
            try:
                if self._path and os.path.exists(self._path):
                    os.remove(self._path)
            except Exception:
                pass

            try:
                if self._temp_dir and os.path.isdir(self._temp_dir):
                    shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:
                pass


def _temporary_cloud_file_response(public_url, filename_hint, content_type):
    downloaded = download_file_from_mega_to_temp(public_url, filename_hint=filename_hint)
    downloaded_path = downloaded.get("path", "")
    temp_dir = downloaded.get("temp_dir", "")

    if not downloaded.get("downloaded") or not _existing_nonempty_file(downloaded_path):
        try:
            if temp_dir and os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        return None

    return FileResponse(
        _DeleteOnCloseFile(downloaded_path, temp_dir=temp_dir),
        content_type=content_type,
    )


def _resolve_student_example_record(student_id, session_id, example_id, date):
    records = StudentExample.objects.prefetch_related('practiced_skills').filter(
        example_id=example_id,
        date=date,
    )

    if student_id:
        records = records.filter(student_id=student_id)
    elif session_id:
        records = records.filter(anonymous_session__session_id=session_id)
    else:
        return None

    return records.first()


def _create_attempt_log_for_record(
    student_example,
    example_id,
    duration,
    input_type,
    language,
    action,
    is_correct,
    transcription,
    parsed_answer,
    example_text,
    correct_answer,
    source='text',
    audio_file_path='',
    audio_format='',
    meta=None,
):
    skill_ids = list(student_example.practiced_skills.values_list('id', flat=True))
    if not skill_ids:
        skill_ids = list(
            ExampleSkill.objects.filter(example_id=example_id).values_list('skill_id', flat=True).distinct()
        )

    skill_names = list(Skill.objects.filter(id__in=skill_ids).values_list('name', flat=True))

    attempt = ExampleAttempt.objects.create(
        student_example=student_example,
        student=student_example.student,
        anonymous_session=student_example.anonymous_session,
        example_id=example_id,
        attempt_number=max(student_example.attempts, 1),
        duration=duration or 0,
        source=source,
        input_type=input_type or '',
        language=language or '',
        action=action,
        is_correct=is_correct,
        transcription=transcription or '',
        parsed_answer=_serialize_attempt_answer(parsed_answer),
        example_text=example_text or '',
        correct_answer=correct_answer or '',
        audio_file_path=audio_file_path or '',
        audio_format=audio_format or '',
        practiced_skill_ids=skill_ids,
        practiced_skill_names=skill_names,
        meta=meta or {},
    )
    return attempt

# Add all skill_ids to the related_skills field of each skill
def create_skill_relations(skill_ids):

    skills = Skill.objects.filter(id__in=skill_ids)

    for skill in skills:
        related_skills = [s for s in skills if s != skill and s.skill_type != skill.skill_type]
        skill.related_skills.add(*related_skills)  

# Creates a new task and its examples
@api_view(['POST'])
def create_task(request):
    task_name = request.data.get('task_name')
    task_form = request.data.get('task_form')
    grade_level_ids = request.data.get('grade_level_ids', [])
    examples_data = request.data.get('examples', [])

    if not task_name:
        return Response({"error": "Nebyl zadán název sady"}, status=status.HTTP_400_BAD_REQUEST)

    if not grade_level_ids:
        return Response({"error": "Nebyl vybrán žádný ročník"}, status=status.HTTP_400_BAD_REQUEST)

    grade_levels = GradeLevel.objects.filter(grade__in=grade_level_ids)

    task_instance, created = Task.objects.get_or_create(name=task_name)
    task_instance.form = task_form
    task_instance.save()

    # Assign grade levels to the task
    task_instance.grade_levels.add(*grade_levels)

    created_examples = []

    # Loop through each example data and create it
    for example_data in examples_data:
        example_text = example_data.get('example')
        input_type = example_data.get('input_type')
        answer_text = example_data.get('answer')
        steps = example_data.get('steps', [])

        if not example_text or not input_type:
            continue

        example_payload = {
            'example': example_text,
            'input_type': input_type,
            'task': task_instance.id
        }
        example_serializer = ExampleSerializer(data=example_payload)

        if example_serializer.is_valid():
            with transaction.atomic():
                example_instance = example_serializer.save()

                if answer_text:
                    Answer.objects.create(example=example_instance, answer=answer_text)

                for index, step_text in enumerate(steps, start=1):
                    if step_text:
                        Step.objects.create(
                            example=example_instance,
                            text=step_text,
                            order=index
                        )

                created_examples.append(example_serializer.data)

    return Response({"created_examples": created_examples}, status=status.HTTP_201_CREATED)

# Edits an existing task and its examples
@api_view(['POST'])
def edit_task(request):
    task_id = request.data.get('task_id')
    task_name = request.data.get('task_name')
    task_form = request.data.get('task_form')   
    grade_level_ids = request.data.get('grade_level_ids', [])
    examples_data = request.data.get('examples', [])

    if not task_id:
        return Response({"error": "Nebyl zadán ID sady"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        task_instance = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({"error": "Task not found."}, status=status.HTTP_404_NOT_FOUND)

    # Update task attributes
    if task_name:
        task_instance.name = task_name
        task_instance.form = task_form
        task_instance.save()

    # Update grade levels if provided
    if grade_level_ids:
        grade_levels = GradeLevel.objects.filter(grade__in=grade_level_ids)
        task_instance.grade_levels.set(grade_levels)

    updated_examples = []

    # Loop through each example in the request data
    for example_data in examples_data:
        example_id = example_data.get('example_id')
        example_text = example_data.get('example')
        input_type = example_data.get('input_type')
        answer_text = example_data.get('answer')
        steps = example_data.get('steps', [])

        if not example_text or not input_type:
            continue

        # If example_id is provided, update the existing example
        if example_id:
            try:
                example_instance = Example.objects.get(id=example_id, task=task_instance)
                example_instance.example = example_text
                example_instance.input_type = input_type
                example_instance.save()
            except Example.DoesNotExist:
                return Response({"error": f"Example with ID {example_id} not found."},
                                status=status.HTTP_404_NOT_FOUND)

        # No example_id — check by text or create new
        else:
            example_instance, created = Example.objects.update_or_create(
                example=example_text,
                task=task_instance,
                defaults={'input_type': input_type}
            )

        # Update or create answer
        if answer_text:
            Answer.objects.update_or_create(
                example=example_instance,
                defaults={'answer': answer_text}
            )

        # Update steps
        Step.objects.filter(example=example_instance).delete()
        for index, step_text in enumerate(steps, start=1):
            if step_text:
                Step.objects.create(
                    example=example_instance,
                    order=index,
                    text=step_text
                )

        example_serializer = ExampleSerializer(example_instance)
        updated_examples.append(example_serializer.data)

    return Response({"updated_examples": updated_examples}, status=status.HTTP_200_OK)

# Get skill data by provided skill id
@api_view(['GET'])
def get_skill(request, skill_id):
    try:
        skill = Skill.objects.get(id=skill_id)

        if skill.deleted == True:
            return Response({"error": "Skill not found"}, status=status.HTTP_404_NOT_FOUND)
        
        skill_data = SkillSerializer(skill).data
        skill_data['example_count'] = ExampleSkill.objects.filter(skill=skill).count()
    
        return Response(skill_data, status=status.HTTP_200_OK)

    except Skill.DoesNotExist:
        return Response({"error": "Skill not found"}, status=status.HTTP_404_NOT_FOUND)

def _extract_variable_keys(answer_str):
    """Return list of variable names from answer string like 'x=5;y=3' → ['x', 'y']."""
    keys = []
    for pair in (answer_str or '').split(';'):
        if '=' in pair:
            key = pair.split('=')[0].strip()
            if key:
                keys.append(key)
    return keys


# Get all examples for the provided skill ids
@api_view(['GET'])
def get_examples(request):
    task_id = request.query_params.get('task_id')

    if task_id:
        task = get_object_or_404(
            Task.objects.prefetch_related('example_set__answers', 'example_set__steps'),
            id=task_id,
        )

        example_data = []
        for example in task.example_set.all():
            entry = {
                "id": example.id,
                "example": example.example,
                "input_type": example.input_type,
                "steps": [
                    {"id": step.id, "order": step.order, "text": step.text}
                    for step in example.steps.all().order_by('order')
                ],
            }
            if example.input_type == 'VAR':
                first_answer = example.answers.first()
                entry["variable_keys"] = _extract_variable_keys(first_answer.answer if first_answer else '')
            example_data.append(entry)

        random.shuffle(example_data)
        return Response(example_data, status=status.HTTP_200_OK)

    skills = request.query_params.get('topics')
    
    if not skills:
        return Response({"error": "No topics provided"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        skills_data = json.loads(skills)

    except json.JSONDecodeError:
        return Response({"error": "Invalid JSON format for topics"}, status=status.HTTP_400_BAD_REQUEST)

    # Get skill paths to get examples containing them
    skill_paths = get_skill_paths(skills_data)

    example_data = []

    for path in skill_paths:

        examples = Example.objects.filter(
            exampleskill__skill__id__in=path
        ).exclude(task__is_private=True).distinct()

        for example in examples:

            example_skill_ids = set(example.exampleskill_set.values_list('skill__id', flat=True))

            # Check if the example skill ids contain all the skills in the current path (no missing skills)
            if example_skill_ids.issuperset(set(path)):

                entry = {
                    "id": example.id,
                    "example": example.example,
                    "input_type": example.input_type,
                    "steps": [
                        {"id": step.id, "order": step.order, "text": step.text}
                        for step in example.steps.all().order_by('order')
                    ],
                }
                if example.input_type == 'VAR':
                    first_answer = example.answers.first()
                    entry["variable_keys"] = _extract_variable_keys(first_answer.answer if first_answer else '')
                example_data.append(entry)

    # Shuffle the final list of examples to ensure they are mixed
    random.shuffle(example_data)

    return Response(example_data, status=status.HTTP_200_OK)

# Create a new record that user practiced the example
@api_view(['POST'])
def create_example_record(request):
    student, anonymous_session = get_user_identity(request)
    example_id = request.data.get('example_id')
    practiced_skills = request.data.get('practiced_skills', [])
    
    if not student and not anonymous_session:
        return Response({"error": "Student ID or Session ID is required"}, status=status.HTTP_400_BAD_REQUEST)
    if not example_id:
        return Response({"error": "Example ID is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    init_data = {
        'student': student.id if student else None,
        'anonymous_session': anonymous_session.id if anonymous_session else None,
        'example': example_id,
        'practiced_skills': practiced_skills,
        'practice_session_key': request.data.get('practice_session_key') or None,
    }

    record_init_serializer = RecordInitSerializer(data=init_data)

    if record_init_serializer.is_valid():
        record = record_init_serializer.save()

        response_data = record_init_serializer.data
        response_data['date'] = record.date

        return Response(response_data, status=status.HTTP_201_CREATED)

    return Response(record_init_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_attempt_logs(request):
    student_id = request.query_params.get('student_id')
    session_id = request.query_params.get('session_id')
    limit = request.query_params.get('limit', 200)

    if not student_id and not session_id:
        return Response({"error": "student_id or session_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        limit = max(1, min(int(limit), 1000))
    except (TypeError, ValueError):
        limit = 200

    records = ExampleAttempt.objects.select_related(
        'student', 'anonymous_session', 'example', 'student_example'
    )

    if student_id:
        records = records.filter(student_id=student_id)
    else:
        records = records.filter(anonymous_session__session_id=session_id)

    date_from = request.query_params.get('date_from')
    if date_from:
        records = records.filter(created_at__gte=date_from)

    serializer = ExampleAttemptSerializer(records[:limit], many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_progress_overview(request):
    student_id = request.query_params.get('student_id')
    session_id = request.query_params.get('session_id')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')

    if not student_id and not session_id:
        return Response({"error": "student_id or session_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        recent_limit = max(1, min(int(request.query_params.get('recent_limit', 50)), 200))
    except (TypeError, ValueError):
        recent_limit = 50

    attempts = ExampleAttempt.objects.select_related('example')
    if student_id:
        attempts = attempts.filter(student_id=student_id)
    else:
        attempts = attempts.filter(anonymous_session__session_id=session_id)

    if date_from:
        attempts = attempts.filter(created_at__gte=date_from)
    if date_to:
        attempts = attempts.filter(created_at__lte=date_to)

    total_records = attempts.count()
    evaluated = attempts.filter(action='evaluated')
    evaluated_records = evaluated.count()
    correct_count = evaluated.filter(is_correct=True).count()
    incorrect_count = evaluated.filter(is_correct=False).count()
    skipped_count = attempts.filter(action='skipped').count()
    terminated_count = attempts.filter(action='terminated').count()

    duration_total = attempts.aggregate(total=Sum('duration'))['total'] or 0
    avg_duration = attempts.aggregate(avg=Avg('duration'))['avg'] or 0
    last_activity = attempts.aggregate(last=Max('created_at'))['last']
    distinct_examples = attempts.values('example_id').distinct().count()

    skill_rows = attempts.filter(
        example__exampleskill__skill__deleted=False
    ).values(
        'example__exampleskill__skill_id',
        'example__exampleskill__skill__name',
    ).annotate(
        attempts_count=Count('id'),
        evaluated_count=Count('id', filter=Q(action='evaluated')),
        correct_count=Count('id', filter=Q(action='evaluated', is_correct=True)),
        avg_duration=Avg('duration'),
        last_activity=Max('created_at'),
    ).order_by('example__exampleskill__skill__name')

    by_skill = []
    for row in skill_rows:
        denom = row['evaluated_count'] or 0
        accuracy = (row['correct_count'] / denom) if denom else 0
        by_skill.append({
            'skill_id': row['example__exampleskill__skill_id'],
            'skill_name': row['example__exampleskill__skill__name'],
            'attempts': row['attempts_count'],
            'evaluated': row['evaluated_count'],
            'correct': row['correct_count'],
            'accuracy': round(accuracy, 3),
            'avg_duration_ms': row['avg_duration'] or 0,
            'last_activity': row['last_activity'],
        })

    by_input_type_rows = attempts.values('input_type').annotate(
        attempts_count=Count('id'),
        evaluated_count=Count('id', filter=Q(action='evaluated')),
        correct_count=Count('id', filter=Q(action='evaluated', is_correct=True)),
        avg_duration=Avg('duration'),
    ).order_by('input_type')

    by_input_type = []
    for row in by_input_type_rows:
        denom = row['evaluated_count'] or 0
        accuracy = (row['correct_count'] / denom) if denom else 0
        by_input_type.append({
            'input_type': row['input_type'] or 'UNKNOWN',
            'attempts': row['attempts_count'],
            'evaluated': row['evaluated_count'],
            'correct': row['correct_count'],
            'accuracy': round(accuracy, 3),
            'avg_duration_ms': row['avg_duration'] or 0,
        })

    daily_rows = attempts.annotate(day=TruncDate('created_at')).values('day').annotate(
        attempts_count=Count('id'),
        evaluated_count=Count('id', filter=Q(action='evaluated')),
        correct_count=Count('id', filter=Q(action='evaluated', is_correct=True)),
        avg_duration=Avg('duration'),
    ).order_by('day')

    daily = []
    for row in daily_rows:
        denom = row['evaluated_count'] or 0
        accuracy = (row['correct_count'] / denom) if denom else 0
        daily.append({
            'date': row['day'],
            'attempts': row['attempts_count'],
            'evaluated': row['evaluated_count'],
            'correct': row['correct_count'],
            'accuracy': round(accuracy, 3),
            'avg_duration_ms': row['avg_duration'] or 0,
        })

    recent_attempts = list(
        attempts.values(
            'id',
            'created_at',
            'example_id',
            'example_text',
            'correct_answer',
            'transcription',
            'parsed_answer',
            'is_correct',
            'action',
            'duration',
            'attempt_number',
            'input_type',
            'language',
            'audio_file_path',
            'practiced_skill_ids',
            'practiced_skill_names',
        ).order_by('-created_at')[:recent_limit]
    )

    response_payload = {
        'summary': {
            'total_records': total_records,
            'evaluated_records': evaluated_records,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'skipped_count': skipped_count,
            'terminated_count': terminated_count,
            'accuracy': round((correct_count / evaluated_records), 3) if evaluated_records else 0,
            'total_duration_ms': duration_total,
            'avg_duration_ms': avg_duration,
            'distinct_examples': distinct_examples,
            'distinct_skills': len(by_skill),
            'last_activity': last_activity,
        },
        'by_skill': by_skill,
        'by_input_type': by_input_type,
        'daily': daily,
        'recent_attempts': recent_attempts,
    }

    return Response(response_payload, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_my_data(request):
    """
    Returns ALL data collected about the user during practice sessions.
    Includes every attempt, transcription, correctness, duration, skills, audio file paths.
    """
    student_id = request.query_params.get('student_id')
    session_id = request.query_params.get('session_id')

    if not student_id and not session_id:
        return Response({"error": "student_id or session_id required"}, status=status.HTTP_400_BAD_REQUEST)

    attempts = ExampleAttempt.objects.select_related(
        'student', 'anonymous_session', 'example', 'student_example'
    ).order_by('-created_at')

    if student_id:
        attempts = attempts.filter(student_id=student_id)
    else:
        attempts = attempts.filter(anonymous_session__session_id=session_id)

    if not attempts.exists():
        return Response({
            "user_id": student_id or session_id,
            "user_type": "student" if student_id else "anonymous",
            "message": "No attempt data found",
            "attempts": []
        }, status=status.HTTP_200_OK)

    attempts_data = []
    for attempt in attempts:
        attempt_dict = {
            "attempt_id": attempt.id,
            "timestamp": attempt.created_at.isoformat(),
            "attempt_number": attempt.attempt_number,
            "example_id": attempt.example_id,
            "example_problem": attempt.example_text,
            "input_type": attempt.input_type,
            "language": attempt.language,
            "action": attempt.action,
            "duration_ms": attempt.duration,
            "transcription": attempt.transcription,
            "your_answer": attempt.parsed_answer,
            "correct_answer": attempt.correct_answer,
            "is_correct": attempt.is_correct,
            "source": attempt.source,
            "audio_file": attempt.audio_file_path,
            "audio_url": f"/api/attempt-audio/{attempt.id}/" if (
                attempt.audio_file_path
                or (attempt.meta or {}).get('mega_audio_url')
                or (attempt.meta or {}).get('mega_public_url')
            ) else "",
            "paired_json_url": "",
            "paired_cloud_audio_url": (attempt.meta or {}).get('mega_audio_url', '') or (attempt.meta or {}).get('mega_public_url', ''),
            "audio_format": attempt.audio_format,
            "practiced_skills": {
                "ids": attempt.practiced_skill_ids,
                "names": attempt.practiced_skill_names,
            },
            "metadata": attempt.meta,
        }

        meta = attempt.meta or {}
        paired_json_url = meta.get('mega_json_url', '')
        if not paired_json_url:
            local_sidecar = meta.get('paired_json_local_path', '')
            if not local_sidecar and attempt.audio_file_path:
                try:
                    local_sidecar = ensure_attempt_sidecar(attempt)
                    meta = attempt.meta or {}
                except Exception:
                    local_sidecar = ''
            if local_sidecar:
                paired_json_url = f"/api/attempt-sidecar/{attempt.id}/"

        attempt_dict["paired_json_url"] = paired_json_url
        attempt_dict["metadata"] = meta
        attempts_data.append(attempt_dict)

    total_count = len(attempts_data)
    evaluated = [a for a in attempts_data if a["action"] == "evaluated"]
    correct = [a for a in evaluated if a["is_correct"]]
    incorrect = [a for a in evaluated if not a["is_correct"]]
    skipped = [a for a in attempts_data if a["action"] == "skipped"]
    terminated = [a for a in attempts_data if a["action"] == "terminated"]
    errors = [a for a in attempts_data if a["action"] == "error"]

    distinct_skills = set()
    for a in attempts_data:
        distinct_skills.update(a["practiced_skills"]["ids"])

    total_duration = sum(a["duration_ms"] for a in attempts_data)
    avg_duration = total_duration / total_count if total_count else 0

    return Response({
        "user_id": student_id or session_id,
        "user_type": "student" if student_id else "anonymous_session",
        "summary": {
            "total_attempts": total_count,
            "evaluated_count": len(evaluated),
            "correct_count": len(correct),
            "incorrect_count": len(incorrect),
            "skipped_count": len(skipped),
            "terminated_count": len(terminated),
            "error_count": len(errors),
            "accuracy": round(len(correct) / len(evaluated), 3) if evaluated else 0,
            "total_duration_ms": total_duration,
            "avg_duration_ms": avg_duration,
            "distinct_skills_count": len(distinct_skills),
        },
        "all_attempts": attempts_data,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_attempt_audio(request, attempt_id):
    attempt = get_object_or_404(ExampleAttempt, id=attempt_id)

    cloud_url = (attempt.meta or {}).get('mega_audio_url', '') or (attempt.meta or {}).get('mega_public_url', '')

    if not attempt.audio_file_path:
        if cloud_url:
            return redirect(cloud_url)
        return Response({"error": "Audio file not available for this attempt"}, status=status.HTTP_404_NOT_FOUND)

    candidate_paths = [attempt.audio_file_path]
    candidate_paths.append(os.path.join(os.getcwd(), attempt.audio_file_path))

    file_path = None
    for path in candidate_paths:
        if _existing_nonempty_file(path):
            file_path = path
            break

    if not file_path:
        if cloud_url:
            response = _temporary_cloud_file_response(
                public_url=cloud_url,
                filename_hint=attempt.audio_file_path or f"attempt_{attempt.id}.wav",
                content_type='audio/wav',
            )
            if response:
                return response
            return redirect(cloud_url)
        return Response({"error": "Audio file not found on server"}, status=status.HTTP_404_NOT_FOUND)

    return FileResponse(open(file_path, 'rb'), content_type='audio/wav')


@api_view(['GET'])
def get_attempt_sidecar(request, attempt_id):
    attempt = get_object_or_404(ExampleAttempt, id=attempt_id)

    meta = attempt.meta or {}
    local_sidecar = meta.get('paired_json_local_path', '')
    cloud_url = meta.get('mega_json_url', '')

    if not local_sidecar and attempt.audio_file_path:
        try:
            local_sidecar = ensure_attempt_sidecar(attempt)
            meta = attempt.meta or {}
        except Exception:
            local_sidecar = ''

    candidate_paths = []
    if local_sidecar:
        candidate_paths.append(local_sidecar)
        candidate_paths.append(os.path.join(os.getcwd(), local_sidecar))

    file_path = None
    for path in candidate_paths:
        if _existing_nonempty_file(path):
            file_path = path
            break

    if file_path:
        return FileResponse(open(file_path, 'rb'), content_type='application/json')

    if cloud_url:
        response = _temporary_cloud_file_response(
            public_url=cloud_url,
            filename_hint=local_sidecar or f"attempt_{attempt.id}.json",
            content_type='application/json',
        )
        if response:
            return response
        return redirect(cloud_url)

    return Response({"error": "JSON sidecar not available for this attempt"}, status=status.HTTP_404_NOT_FOUND)

# Updates record that user practiced the example
@api_view(['POST'])
def update_example_record(request):
    # Data to identify the record
    student, anonymous_session = get_user_identity(request)
    example_id = request.data.get('example_id')
    date = request.data.get('date')

    # Duration how long it took user to enter the answer
    duration = request.data.get('time')
  
    if (not student and not anonymous_session) or not example_id or not duration:
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Find record by student or anonymous_session
    if student:
        student_example = get_object_or_404(StudentExample, student=student, example_id=example_id, date=date)
    else:
        student_example = get_object_or_404(StudentExample, anonymous_session=anonymous_session, example_id=example_id, date=date)
    
    try:
        with transaction.atomic():
            # Update record data
            student_example.attempts += 1
            student_example.duration = duration

            # Determine if limit of tries is reached and new example should be shown to user
            next_example = student_example.attempts == 3
                         
            student_example.save()
        
        return Response({"message": "Record updated successfully", "next_example": next_example}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Deletes record that user practiced the example        
@api_view(['POST'])
def delete_example_record(request):
    # Data to identify the record
    student, anonymous_session = get_user_identity(request)
    example_id = request.data.get('example_id')
    date = request.data.get('date')

    if (not student and not anonymous_session) or not example_id or not date:
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)
    
    if student:
        student_example = get_object_or_404(StudentExample, student=student, example_id=example_id, date=date)
    else:
        student_example = get_object_or_404(StudentExample, anonymous_session=anonymous_session, example_id=example_id, date=date)

    try:
        with transaction.atomic():
            student_example.delete()

        return Response({"message": "Record successfully deleted"}, status=status.HTTP_204_NO_CONTENT)

    except StudentExample.DoesNotExist:
        return Response({"error": "Record not found"}, status=status.HTTP_404_NOT_FOUND)

# Updates example record to skipped
@api_view(['POST'])
def skip_example(request):
    # Data to identify the record
    student, anonymous_session = get_user_identity(request)
    example_id = request.data.get('example_id')
    date = request.data.get('date')

    if (not student and not anonymous_session) or not example_id or not date:
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)
    
    if student:
        student_example = get_object_or_404(StudentExample, student=student, example_id=example_id, date=date)
    else:
        student_example = get_object_or_404(StudentExample, anonymous_session=anonymous_session, example_id=example_id, date=date)

    try:
        with transaction.atomic():

            # Record is marked as skipped and attempts and duration are not relevant
            student_example.skipped = True
            student_example.attempts = 0
            student_example.duration = 0
                        
            student_example.save()
        
        return Response({"message": "Example skipped"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Get all tasks and their examples
@api_view(['GET'])
def get_tasks(request):
    tasks = Task.objects.prefetch_related(
        'example_set__answers',         
        'example_set__exampleskill_set__skill', 
        'example_set__steps',
        'grade_levels',
    )
    
    data = []
    for task in tasks:
        # Get skills for the task
        skills = []
        # Use the first example to get skills, since all examples share the same skills
        first_example = task.example_set.first()
        if first_example:
            skills = [
                {
                    "id": example_skill.skill.id,
                    "name": example_skill.skill.name,
                    "height": example_skill.skill.height,
                    "skill_type": example_skill.skill.skill_type,
                    "parent_skill": example_skill.skill.parent_skill.id if example_skill.skill.parent_skill else None,
                    "related_skills": list(example_skill.skill.related_skills.values_list('id', flat=True))
                }
                for example_skill in first_example.exampleskill_set.all()
            ]
        
        # Get task data
        task_data = {
            "task_id": task.id,
            "task_name": task.name,
            "task_form": task.form,
            "grade_levels": [
                {
                    "id": grade_level.id,
                    "grade": grade_level.grade,
                }
                for grade_level in task.grade_levels.all().order_by('grade')
            ],
            "skills": skills,  
            "examples": [
                {
                    "example_id": example.id,
                    "example": example.example,
                    "input_type": example.input_type,
                    "answers": [
                        {
                            "answer_id": answer.id,
                            "answer_text": answer.answer
                        }
                        for answer in example.answers.all()
                    ],
                    "steps": [
                        {
                            "step_id": step.id,
                            "step_text": step.text,
                            "order": step.order
                        }
                        for step in example.steps.all()
                    ]
                }
                for example in task.example_set.all()
            ]
        }
        data.append(task_data)
    
    return JsonResponse(data, safe=False)


@api_view(['GET'])
def get_task_assignment_overview(request):
    tasks = Task.objects.prefetch_related(
        'skills',
        'grade_levels',
    ).annotate(
        example_count=Count('example', distinct=True),
    ).order_by('name')

    data = []
    for task in tasks:
        task_skills = sorted(task.skills.all(), key=lambda skill: skill.name.lower())
        task_grade_levels = sorted(task.grade_levels.all(), key=lambda grade: grade.grade)

        data.append(
            {
                "id": task.id,
                "name": task.name,
                "form": task.form,
                "example_count": task.example_count,
                "skills": [
                    {
                        "id": skill.id,
                        "name": skill.name,
                    }
                    for skill in task_skills
                ],
                "grade_levels": [
                    {
                        "id": grade_level.id,
                        "grade": grade_level.grade,
                    }
                    for grade_level in task_grade_levels
                ],
            }
        )

    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)


@api_view(['PATCH'])
def update_task_grade_levels(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    grade_level_ids = request.data.get('grade_levels', [])

    if not isinstance(grade_level_ids, list):
        return Response({"error": "grade_levels must be a list"}, status=status.HTTP_400_BAD_REQUEST)

    valid_grade_ids = list(
        GradeLevel.objects.filter(id__in=grade_level_ids).values_list('id', flat=True)
    )
    task.grade_levels.set(valid_grade_ids)

    # Sync primary TASK skill: create if missing, update grade_levels, link all examples
    if valid_grade_ids:
        skill = task.primary_skill
        if skill is None:
            skill = Skill.objects.create(name=task.name, skill_type='TASK')
            task.primary_skill = skill
            task.save(update_fields=['primary_skill'])
        else:
            skill.name = task.name
            skill.save(update_fields=['name'])
        skill.grade_levels.set(valid_grade_ids)
        # Ensure every example is linked to this skill
        for example in task.example_set.all():
            ExampleSkill.objects.get_or_create(example=example, skill=skill)
    elif task.primary_skill:
        # All grades removed — clear skill grade_levels so it disappears from grade pages
        task.primary_skill.grade_levels.clear()

    return Response(
        {
            "task_id": task.id,
            "grade_levels": list(
                task.grade_levels.order_by('grade').values('id', 'grade')
            ),
        },
        status=status.HTTP_200_OK,
    )

# Delete an example and its related data (answers, steps)
@api_view(['DELETE'])
def delete_example(request, example_id):
    example = get_object_or_404(Example, id=example_id)
    
    try:
        with transaction.atomic():
            example.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Delete a task and its related data
@api_view(['DELETE'])
def delete_task(request, task_id):
    try:
        with transaction.atomic():
            task = get_object_or_404(Task, id=task_id)
            
            related_skills = list(task.skills.all())  

            # Remove connections from the skill-task relationship
            task.skills.clear()

            # Delete the task and its related data (examples, answers, steps)
            task.delete()

            # Check skill relationships and remove them if no other task uses them
            for skill in related_skills:
                for related_skill in skill.related_skills.all():
                    # Get all tasks where both skills are used together
                    shared_tasks = Task.objects.filter(skills=skill).filter(skills=related_skill)
                    
                    # If this was the last task using this relationship, remove the relation
                    if not shared_tasks.exists():
                        skill.related_skills.remove(related_skill)
                        related_skill.related_skills.remove(skill)

        return Response(status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        return Response(
            {"error": f"Error deleting task: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

# Create a new skill or restore a deleted one
@api_view(['POST'])
def create_skill(request):
    try:
        name = request.data.get('name')
        parent_skill_id = request.data.get('parent_skill')
        grade_level_ids = request.data.get('grade_levels', [])

        if not name:
            return Response({"error": "Skill name is required."}, status=status.HTTP_400_BAD_REQUEST)

        parent_skill = None
        skill_type = None

        # Prepare new skill data
        if parent_skill_id:
            parent_skill = get_object_or_404(Skill, id=parent_skill_id)
            skill_type = parent_skill.skill_type  
            height = get_height(parent_skill_id) + 1
        
        # No parent skill
        else:
            height = 0  
        # Check if a skill with the same name already exists and is not deleted
        existing_skill = Skill.objects.filter(name=name, deleted=True).first()
        
        if existing_skill:
            # If a deleted skill exists with the same name, restore it
            existing_skill.deleted = False
            existing_skill.save()
            
            # Update grade levels
            if grade_level_ids:
                existing_skill.grade_levels.set(grade_level_ids)

            return JsonResponse({
                "id": existing_skill.id,
                "name": existing_skill.name,
                "parent_skill": existing_skill.parent_skill.id if existing_skill.parent_skill else None,
                "skill_type": existing_skill.skill_type,
                "grade_levels": list(existing_skill.grade_levels.values_list('id', flat=True)),
            }, status=status.HTTP_200_OK)

        # If no deleted skill exists, create a new skill
        else:
            with transaction.atomic():  
                skill = Skill.objects.create(
                    name=name, 
                    parent_skill=parent_skill, 
                    skill_type=skill_type, 
                    height=height
                )
                
                # Add grade levels
                if grade_level_ids:
                    skill.grade_levels.set(grade_level_ids)

            return JsonResponse({
                "id": skill.id,
                "name": skill.name,
                "parent_skill": skill.parent_skill.id if skill.parent_skill else None,
                "skill_type": skill.skill_type,
                "grade_levels": list(skill.grade_levels.values_list('id', flat=True)),
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Get all skills in a tree structure
@api_view(['GET'])
def get_skill_tree(request):
    skills = Skill.objects.filter(deleted=False)
    skill_list = SkillSerializer(skills, many=True).data

    # Convert the flat list into a hierarchical structure
    skill_dict = {skill["id"]: {**skill, "children": []} for skill in skill_list}

    root_skills = []

    # Build the tree structure
    for skill in skill_dict.values():

        if skill["parent_skill"] is None:
            root_skills.append(skill)

        else:
            parent = skill_dict.get(skill["parent_skill"])
            if parent:
                parent["children"].append(skill)

    return Response(root_skills)

# Search for skills based on a query and parent skill
@api_view(['GET'])
def search_skills(request):
    query = request.GET.get('q', '') 
    skill_id = request.GET.get('skill_id', None) 

    if not skill_id:
        return Response([]) 

    try:
        parent_skill = Skill.objects.get(id=skill_id)

    except Skill.DoesNotExist:
        return Response([])

    if query:
        # Searched skill name must be children of provided parent skill
        skills = Skill.objects.filter(
            name__icontains=query, 
            parent_skill=parent_skill,
            deleted=False  
        )
    # No query provided, get all children of the parent skill   
    else:
        skills = Skill.objects.filter(parent_skill=parent_skill, deleted=False)

    skill_list = SkillSerializer(skills, many=True).data

    return Response(skill_list)

# Get skills which should be displayed on landing page
@api_view(['GET'])
def get_landing_page_skills(request):

    # Show only leaf skills (no children), assigned to at least one grade.
    # This hides broad parent categories from menu navigation.
    skills = Skill.objects.filter(
        deleted=False,
        subskills__isnull=True,
        grade_levels__isnull=False,
    ).distinct().order_by('name')

    serializer = SkillSerializer(skills, many=True)

    return Response(serializer.data)

# Get all skills related to the selected skill  
@api_view(['GET'])
def get_related_skills_tree(request, skill_id):
    try:
        main_skill = Skill.objects.get(id=skill_id, deleted=False)  
        visited = set()
        tree = []

        related_skills = main_skill.related_skills.filter(deleted=False)    

        # Build tree structure to be visualized in the frontend
        for skill in related_skills:
            skill_ids = [main_skill.id, skill.id] 
            if skill.id not in visited:
                subtree = build_skill_tree(skill, visited, skill_ids, related_skills, None)
                if subtree:
                    tree.append(subtree)

        return Response(tree)

    except Skill.DoesNotExist:
        return Response({"error": "Skill not found"}, status=404)

# Get all children skills of the selected skill
@api_view(['GET'])
def get_children_skills_tree(request, skill_id):

    # Edge case for Equation skills
    withCounts = request.GET.get('with_counts', 'false') == 'true'

    try:
        main_skill = Skill.objects.get(id=skill_id)  

        if main_skill.deleted:
            return Response({"error": "Skill not found"}, status=404)   
        visited = set()  
        tree = []
        
        # Get all children skills of the selected skill
        children = Skill.objects.filter(parent_skill=main_skill, deleted=False)

        # Build subtree structure of each child to be visualized in the frontend
        for skill in children:
            if skill.id not in visited:
                subtree = build_skill_tree(skill, visited, None, None, withCounts) 
                if subtree:
                    tree.append(subtree)

        return Response(tree)  

    except Skill.DoesNotExist:
        return Response({"error": "Skill not found"}, status=404)

# Get all operation skills related to the selected skill    
@api_view(['GET'])
def get_operation_skills(request, skill_id):
    try:
        main_skill = get_object_or_404(Skill, id=skill_id)

        if main_skill.deleted:
            return Response({"error": "Skill not found"}, status=404)

        # Get all children skills of the selected skill
        children_skills = main_skill.subskills.filter(deleted=False)

        # Get all operation skills related to the selected skill    
        related_operation_skills = main_skill.related_skills.filter(skill_type='OPERATION', deleted=False)

        skills_data = []

        for operation_skill in related_operation_skills:
            child_data = []

            for child_skill in children_skills:
                # Count examples that have both operation_skill and child_skill
                examples_count = ExampleSkill.objects.filter(
                    skill=operation_skill
                ).filter(
                    example__in=ExampleSkill.objects.filter(skill=child_skill).values('example')
                ).count()

                child_data.append({
                    "related_id": child_skill.id,
                    "related_name": child_skill.name,
                    "examples": examples_count
                })

            # Include only single operations not parent skill Operations
            if operation_skill.height >= 3:
                skills_data.append({
                "id": operation_skill.id,
                "name": operation_skill.name,
                "related_skills": child_data
                })

        return Response(skills_data)
    
    except Skill.DoesNotExist:
        return Response({"error": "Skill not found"}, status=404)

# Soft delete a skill and remove all its relations
@api_view(['PATCH'])
def delete_skill(request, skill_id):
    try:
        skill = Skill.objects.get(id=skill_id)
        
        # Mark the skill as deleted
        skill.deleted = True
        skill.save()
        
        # Remove this skill from all related examples
        ExampleSkill.objects.filter(skill=skill).delete()
        
        # Remove this skill from realtions with tasks
        for task in Task.objects.filter(skills=skill):
            task.skills.remove(skill)
        
        # Remove this skill from all related_skills
        for related_skill in skill.related_skills.all():
            skill.related_skills.remove(related_skill)
        
        return Response(
            {"message": f"Skill '{skill.name}' marked as deleted and all relations removed."},
            status=status.HTTP_200_OK
        )
        
    except Skill.DoesNotExist:
        return Response(
            {"error": "Skill not found."},
            status=404
        )

# Create new user account
@api_view(['POST'])
def register_student(request):
    username = request.data.get('username')
    passphrase = request.data.get('passphrase')
    grade = request.data.get('grade')

    if not username or not passphrase:
        return Response({'error': 'Chybí uživatelské jméno nebo heslo'}, status=status.HTTP_400_BAD_REQUEST)

    if Student.objects.filter(username=username).exists():
        return Response({'error': 'Tato přezdívka je již používána jiným uživatelem'}, status=status.HTTP_400_BAD_REQUEST)

    hashed_passphrase = make_password(passphrase)

    grade_value = None
    if grade is not None:
        try:
            grade_value = int(grade)
            if not (1 <= grade_value <= 9):
                grade_value = None
        except (TypeError, ValueError):
            grade_value = None

    student = Student.objects.create(username=username, passphrase=hashed_passphrase, grade=grade_value)

    return Response({'message': 'Student registered successfully!', 'id': student.id}, status=status.HTTP_201_CREATED)

# Login user account
@api_view(['POST'])
def login_student(request):
    username = request.data.get('username')
    passphrase = request.data.get('passphrase')

    if not username or not passphrase:
        return Response({'error': 'Nebyly zadány všechny potřebné údaje'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        student = Student.objects.get(username=username)
    except Student.DoesNotExist:
        return Response({'error': 'Nesprávné přihlašovací údaje'}, status=status.HTTP_400_BAD_REQUEST)

    if check_password(passphrase, student.passphrase):
        return Response({
            'message': 'Login successful!',
            'id': student.id,
            'role': 'student',
            'language': student.language,
            'grade': student.grade,
            'grade_change_used': student.grade_change_used,
        }, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Nesprávné přihlašovací údaje'}, status=status.HTTP_401_UNAUTHORIZED)
    
# Update student grade (allowed once after initial registration)
@api_view(['PATCH'])
def update_student_grade(request, student_id):
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    if student.grade_change_used:
        return Response({'error': 'Grade can only be changed once'}, status=status.HTTP_400_BAD_REQUEST)

    grade = request.data.get('grade')
    try:
        grade_value = int(grade)
        if not (1 <= grade_value <= 9):
            raise ValueError
    except (TypeError, ValueError):
        return Response({'error': 'Grade must be an integer between 1 and 9'}, status=status.HTTP_400_BAD_REQUEST)

    student.grade = grade_value
    student.grade_change_used = True
    student.save(update_fields=['grade', 'grade_change_used'])

    return Response({'grade': student.grade, 'grade_change_used': student.grade_change_used})


# Login admin account
@api_view(['POST'])
def login_admin(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'Nebyly zadány všechny potřebné údaje'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        admin = Admin.objects.get(username=username)
    except Admin.DoesNotExist:
        return Response({'error': 'Nesprávné přihlašovací údaje'}, status=status.HTTP_400_BAD_REQUEST)

    if check_password(password, admin.password):
        return Response({'message': 'Přihlášení proběhlo úspěšně!', 'role': 'admin'}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Nesprávné přihlašovací údaje'}, status=status.HTTP_401_UNAUTHORIZED)


# ─── Teacher Auth ────────────────────────────────────────────────────────────

def _send_teacher_welcome_email(teacher_email, first_name):
    """Send a welcome email with the teacher guide PDF. Runs in a background thread."""
    if not django_settings.EMAIL_HOST_USER:
        logger.warning('EMAIL_HOST_USER not set — skipping welcome email')
        return
    try:
        pdf_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'Navod_pre_ucitelov.pdf')
        pdf_path = os.path.normpath(pdf_path)

        subject = 'Vitajte v Drillovačke!'
        body = (
            f'Dobrý deň, {first_name},\n\n'
            'Ďakujeme za registráciu v aplikácii Drillovačka.\n\n'
            'V prílohe nájdete stručný návod, ktorý vám pomôže začať — '
            'ako vytvoriť triedu, pridať žiakov a priradiť príkladové sady.\n\n'
            'Ak budete mať akékoľvek otázky, neváhajte nás kontaktovať.\n\n'
            'Prajeme veľa úspechov,\n'
            'tím Drillovačka\n'
            'superlectures.net'
        )

        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=f'Drillovačka <{django_settings.DEFAULT_FROM_EMAIL}>',
            to=[teacher_email],
        )

        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                msg.attach('Navod_pre_ucitelov.pdf', f.read(), 'application/pdf')
        else:
            logger.warning(f'Teacher guide PDF not found at {pdf_path}')

        msg.send()
        logger.info(f'Welcome email sent to {teacher_email}')
    except Exception as e:
        logger.error(f'Failed to send welcome email to {teacher_email}: {e}')


@api_view(['POST'])
def register_teacher(request):
    email = request.data.get('email', '').strip()
    password = request.data.get('password')
    first_name = request.data.get('first_name', '').strip()
    last_name = request.data.get('last_name', '').strip()

    if not email or not password or not first_name or not last_name:
        return Response({'error': 'Všetky polia sú povinné'}, status=status.HTTP_400_BAD_REQUEST)

    if Teacher.objects.filter(email=email).exists():
        return Response({'error': 'Tento email je už zaregistrovaný'}, status=status.HTTP_400_BAD_REQUEST)

    teacher = Teacher.objects.create(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    threading.Thread(
        target=_send_teacher_welcome_email,
        args=(teacher.email, teacher.first_name),
        daemon=True,
    ).start()

    return Response({
        'id': teacher.id,
        'role': 'teacher',
        'email': teacher.email,
        'first_name': teacher.first_name,
        'last_name': teacher.last_name,
        'language': teacher.language,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def login_teacher(request):
    email = request.data.get('email', '').strip()
    password = request.data.get('password')

    if not email or not password:
        return Response({'error': 'Nebyly zadány všechny potřebné údaje'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        teacher = Teacher.objects.get(email=email)
    except Teacher.DoesNotExist:
        return Response({'error': 'Nesprávné přihlašovací údaje'}, status=status.HTTP_400_BAD_REQUEST)

    if teacher.check_password(password):
        return Response({
            'id': teacher.id,
            'role': 'teacher',
            'email': teacher.email,
            'first_name': teacher.first_name,
            'last_name': teacher.last_name,
            'language': teacher.language,
        }, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Nesprávné přihlašovací údaje'}, status=status.HTTP_401_UNAUTHORIZED)


# Initialize or get anonymous session
@api_view(['POST'])
def init_session(request):
    session_id = request.data.get('session_id')
    
    # If no session_id provided, generate new one
    if not session_id:
        session_id = str(uuid.uuid4())
        session = AnonymousSession.objects.create(session_id=session_id)
        return Response({
            'session_id': session_id,
            'language': session.language,
            'created': True
        }, status=status.HTTP_201_CREATED)
    
    # Try to get existing session
    try:
        session = AnonymousSession.objects.get(session_id=session_id)
        # Update last_active timestamp
        session.save()
        return Response({
            'session_id': session.session_id,
            'language': session.language,
            'created': False
        }, status=status.HTTP_200_OK)
    except AnonymousSession.DoesNotExist:
        # Session doesn't exist, create new one
        session = AnonymousSession.objects.create(session_id=session_id)
        return Response({
            'session_id': session.session_id,
            'language': session.language,
            'created': True
        }, status=status.HTTP_201_CREATED)

# Update language preference for anonymous session
@api_view(['POST'])
def update_session_language(request):
    session_id = request.data.get('session_id')
    language = request.data.get('language')
    
    if not session_id or not language:
        return Response({'error': 'Missing session_id or language'}, status=status.HTTP_400_BAD_REQUEST)
    
    if language not in ['cs', 'sk', 'en']:
        return Response({'error': 'Invalid language code'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        session = AnonymousSession.objects.get(session_id=session_id)
        session.language = language
        session.save()
        return Response({
            'message': 'Language updated successfully',
            'language': session.language
        }, status=status.HTTP_200_OK)
    except AnonymousSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

# Update language preference for authenticated student
@api_view(['POST'])
def update_student_language(request):
    student_id = request.data.get('student_id')
    language = request.data.get('language')
    
    print(f"[DEBUG] update_student_language called with student_id={student_id}, language={language}")
    
    if not student_id or not language:
        return Response({'error': 'Missing student_id or language'}, status=status.HTTP_400_BAD_REQUEST)
    
    if language not in ['cs', 'sk', 'en']:
        return Response({'error': 'Invalid language code'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        student = Student.objects.get(id=student_id)
        print(f"[DEBUG] Found student: {student.username}, current language: {student.language}")
        student.language = language
        student.save()
        print(f"[DEBUG] Updated student {student.username} language to: {student.language}")
        return Response({
            'message': 'Language updated successfully',
            'language': student.language
        }, status=status.HTTP_200_OK)
    except Student.DoesNotExist:
        print(f"[DEBUG] Student with id={student_id} not found")
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

# Check if the keyboard entered answer is correct
@api_view(['POST'])
def check_answer(request):

    student_id = request.data.get('student_id')
    session_id = request.data.get('session_id')
    example_id = request.data.get('example_id')

    # Data for record creation
    date = request.data.get('date')
    duration = request.data.get('duration')

    student_answer = request.data.get('student_answer')
    answer_type = request.data.get('answer_type')
    language = request.data.get('language', '')

    if (not student_id and not session_id) or not example_id or not date or not duration or not answer_type:
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Choose the answer checker based on the answer type
    # Note: verifyAnswer internally calls updateRecord with student_id/session_id
    match answer_type:
        case "inline" | "word":
            isCorrect, continue_with_next = InlineAnswerChecker.verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=session_id)
            pass

        case "fraction":
            isCorrect, continue_with_next = FractionAnswerChecker.verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=session_id)
            pass

        case "variable":
            isCorrect, continue_with_next = VariableAnswerChecker.verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=session_id)
            pass

        case _:
            return Response({'error': 'Invalid answer type'}, status=status.HTTP_400_BAD_REQUEST)

    # Persist detailed attempt log for keyboard-entered answers
    attempt_obj = None
    try:
        student_record = _resolve_student_example_record(student_id, session_id, example_id, date)

        if student_record:
            example_obj = Example.objects.filter(id=example_id).first()
            answer_obj = Answer.objects.filter(example_id=example_id).first()

            input_type_map = {
                'inline': 'INLINE',
                'word': 'WORD',
                'fraction': 'FRAC',
                'variable': 'VAR',
            }
            input_type = input_type_map.get(answer_type, answer_type.upper())

            try:
                duration_value = int(float(duration))
            except (TypeError, ValueError):
                duration_value = 0

            attempt = _create_attempt_log_for_record(
                student_example=student_record,
                example_id=example_id,
                duration=duration_value,
                input_type=input_type,
                language=language,
                action='evaluated',
                is_correct=isCorrect,
                transcription='',
                parsed_answer=student_answer,
                example_text=example_obj.example if example_obj else '',
                correct_answer=answer_obj.answer if answer_obj else '',
                source='text',
                meta={
                    'continue_with_next': continue_with_next,
                    'answer_type': answer_type,
                },
            )

            if attempt:
                attempt_obj = attempt
                def _bg_write_sync(att):
                    try:
                        sync_write_attempt_to_mega(att)
                        retry_pending_write_uploads(limit=5)
                    except Exception as cloud_error:
                        print(f"[ERROR] Background write sync failed for attempt {att.id}: {cloud_error}")

                threading.Thread(target=_bg_write_sync, args=(attempt,), daemon=True).start()

    except Exception as log_error:
        print(f"[ERROR] Failed to log text attempt: {log_error}")

    # Award XP for correct text answers (registered students only)
    xp_data = {}
    if isCorrect and student_id:
        try:
            from .xp_service import award_xp
            xp_data = award_xp(student_id, attempt_obj) or {}
        except Exception as xp_error:
            print(f"[ERROR] Failed to award XP for text attempt: {xp_error}")

    # Update incremental skill mastery (once per completed example)
    # Only task-based practice counts; skills come from the Task, not from the example.
    if continue_with_next and student_id and attempt_obj:
        try:
            from .mastery import update_skill_mastery
            student_example = attempt_obj.student_example
            if student_example.task_id:
                leaf_skill_ids = set(
                    student_example.task.skills.filter(
                        subskills__isnull=True,
                        deleted=False,
                    ).values_list('id', flat=True)
                )
                student_time_ms = student_example.duration
                for skill_id in leaf_skill_ids:
                    update_skill_mastery(
                        student_id=int(student_id),
                        skill_id=skill_id,
                        attempt_number=attempt_obj.attempt_number,
                        solved=bool(isCorrect),
                        student_time_ms=student_time_ms,
                    )
        except Exception as mastery_error:
            print(f"[ERROR] Failed to update skill mastery (text): {mastery_error}")

    return Response({'isCorrect': isCorrect, 'continue_with_next': continue_with_next, **xp_data}, status=status.HTTP_200_OK)


@api_view(['GET'])
def reveal_example_answer(request, example_id):
    """Return the correct answer for an example (called only after 3 failed attempts)."""
    example = get_object_or_404(Example, id=example_id)
    answer = Answer.objects.filter(example=example).first()
    return Response({'answer': answer.answer if answer else ''}, status=status.HTTP_200_OK)


# Get all skill paths from skill ids to be displayed when editing task
@api_view(['GET'])
def get_paths_for_sandbox(request):
    skill_ids = request.GET.getlist('skill_ids', [])  

    if len(skill_ids) == 1 and ',' in skill_ids[0]:
        skill_ids = skill_ids[0].split(',')

    try:
        skill_ids = [int(id) for id in skill_ids] 
        skill_paths = get_skill_paths(skill_ids, False)
        return Response(skill_paths, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Get number of tasks and examples related to the selected skill
@api_view(['GET'])
def get_skill_related_counts(request):
    skill_id = request.GET.get('skill_id')

    skill = get_object_or_404(Skill, id=skill_id)

    task_count = Task.objects.filter(skills=skill).count()

    example_count = ExampleSkill.objects.filter(skill=skill).count()

    data = {
        "task_count": task_count,
        "example_count": example_count
    }

    return Response(data)

@api_view(['POST'])
def save_survey_answer(request):
    question_type = request.data.get('question_type')
    question_text = request.data.get('question_text')
    answer = request.data.get('answer')
    skills = request.data.get('skills')
    student_id = request.data.get('student_id')
    session_id = request.data.get('session_id')
    language = (request.data.get('language') or '').strip()

    if not question_type or not question_text or not answer:
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        feedback = create_survey_feedback(
            question_type=question_type,
            question_text=question_text,
            answer=answer,
            skills=skills,
            student_id=student_id,
            session_id=session_id,
            language=language,
            source='text',
        )
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    sync_result = sync_survey_feedback_to_mega(feedback)
    retry_pending_survey_feedback_uploads(limit=3)

    return Response(
        {
            "feedback_id": feedback.id,
            "mega_uploaded": sync_result.get("uploaded", False),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
def save_example_report(request):
    student, anonymous_session = get_user_identity(request)
    example_id = request.data.get('example_id')
    report_type = request.data.get('report_type')
    note = (request.data.get('note') or '').strip()
    language = (request.data.get('language') or '').strip()

    if not student and not anonymous_session:
        return Response({"error": "Student ID or Session ID is required"}, status=status.HTTP_400_BAD_REQUEST)

    if not example_id or not report_type:
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

    allowed_types = {choice[0] for choice in ExampleReport.REPORT_TYPE_CHOICES}
    if report_type not in allowed_types:
        return Response({"error": "Invalid report type"}, status=status.HTTP_400_BAD_REQUEST)

    example = get_object_or_404(Example.objects.prefetch_related('answers', 'exampleskill_set__skill'), id=example_id)
    correct_answer_obj = example.answers.first()
    skill_ids = list(example.exampleskill_set.values_list('skill_id', flat=True).distinct())
    skill_names = list(Skill.objects.filter(id__in=skill_ids).values_list('name', flat=True))

    report = ExampleReport.objects.create(
        student=student,
        anonymous_session=anonymous_session,
        example=example,
        report_type=report_type,
        note=note,
        input_type=example.input_type or '',
        language=language or '',
        example_text=example.example or '',
        correct_answer=correct_answer_obj.answer if correct_answer_obj else '',
        practiced_skill_ids=skill_ids,
        practiced_skill_names=skill_names,
        meta={},
    )

    sync_result = sync_report_to_mega(report)
    retry_pending_report_uploads(limit=3)

    return Response(
        {
            "report_id": report.id,
            "mega_uploaded": sync_result.get("uploaded", False),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
def save_example_request(request):
    """Student suggestion: what examples they'd like to see added."""
    student, anonymous_session = get_user_identity(request)
    text = (request.data.get('text') or '').strip()
    grade = request.data.get('grade')
    source = request.data.get('source', 'text')

    if not text:
        return Response({'error': 'text is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        grade = int(grade) if grade is not None else None
    except (ValueError, TypeError):
        grade = None

    ExampleRequest.objects.create(
        student=student,
        anonymous_session=anonymous_session,
        grade=grade,
        text=text,
        source=source,
    )
    return Response({'ok': True}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_all_example_requests(request):
    limit = request.query_params.get('limit', 500)
    try:
        limit = max(1, min(int(limit), 2000))
    except (TypeError, ValueError):
        limit = 500

    requests_qs = ExampleRequest.objects.select_related(
        'student', 'anonymous_session'
    ).order_by('-created_at')[:limit]

    data = []
    for req in requests_qs:
        data.append({
            'id': req.id,
            'created_at': req.created_at.isoformat() if req.created_at else None,
            'grade': req.grade,
            'text': req.text,
            'source': req.source,
            'student_id': req.student.id if req.student else None,
            'student_username': req.student.username if req.student else None,
            'anonymous_session_id': str(req.anonymous_session.session_id) if req.anonymous_session else None,
        })

    return Response(data)


@api_view(['GET'])
def get_example_reports(request):
    limit = request.query_params.get('limit', 500)

    try:
        limit = max(1, min(int(limit), 2000))
    except (TypeError, ValueError):
        limit = 500

    reports = ExampleReport.objects.select_related(
        'student',
        'anonymous_session',
        'example__task',
    ).order_by('-created_at')[:limit]

    data = []
    for report in reports:
        meta = report.meta or {}
        data.append(
            {
                "report_id": report.id,
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "report_type": report.report_type,
                "note": report.note,
                "student_id": report.student_id,
                "student_username": report.student.username if report.student_id else '',
                "anonymous_session_id": report.anonymous_session.session_id if report.anonymous_session_id else '',
                "example_id": report.example_id,
                "task_id": report.example.task_id if report.example_id and report.example.task_id else None,
                "task_name": report.example.task.name if report.example_id and report.example.task_id else '',
                "example_text": report.example_text,
                "correct_answer": report.correct_answer,
                "input_type": report.input_type,
                "language": report.language,
                "practiced_skill_ids": report.practiced_skill_ids,
                "practiced_skill_names": report.practiced_skill_names,
                "mega_uploaded": meta.get("mega_uploaded", False),
                "mega_json_url": meta.get("mega_json_url", ""),
                "mega_error": meta.get("mega_error", ""),
                "local_json_name": meta.get("local_json_name", ""),
                "meta": meta,
            }
        )

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_survey_feedbacks(request):
    limit = request.query_params.get('limit', 500)

    try:
        limit = max(1, min(int(limit), 2000))
    except (TypeError, ValueError):
        limit = 500

    feedbacks = SurveyFeedback.objects.select_related(
        'student',
        'anonymous_session',
    ).order_by('-created_at')[:limit]

    data = []
    for feedback in feedbacks:
        meta = feedback.meta or {}
        data.append(
            {
                "feedback_id": feedback.id,
                "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
                "question_type": feedback.question_type,
                "question_text": feedback.question_text,
                "answer": feedback.answer,
                "source": feedback.source,
                "language": feedback.language,
                "student_id": feedback.student_id,
                "student_username": feedback.student.username if feedback.student_id else '',
                "anonymous_session_id": feedback.anonymous_session.session_id if feedback.anonymous_session_id else '',
                "practiced_skill_ids": feedback.practiced_skill_ids,
                "practiced_skill_names": feedback.practiced_skill_names,
                "audio_url": f"/api/survey-feedback-audio/{feedback.id}/" if (
                    feedback.audio_file_path or meta.get("mega_audio_url")
                ) else "",
                "mega_uploaded": meta.get("mega_uploaded", False),
                "mega_json_uploaded": meta.get("mega_json_uploaded", False),
                "mega_audio_uploaded": meta.get("mega_audio_uploaded", False),
                "mega_json_url": meta.get("mega_json_url", ""),
                "mega_audio_url": meta.get("mega_audio_url", ""),
                "mega_error": meta.get("mega_error", "") or meta.get("mega_json_error", "") or meta.get("mega_audio_error", ""),
                "local_json_name": meta.get("local_json_name", ""),
                "meta": meta,
            }
        )

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_survey_feedback_audio(request, feedback_id):
    feedback = get_object_or_404(SurveyFeedback, id=feedback_id)
    cloud_url = (feedback.meta or {}).get('mega_audio_url', '')

    candidate_paths = [feedback.audio_file_path]
    candidate_paths.append(os.path.join(os.getcwd(), feedback.audio_file_path))

    file_path = None
    for path in candidate_paths:
        if _existing_nonempty_file(path):
            file_path = path
            break

    if not file_path:
        if cloud_url:
            response = _temporary_cloud_file_response(
                public_url=cloud_url,
                filename_hint=feedback.audio_file_path or f"survey_feedback_{feedback.id}.wav",
                content_type='audio/wav',
            )
            if response:
                return response
            return redirect(cloud_url)
        return Response({"error": "Audio file not available for this feedback"}, status=status.HTTP_404_NOT_FOUND)

    return FileResponse(open(file_path, 'rb'), content_type='audio/wav')

# Get all grade levels (1-9)
@api_view(['GET'])
def get_grade_levels(request):
    try:
        grade_levels = GradeLevel.objects.all().order_by('grade')
        data = [{"id": gl.id, "grade": gl.grade} for gl in grade_levels]
        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Update grade levels for a skill
@api_view(['PATCH'])
def update_skill_grade_levels(request, skill_id):
    try:
        skill = get_object_or_404(Skill, id=skill_id)
        grade_level_ids = request.data.get('grade_levels', [])
        
        # Update the grade levels
        skill.grade_levels.set(grade_level_ids)
        
        return JsonResponse({
            "id": skill.id,
            "name": skill.name,
            "grade_levels": list(skill.grade_levels.values_list('id', flat=True))
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Get skills by grade level
@api_view(['GET'])
def get_skills_by_grade(request, grade_id):
    try:
        grade = get_object_or_404(GradeLevel, id=grade_id)
        
        # Show only leaf skills for the grade that have at least one example.
        # TASK-type skills are always leaf nodes so they bypass the subskills filter.
        from django.db.models import Count
        skills = Skill.objects.filter(
            grade_levels=grade,
            deleted=False,
            exampleskill__isnull=False,
        ).filter(
            Q(subskills__isnull=True) | Q(skill_type='TASK')
        ).annotate(
            example_count=Count('exampleskill', distinct=True)
        ).distinct().order_by('name')
        
        skills_data = [
            {
                "id": skill.id,
                "name": skill.name,
                "skill_type": skill.skill_type,
                "example_count": skill.example_count,
            }
            for skill in skills
        ]
        
        return JsonResponse(skills_data, safe=False, status=status.HTTP_200_OK)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_task_stats(request, task_id):
    from django.db.models import Count, Avg, Q
    task = get_object_or_404(Task, id=task_id)
    student, anonymous_session = get_user_identity_any(request)

    # --- Leaderboard: top 3 registered students, success_rate >= 60%, sorted by solved count ---
    rows = (
        StudentExample.objects
        .filter(task=task, student__isnull=False)
        .values('student_id', 'student__username')
        .annotate(
            solved=Count('id', filter=Q(solved=True)),
            total=Count('id'),
        )
        .filter(total__gt=0)
        .order_by('-solved')
    )
    leaderboard = []
    for row in rows:
        success_rate = round(row['solved'] / row['total'] * 100)
        if success_rate < 60:
            continue
        leaderboard.append({
            'username': row['student__username'],
            'solved': row['solved'],
            'success_rate': success_rate,
        })
        if len(leaderboard) == 3:
            break

    # --- Global avg time per example (ms, solved only) ---
    global_avg = (
        StudentExample.objects
        .filter(task=task, solved=True, duration__gt=0)
        .aggregate(avg=Avg('duration'))
    )['avg']

    # --- My stats ---
    my_stats = None
    if student or anonymous_session:
        base = StudentExample.objects.filter(task=task)
        base = base.filter(student=student) if student else base.filter(anonymous_session=anonymous_session)

        agg = base.aggregate(
            total=Count('id'),
            solved_count=Count('id', filter=Q(solved=True)),
            avg_time=Avg('duration', filter=Q(solved=True, duration__gt=0)),
        )

        total_examples = task.example_set.count()
        unique_solved = base.filter(solved=True).values('example').distinct().count()
        mastery = round(unique_solved / total_examples * 100) if total_examples > 0 else 0
        success_rate = round(agg['solved_count'] / agg['total'] * 100) if agg['total'] else 0

        my_stats = {
            'solved': agg['solved_count'],
            'total_attempted': agg['total'],
            'success_rate': success_rate,
            'avg_time': round(agg['avg_time'], 1) if agg['avg_time'] else None,
            'mastery': mastery,
            'total_examples': total_examples,
        }

    return JsonResponse({
        'leaderboard': leaderboard,
        'global_avg_time': round(global_avg, 1) if global_avg else None,
        'my_stats': my_stats,
    }, status=200)


@api_view(['GET'])
def get_task_history(request, task_id):
    """Per-session avg time and cumulative mastery for a user on a given task."""
    from datetime import timedelta
    task = get_object_or_404(Task, id=task_id)
    student, anonymous_session = get_user_identity_any(request)
    if not student and not anonymous_session:
        return JsonResponse({'history': []})

    base = StudentExample.objects.filter(task=task)
    base = base.filter(student=student) if student else base.filter(anonymous_session=anonymous_session)

    records = list(base.order_by('date').values('example_id', 'solved', 'duration', 'date', 'practice_session_key'))
    if not records:
        return JsonResponse({'history': []})

    # Group by practice_session_key if available, else fall back to 30-min gap heuristic
    SESSION_GAP = timedelta(minutes=30)
    sessions = []
    keyed = {}   # key -> list of records
    ungrouped = []
    for r in records:
        k = r['practice_session_key']
        if k:
            keyed.setdefault(k, []).append(r)
        else:
            ungrouped.append(r)

    # Sort keyed sessions by their first record's date
    for k, recs in sorted(keyed.items(), key=lambda x: x[1][0]['date']):
        sessions.append(recs)

    # Apply gap heuristic only to legacy records without a key
    if ungrouped:
        current = [ungrouped[0]]
        for r in ungrouped[1:]:
            if r['date'] - current[-1]['date'] > SESSION_GAP:
                sessions.append(current)
                current = [r]
            else:
                current.append(r)
        sessions.append(current)

    # Re-sort all sessions by their start date
    sessions.sort(key=lambda s: s[0]['date'])

    total_examples = task.example_set.count()
    cumulative_solved = set()
    history = []
    for i, session in enumerate(sessions):
        solved_ids = set()
        times = []
        for r in session:
            if r['solved']:
                solved_ids.add(r['example_id'])
                if r['duration'] and r['duration'] > 0:
                    times.append(r['duration'])
        cumulative_solved |= solved_ids
        mastery = round(len(cumulative_solved) / total_examples * 100) if total_examples > 0 else 0
        avg_time = round(sum(times) / len(times), 1) if times else None
        label = session[0]['date'].strftime('%d.%m %H:%M')
        history.append({'session': i + 1, 'label': label, 'avg_time': avg_time, 'mastery': mastery})

    return JsonResponse({'history': history})


def get_task(request, task_id):
    try:
        task = get_object_or_404(Task, id=task_id)
        batch = GeneratedTaskBatch.objects.filter(created_task=task).values('id').first()
        data = {
            "id": task.id,
            "name": task.name,
            "form": task.form,
            "example_count": task.example_set.count(),
            "is_private": task.is_private,
            "generated_batch_id": batch['id'] if batch else None,
        }
        return JsonResponse(data, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_tasks_by_grade(request, grade_id):
    try:
        grade = get_object_or_404(GradeLevel, id=grade_id)
        student_id = request.GET.get('student_id')
        try:
            student_id = int(student_id) if student_id else None
        except (ValueError, TypeError):
            student_id = None

        # Include public tasks + student's own private tasks; exclude other students' private tasks
        from django.db.models import Q
        tasks = Task.objects.filter(
            grade_levels=grade,
            example__isnull=False,
        ).filter(
            Q(is_private=False) | Q(is_private=True, owner_student_id=student_id)
        ).distinct().order_by('name')

        # Build batch_id lookup: task_id → batch_id (one query)
        task_ids = [t.id for t in tasks]
        batch_map = {
            b['created_task_id']: b['id']
            for b in GeneratedTaskBatch.objects.filter(created_task_id__in=task_ids).values('created_task_id', 'id')
        }

        data = [
            {
                "id": task.id,
                "name": task.name,
                "form": task.form,
                "example_count": task.example_set.count(),
                "is_private": task.is_private,
                "generated_batch_id": batch_map.get(task.id),
                "owner_teacher_id": task.owner_teacher_id,
            }
            for task in tasks
        ]

        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================
# Analytics & Skill Tracking
# ================================

# Per-student stats aggregated by skill (no new tables; computed on demand)
@api_view(['GET'])
def get_student_skill_stats(request, student_id):
    """
    Returns analytics for skills that the student has practiced.
    
    Key change: Mastery is now calculated ONLY for the specific skill combinations
    that the student selected during practice sessions (practiced_skills),
    rather than separately for each parent skill in the hierarchy.
    
    For example, if a student practices "addition up to 10" (selecting both 
    "addition" and "up to 10" skills), the mastery will be tracked for that
    specific combination, not separately for "addition", "arithmetic", "up to 10", etc.
    """
    try:
        # Optional: filter by subtree root skill
        root_skill_id = request.GET.get('root_skill_id')

        # Get all unique skill IDs that were explicitly selected for practice
        # (from the practiced_skills ManyToMany relationship)
        practiced_skill_ids = StudentExample.objects.filter(
            student_id=student_id
        ).values_list('practiced_skills__id', flat=True).distinct()

        # Remove None values (in case some StudentExamples have no practiced_skills)
        practiced_skill_ids = [sid for sid in practiced_skill_ids if sid is not None]

        if not practiced_skill_ids:
            # Fallback to old behavior if no practiced_skills are set
            # (for backward compatibility with old data)
            practiced_skill_ids = ExampleSkill.objects.filter(
                example__studentexample__student_id=student_id
            ).values_list('skill_id', flat=True).distinct()

        results = []
        for skill_id in practiced_skill_ids:
            # Get all StudentExample records where this skill was in practiced_skills
            records = StudentExample.objects.filter(
                student_id=student_id,
                practiced_skills__id=skill_id
            ).distinct()
            
            if not records.exists():
                continue
            
            skill = Skill.objects.get(id=skill_id)
            examples_practiced = records.count()
            solved_count = records.filter(solved=True).count()
            skip_count = records.filter(skipped=True).count()
            total_attempts = records.aggregate(Sum('attempts'))['attempts__sum'] or 0
            avg_duration = records.aggregate(Avg('duration'))['duration__avg'] or 0
            last_practiced = records.aggregate(Max('date'))['date__max']
            
            results.append({
                'skill_id': skill_id,
                'skill_name': skill.name,
                'examples_practiced': examples_practiced,
                'solved_count': solved_count,
                'skip_count': skip_count,
                'total_attempts': total_attempts,
                'avg_duration': avg_duration,
                'last_practiced': last_practiced,
            })

        # If filtering by a subtree, keep only skills under that subtree
        if root_skill_id:
            try:
                root = Skill.objects.get(id=int(root_skill_id))
            except Exception:
                return Response({"error": "Invalid root_skill_id"}, status=status.HTTP_400_BAD_REQUEST)

            # Collect all descendants (including root)
            descendant_ids = set()
            stack = [root]
            while stack:
                node = stack.pop()
                if node.id not in descendant_ids:
                    descendant_ids.add(node.id)
                    stack.extend(list(node.subskills.filter(deleted=False)))

            results = [r for r in results if r['skill_id'] in descendant_ids]

        # Build response with derived metrics
        now = timezone.now()
        tau_seconds = int(request.GET.get('tau_seconds', '86400'))  # ~1 day default

        # Batch-load EWMA mastery state for this student
        from .mastery import compute_final_mastery
        from .models import SkillMastery
        skill_ids_in_results = [r['skill_id'] for r in results]
        mastery_map = {
            m.skill_id: m
            for m in SkillMastery.objects.filter(student_id=student_id, skill_id__in=skill_ids_in_results)
        }

        data = []
        for row in results:
            practiced = row['examples_practiced'] or 0
            skipped = row['skip_count'] or 0
            denom = max(practiced - skipped, 1)
            accuracy = (row['solved_count'] or 0) / denom
            avg_attempts = (row['total_attempts'] or 0) / practiced if practiced else 0

            # Bayesian mastery with Beta prior (2,2)
            successes = row['solved_count'] or 0
            failures = max(denom - successes, 0)
            alpha = 2 + successes
            beta = 2 + failures
            mastery_mean = alpha / (alpha + beta)

            # Wilson-like lower bound approximation for prioritization
            n = successes + failures
            p = successes / n if n > 0 else 0.0
            z = 1.96
            denom_w = 1 + z*z/n if n > 0 else 1
            center = p + z*z/(2*n) if n > 0 else 0
            margin = z*math.sqrt((p*(1-p) + z*z/(4*n))/n) if n > 0 else 0
            wilson_lower = max(0.0, (center - margin)/denom_w) if n > 0 else 0.0

            # Freshness factor (larger when not practiced recently)
            last = row['last_practiced']
            if last:
                dt = (now - last).total_seconds()
                freshness = 1 - math.exp(-dt / max(tau_seconds, 1))
            else:
                freshness = 1.0

            # Next practice weight: focus on weak + stale skills
            next_weight = (1 - wilson_lower) * freshness

            # EWMA mastery (accuracy + fluency, confidence-scaled)
            sm = mastery_map.get(row['skill_id'])
            final_mastery = round(compute_final_mastery(sm)['final_mastery'], 3) if sm else None

            data.append({
                'skill_id': row['skill_id'],
                'skill_name': row['skill_name'],
                'examples_practiced': practiced,
                'solved_count': row['solved_count'] or 0,
                'skip_count': skipped,
                'total_attempts': row['total_attempts'] or 0,
                'avg_attempts_per_example': round(avg_attempts, 3),
                'avg_duration_ms': row['avg_duration'] or 0,
                'last_practiced': row['last_practiced'],
                'accuracy': round(accuracy, 3),
                'mastery_mean': round(mastery_mean, 3),
                'wilson_lower': round(wilson_lower, 3),
                'next_weight': round(next_weight, 3),
                'observations': n,
                'final_mastery': final_mastery,
            })

        # Sort by lowest accuracy first by default
        order = request.GET.get('order', 'accuracy_asc')
        if order == 'accuracy_desc':
            data.sort(key=lambda x: x['accuracy'], reverse=True)
        elif order == 'recent':
            data.sort(key=lambda x: (x['last_practiced'] is None, x['last_practiced']), reverse=True)
        else:
            data.sort(key=lambda x: x['accuracy'])

        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Get student stats grouped by skill COMBINATIONS (not individual skills)
# This shows what the student actually practiced together (e.g., "Sčítání + Celé čísla + Do 100")
@api_view(['GET'])
def get_student_skill_combinations(request, student_id):
    """
    Returns analytics grouped by practiced skill combinations.
    
    Instead of showing individual skills separately, this groups records by
    the exact combination of skills that were practiced together.
    
    Example: If student practiced "Sčítání + Celé čísla + Do 100" together,
    it will show as one row, not three separate rows.
    """
    try:
        from collections import defaultdict
        
        # Get all StudentExample records for this student
        records = StudentExample.objects.filter(
            student_id=student_id
        ).prefetch_related('practiced_skills')
        
        if not records.exists():
            return JsonResponse([], safe=False, status=status.HTTP_200_OK)
        
        # Group records by skill combination (tuple of skill IDs)
        combinations = defaultdict(list)
        
        for record in records:
            # Get sorted tuple of skill IDs (for consistent grouping)
            skill_ids = tuple(sorted(record.practiced_skills.values_list('id', flat=True)))
            
            # Skip records with no practiced_skills (old data)
            if not skill_ids:
                continue
                
            combinations[skill_ids].append(record)
        
        # Calculate stats for each combination
        now = timezone.now()
        tau_seconds = int(request.GET.get('tau_seconds', '86400'))

        # Batch-load EWMA mastery for all skills this student has practiced
        from .mastery import compute_final_mastery as _compute_final_mastery
        from .models import SkillMastery as _SkillMastery
        all_skill_ids_in_combos = {sid for skill_ids in combinations for sid in skill_ids}
        combo_mastery_map = {
            m.skill_id: m
            for m in _SkillMastery.objects.filter(student_id=student_id, skill_id__in=all_skill_ids_in_combos)
        }

        data = []
        for skill_ids, combo_records in combinations.items():
            # Get skill names
            skills = Skill.objects.filter(id__in=skill_ids).values('id', 'name')
            skill_map = {s['id']: s['name'] for s in skills}
            skill_names = [skill_map[sid] for sid in skill_ids]
            
            # Calculate metrics
            examples_practiced = len(combo_records)
            solved_count = sum(1 for r in combo_records if r.solved)
            skip_count = sum(1 for r in combo_records if r.skipped)
            total_attempts = sum(r.attempts for r in combo_records)
            avg_duration = sum(r.duration for r in combo_records) / len(combo_records) if combo_records else 0
            last_practiced = max(r.date for r in combo_records)
            
            # Accuracy & mastery
            denom = max(examples_practiced - skip_count, 1)
            accuracy = solved_count / denom
            avg_attempts = total_attempts / examples_practiced if examples_practiced else 0
            
            # Bayesian mastery
            successes = solved_count
            failures = max(denom - successes, 0)
            alpha = 2 + successes
            beta = 2 + failures
            mastery_mean = alpha / (alpha + beta)
            
            # Wilson lower bound
            n = successes + failures
            p = successes / n if n > 0 else 0.0
            z = 1.96
            denom_w = 1 + z*z/n if n > 0 else 1
            center = p + z*z/(2*n) if n > 0 else 0
            margin = z*math.sqrt((p*(1-p) + z*z/(4*n))/n) if n > 0 else 0
            wilson_lower = max(0.0, (center - margin)/denom_w) if n > 0 else 0.0
            
            # Freshness
            dt = (now - last_practiced).total_seconds()
            freshness = 1 - math.exp(-dt / max(tau_seconds, 1))
            
            # Next practice weight
            next_weight = (1 - wilson_lower) * freshness

            # EWMA mastery: average final_mastery across skills in this combination
            combo_sm_values = [
                _compute_final_mastery(combo_mastery_map[sid])['final_mastery']
                for sid in skill_ids if sid in combo_mastery_map
            ]
            final_mastery = round(sum(combo_sm_values) / len(combo_sm_values), 3) if combo_sm_values else None

            data.append({
                'skill_ids': list(skill_ids),
                'skill_names': skill_names,
                'combination_display': ' + '.join(skill_names),
                'examples_practiced': examples_practiced,
                'solved_count': solved_count,
                'skip_count': skip_count,
                'total_attempts': total_attempts,
                'avg_attempts_per_example': round(avg_attempts, 3),
                'avg_duration_ms': round(avg_duration, 3),
                'last_practiced': last_practiced,
                'accuracy': round(accuracy, 3),
                'mastery_mean': round(mastery_mean, 3),
                'wilson_lower': round(wilson_lower, 3),
                'next_weight': round(next_weight, 3),
                'observations': n,
                'final_mastery': final_mastery,
            })
        
        # Add unpracticed grade skills at mastery=0 so recommendations cover full grade
        try:
            student = Student.objects.filter(id=student_id).first()
            if student and student.grade:
                grade_level = GradeLevel.objects.filter(grade=student.grade).first()
                if grade_level:
                    from django.db.models import Q
                    grade_skills = Skill.objects.filter(
                        grade_levels=grade_level,
                        deleted=False,
                        exampleskill__isnull=False,
                    ).filter(
                        Q(subskills__isnull=True) | Q(skill_type='TASK')
                    ).distinct()

                    practiced_skill_ids = set()
                    for item in data:
                        practiced_skill_ids.update(item['skill_ids'])

                    for skill in grade_skills:
                        if skill.id not in practiced_skill_ids:
                            data.append({
                                'skill_ids': [skill.id],
                                'skill_names': [skill.name],
                                'combination_display': skill.name,
                                'examples_practiced': 0,
                                'solved_count': 0,
                                'skip_count': 0,
                                'total_attempts': 0,
                                'avg_attempts_per_example': 0,
                                'avg_duration_ms': 0,
                                'last_practiced': None,
                                'accuracy': 0,
                                'mastery_mean': 0,
                                'wilson_lower': 0,
                                'next_weight': 1.0,
                                'observations': 0,
                                'final_mastery': None,
                            })
        except Exception:
            pass  # Don't break recommendation if grade lookup fails

        # Sort by next_weight (descending) - most important to practice first
        data.sort(key=lambda x: x['next_weight'], reverse=True)
        
        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Global example quality stats; flags potentially problematic examples
@api_view(['GET'])
def get_group_example_stats(request):
    try:
        min_records = int(request.GET.get('min_records', '10'))
        flag_threshold = float(request.GET.get('flag_threshold', '0.5'))  # accuracy below threshold => flag
        limit = int(request.GET.get('limit', '100'))

        qs = StudentExample.objects.values(
            'example_id',
            'example__example',
            'example__input_type',
        ).annotate(
            records=Count('id'),
            solved_count=Count('id', filter=Q(solved=True)),
            skip_count=Count('id', filter=Q(skipped=True)),
            total_attempts=Sum('attempts'),
            avg_duration=Avg('duration'),
            last_practiced=Max('date'),
        )

        data = []
        for row in qs:
            practiced = row['records'] or 0
            skipped = row['skip_count'] or 0
            denom = max(practiced - skipped, 1)
            accuracy = (row['solved_count'] or 0) / denom

            # Get skills for the example (names & ids)
            skills = list(ExampleSkill.objects.filter(example_id=row['example_id'])
                          .values('skill_id', 'skill__name'))

            item = {
                'example_id': row['example_id'],
                'example': row['example__example'],
                'input_type': row['example__input_type'],
                'records': practiced,
                'solved_count': row['solved_count'] or 0,
                'skip_count': skipped,
                'total_attempts': row['total_attempts'] or 0,
                'avg_duration_ms': row['avg_duration'] or 0,
                'last_practiced': row['last_practiced'],
                'accuracy': round(accuracy, 3),
                'skills': skills,
                'flagged': practiced >= min_records and accuracy < flag_threshold,
            }
            data.append(item)

        # Order: most problematic first (lowest accuracy with enough data), then by records desc
        data.sort(key=lambda x: (not (x['records'] >= min_records), x['accuracy'], -x['records']))
        data = data[:limit]

        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Global skill stats across all students
@api_view(['GET'])
def get_group_skill_stats(request):
    try:
        qs = StudentExample.objects.values(
            'example__exampleskill__skill_id',
            'example__exampleskill__skill__name',
        ).annotate(
            records=Count('id'),
            solved_count=Count('id', filter=Q(solved=True)),
            skip_count=Count('id', filter=Q(skipped=True)),
            total_attempts=Sum('attempts'),
            avg_duration=Avg('duration'),
            last_practiced=Max('date'),
        )

        data = []
        for row in qs:
            practiced = row['records'] or 0
            skipped = row['skip_count'] or 0
            denom = max(practiced - skipped, 1)
            accuracy = (row['solved_count'] or 0) / denom
            avg_attempts = (row['total_attempts'] or 0) / practiced if practiced else 0

            data.append({
                'skill_id': row['example__exampleskill__skill_id'],
                'skill_name': row['example__exampleskill__skill__name'],
                'records': practiced,
                'solved_count': row['solved_count'] or 0,
                'skip_count': skipped,
                'total_attempts': row['total_attempts'] or 0,
                'avg_attempts_per_example': round(avg_attempts, 3),
                'avg_duration_ms': row['avg_duration'] or 0,
                'last_practiced': row['last_practiced'],
                'accuracy': round(accuracy, 3),
            })

        # Sort by lowest accuracy first
        data.sort(key=lambda x: x['accuracy'])

        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Get list of all students with their overall stats
@api_view(['GET'])
def get_all_students_stats(request):
    try:
        students = Student.objects.all().order_by('username')
        data = []
        
        for student in students:
            records = StudentExample.objects.filter(student=student)
            total_examples = records.count()
            if total_examples == 0:
                continue
            solved = records.filter(solved=True).count()
            skipped = records.filter(skipped=True).count()
            total_attempts = records.aggregate(Sum('attempts'))['attempts__sum'] or 0
            avg_duration = records.aggregate(Avg('duration'))['duration__avg'] or 0
            last_practiced = records.aggregate(Max('date'))['date__max']
            
            denom = max(total_examples - skipped, 1)
            accuracy = solved / denom if denom > 0 else 0
            
            data.append({
                'student_id': student.id,
                'username': student.username,
                'total_examples': total_examples,
                'solved_count': solved,
                'skip_count': skipped,
                'total_attempts': total_attempts,
                'avg_duration_ms': round(avg_duration, 1),
                'last_practiced': last_practiced,
                'accuracy': round(accuracy, 3),
            })
        
        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_all_anonymous_sessions_stats(request):
    try:
        qs = ExampleAttempt.objects.filter(
            anonymous_session__isnull=False
        ).values(
            'anonymous_session__session_id',
        ).annotate(
            total_attempts=Count('id'),
            evaluated_count=Count('id', filter=Q(action='evaluated')),
            correct_count=Count('id', filter=Q(action='evaluated', is_correct=True)),
            avg_duration=Avg('duration'),
            last_activity=Max('created_at'),
            distinct_examples=Count('example_id', distinct=True),
        ).order_by('-last_activity')

        data = []
        for row in qs:
            evaluated_count = row['evaluated_count'] or 0
            accuracy = (row['correct_count'] / evaluated_count) if evaluated_count else 0

            session_id = row['anonymous_session__session_id']
            masked = f"anonym{session_id[:6]}" if session_id else 'anonymunknown'

            data.append({
                'session_id': session_id,
                'display_name': masked,
                'total_attempts': row['total_attempts'] or 0,
                'evaluated_count': evaluated_count,
                'correct_count': row['correct_count'] or 0,
                'accuracy': round(accuracy, 3),
                'avg_duration_ms': row['avg_duration'] or 0,
                'last_activity': row['last_activity'],
                'distinct_examples': row['distinct_examples'] or 0,
            })

        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ──────────────────────────────────────────────────────────────────────────────
# Admin: activity feed + teachers list + publish teacher task
# ──────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def admin_classroom_students(request, classroom_id):
    memberships = ClassroomStudent.objects.filter(
        classroom_id=classroom_id
    ).select_related('student').order_by('student__username')
    return Response([
        {'id': m.student.id, 'username': m.student.username}
        for m in memberships
    ])


@api_view(['GET'])
def admin_task_examples(request, task_id):
    try:
        task = Task.objects.prefetch_related('example_set__answers').get(id=task_id)
    except Task.DoesNotExist:
        return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    data = []
    for ex in task.example_set.all():
        data.append({
            'id': ex.id,
            'example': ex.example,
            'input_type': ex.input_type,
            'answers': [a.answer for a in ex.answers.all()],
        })
    return Response(data)


@api_view(['POST'])
def admin_publish_teacher_task(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({'error': 'Task not found.'}, status=status.HTTP_404_NOT_FOUND)

    grade_ids = request.data.get('grade_ids', [])

    with transaction.atomic():
        task.owner_teacher = None
        task.is_private = False
        task.save(update_fields=['owner_teacher', 'is_private'])

        if grade_ids:
            grades = GradeLevel.objects.filter(grade__in=grade_ids)
            task.grade_levels.set(grades)

    return Response({
        'task_id': task.id,
        'task_name': task.name,
        'grade_levels': list(task.grade_levels.values_list('grade', flat=True)),
    })

@api_view(['GET'])
def get_recent_activity(request):
    try:
        limit = min(int(request.GET.get('limit', 100)), 500)
    except (TypeError, ValueError):
        limit = 100
    attempts = ExampleAttempt.objects.select_related(
        'student', 'anonymous_session'
    ).order_by('-created_at')[:limit]
    data = []
    for a in attempts:
        if a.student:
            user_type = 'student'
            user_label = a.student.username
        else:
            sid = a.anonymous_session.session_id if a.anonymous_session else ''
            user_type = 'anonymous'
            user_label = sid[:8] + '...'
        data.append({
            'id': a.id,
            'created_at': a.created_at,
            'user_type': user_type,
            'user_label': user_label,
            'example_text': a.example_text,
            'action': a.action,
            'is_correct': a.is_correct,
            'duration': a.duration,
            'source': a.source,
        })
    return Response(data)


@api_view(['GET'])
def get_all_teachers(request):
    teachers = Teacher.objects.prefetch_related('classrooms').order_by('-created_at')
    data = []
    for t in teachers:
        classrooms = list(t.classrooms.all())
        student_ids = ClassroomStudent.objects.filter(
            classroom__in=classrooms
        ).values_list('student_id', flat=True).distinct()

        classrooms_data = []
        for c in classrooms:
            assignments = ClassroomTask.objects.filter(
                classroom=c
            ).select_related('task').order_by('assigned_at')
            classrooms_data.append({
                'id': c.id,
                'name': c.name,
                'student_count': ClassroomStudent.objects.filter(classroom=c).count(),
                'tasks': [
                    {
                        'id': a.task.id,
                        'name': a.task.name,
                        'is_homework': a.is_homework,
                        'assigned_at': a.assigned_at,
                        'grade_levels': list(a.task.grade_levels.values_list('grade', flat=True)),
                        'generation_prompt': a.task.generation_prompt,
                        'generation_params': a.task.generation_params,
                    }
                    for a in assignments
                ],
            })

        data.append({
            'id': t.id,
            'first_name': t.first_name,
            'last_name': t.last_name,
            'email': t.email,
            'created_at': t.created_at,
            'classroom_count': len(classrooms),
            'student_count': len(set(student_ids)),
            'classrooms': classrooms_data,
        })
    return Response(data)


# ──────────────────────────────────────────────────────────────────────────────
# Bulk task/example import
# ──────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
def bulk_import_tasks(request):
    """
    Bulk-create tasks with examples from a JSON payload.

    Expected format:
    {
      "tasks": [
        {
          "task_name": "Sčítanie do 10",
          "task_form": "classic",
          "skill_ids": [1, 3],
          "grade_ids": [1, 2],
          "examples": [
            {
              "example": "3 + 4 =",
              "input_type": "INLINE",
              "answer": "7"
            }
          ]
        }
      ]
    }
    """
    tasks_data = request.data.get('tasks', [])
    if not tasks_data:
        return Response({"error": "No tasks provided."}, status=status.HTTP_400_BAD_REQUEST)

    results = []

    for task_data in tasks_data:
        task_name = task_data.get('task_name', '').strip()
        task_form = task_data.get('task_form', 'classic')
        skill_ids = task_data.get('skill_ids', [])
        grade_ids = task_data.get('grade_ids', [])
        examples_data = task_data.get('examples', [])

        if not task_name:
            results.append({"task_name": task_name, "status": "skipped", "reason": "empty name"})
            continue

        skill_name = task_data.get("skill_name", "").strip()

        # skill_name auto-creates a TASK leaf skill if not exists
        if skill_name and not skill_ids:
            _grades = GradeLevel.objects.filter(id__in=grade_ids) if grade_ids else []
            _skill_obj, _ = Skill.objects.get_or_create(
                name=skill_name,
                defaults={"skill_type": "TASK", "height": 0, "deleted": False, "parent_skill": None},
            )
            if _grades:
                _skill_obj.grade_levels.add(*_grades)
            skill_ids = [_skill_obj.id]

        if not skill_ids:
            results.append({"task_name": task_name, "status": "skipped", "reason": "no skill_ids or skill_name"})
            continue

        skills = Skill.objects.filter(id__in=skill_ids)
        if not skills.exists():
            results.append({"task_name": task_name, "status": "skipped", "reason": "no valid skills found"})
            continue

        with transaction.atomic():
            task_instance, created = Task.objects.get_or_create(
                name=task_name,
                defaults={'form': task_form},
            )
            if not created:
                task_instance.form = task_form
                task_instance.save()

            task_instance.skills.add(*skills)

            if grade_ids:
                grades = GradeLevel.objects.filter(id__in=grade_ids)
                task_instance.grade_levels.add(*grades)

            example_count = 0
            for ex_data in examples_data:
                example_text = ex_data.get('example', '').strip()
                input_type = ex_data.get('input_type', '').strip()
                answer_text = ex_data.get('answer', '').strip()
                steps = ex_data.get('steps', [])

                if not example_text or not input_type:
                    continue

                example_instance = Example.objects.create(
                    example=example_text,
                    input_type=input_type,
                    task=task_instance,
                )

                if answer_text:
                    Answer.objects.create(example=example_instance, answer=answer_text)

                for skill in skills:
                    ExampleSkill.objects.create(example=example_instance, skill=skill)

                for idx, step_text in enumerate(steps, start=1):
                    if step_text:
                        Step.objects.create(example=example_instance, text=step_text, order=idx)

                example_count += 1

            create_skill_relations(skill_ids)

        results.append({
            "task_name": task_name,
            "task_id": task_instance.id,
            "status": "created" if created else "updated",
            "examples_added": example_count,
        })

    return Response({"results": results}, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# Bulk CSV export – DKT-ready format
# ──────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def export_attempts_csv(request):
    """
    Export all ExampleAttempt records as CSV suitable for DKT pipelines.

    Query params (all optional):
      ?student_id=5          – filter by student
      ?session_id=abc123     – filter by anonymous session
      ?action=evaluated      – filter by action (default: evaluated only)
      ?all_actions=true      – include all actions, not just evaluated
      ?date_from=2026-01-01  – only attempts after this date
      ?date_to=2026-12-31    – only attempts before this date
    """
    from django.http import HttpResponse as DjangoHttpResponse

    qs = ExampleAttempt.objects.select_related(
        'student', 'anonymous_session', 'example'
    ).order_by('created_at')

    student_id = request.query_params.get('student_id')
    session_id = request.query_params.get('session_id')
    action_filter = request.query_params.get('action', 'evaluated')
    all_actions = request.query_params.get('all_actions', '').lower() == 'true'
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')

    if student_id:
        qs = qs.filter(student_id=student_id)
    if session_id:
        qs = qs.filter(anonymous_session__session_id=session_id)
    if not all_actions:
        qs = qs.filter(action=action_filter)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    buf = io.StringIO()
    writer = csv.writer(buf)

    header = [
        'timestamp', 'user_type', 'user_id', 'example_id', 'example_text',
        'skill_ids', 'skill_names', 'input_type', 'is_correct', 'attempt_number',
        'duration_ms', 'transcription', 'parsed_answer', 'correct_answer',
        'action', 'source', 'language', 'confidence', 'audio_file_path',
    ]
    writer.writerow(header)

    for att in qs.iterator(chunk_size=500):
        user_type = 'student' if att.student_id else 'anonymous'
        user_id = str(att.student_id) if att.student_id else (
            att.anonymous_session.session_id if att.anonymous_session else ''
        )
        confidence = ''
        if isinstance(att.meta, dict):
            confidence = att.meta.get('azure_confidence', '')

        writer.writerow([
            att.created_at.isoformat(),
            user_type,
            user_id,
            att.example_id,
            att.example_text,
            pyjson.dumps(att.practiced_skill_ids),
            pyjson.dumps(att.practiced_skill_names, ensure_ascii=False),
            att.input_type,
            att.is_correct,
            att.attempt_number,
            att.duration,
            att.transcription,
            att.parsed_answer,
            att.correct_answer,
            att.action,
            att.source,
            att.language,
            confidence,
            att.audio_file_path,
        ])

    csv_response = DjangoHttpResponse(buf.getvalue(), content_type='text/csv')
    csv_response['Content-Disposition'] = 'attachment; filename="attempts_export.csv"'
    return csv_response


# ─────────────────────────── Gamification API ────────────────────────────────

@api_view(['GET'])
def get_leaderboard(request):
    """Top 20 registered students ranked by XP."""
    from .models import Badge, StudentBadge
    import math

    top_students = (
        Student.objects
        .filter(total_xp__gt=0)
        .order_by('-total_xp', 'id')[:20]
    )

    result = []
    for i, student in enumerate(top_students, start=1):
        solved_count = ExampleAttempt.objects.filter(student=student, is_correct=True).count()
        result.append({
            'rank': i,
            'student_id': student.id,
            'username': student.username,
            'total_xp': student.total_xp,
            'level': student.level,
            'current_streak': student.current_streak,
            'solved_count': solved_count,
        })

    return Response(result)


@api_view(['GET'])
def get_leaderboard_accuracy(request):
    """Top 20 registered students ranked by accuracy (min 10 attempts to qualify)."""
    from django.db.models import Count, Case, When, IntegerField, FloatField, ExpressionWrapper, F

    top_students = (
        Student.objects
        .annotate(
            total_attempts=Count('exampleattempt'),
            correct_attempts=Count(Case(When(exampleattempt__is_correct=True, then=1), output_field=IntegerField())),
        )
        .filter(total_attempts__gte=10)
        .annotate(
            accuracy=ExpressionWrapper(
                F('correct_attempts') * 1.0 / F('total_attempts'),
                output_field=FloatField()
            )
        )
        .order_by('-accuracy', '-correct_attempts', 'id')[:20]
    )

    result = []
    for i, student in enumerate(top_students, start=1):
        result.append({
            'rank': i,
            'student_id': student.id,
            'username': student.username,
            'total_xp': student.total_xp,
            'level': student.level,
            'current_streak': student.current_streak,
            'solved_count': student.correct_attempts,
            'accuracy': round(student.accuracy, 4),
        })

    return Response(result)


@api_view(['GET'])
def get_leaderboard_by_grade(request):
    """Top 20 students of the same grade, ranked by level then XP."""
    grade = request.query_params.get('grade')
    if not grade:
        return Response({'error': 'grade parameter required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        grade = int(grade)
    except (ValueError, TypeError):
        return Response({'error': 'grade must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

    top_students = (
        Student.objects
        .filter(grade=grade, total_xp__gt=0)
        .annotate(solved_count=Count('example_attempts', filter=Q(example_attempts__is_correct=True)))
        .order_by('-level', '-total_xp', 'id')[:20]
    )

    result = []
    for i, student in enumerate(top_students, start=1):
        result.append({
            'rank': i,
            'student_id': student.id,
            'username': student.username,
            'total_xp': student.total_xp,
            'level': student.level,
            'current_streak': student.current_streak,
            'solved_count': student.solved_count,
            'grade': student.grade,
        })

    return Response(result)


@api_view(['GET'])
def get_student_gamification_stats(request, student_id):
    """XP, level, streak, badges and leaderboard rank for one student."""
    import math

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    from .models import StudentBadge

    badges = (
        StudentBadge.objects
        .filter(student=student)
        .select_related('badge')
        .order_by('-earned_at')
    )
    badge_list = [
        {
            'key': sb.badge.key,
            'name': sb.badge.name,
            'icon': sb.badge.icon,
            'category': sb.badge.category,
            'description': sb.badge.description,
            'earned_at': sb.earned_at.isoformat(),
        }
        for sb in badges
    ]

    rank = Student.objects.filter(total_xp__gt=student.total_xp).count() + 1
    solved_count = ExampleAttempt.objects.filter(student=student, is_correct=True).count()

    # XP thresholds for current level (for progress bar)
    lvl = student.level
    level_xp_start = (lvl - 1) ** 2 * 50
    level_xp_end = lvl ** 2 * 50

    return Response({
        'total_xp': student.total_xp,
        'level': student.level,
        'current_streak': student.current_streak,
        'longest_streak': student.longest_streak,
        'rank': rank,
        'badges': badge_list,
        'solved_count': solved_count,
        'level_xp_start': level_xp_start,
        'level_xp_end': level_xp_end,
        'grade': student.grade,
        'grade_change_used': student.grade_change_used,
    })


@api_view(['GET'])
def get_all_badges(request):
    """All badges with metadata; optionally annotate which ones a student has earned."""
    from .models import Badge, StudentBadge

    student_id = request.query_params.get('student_id')
    earned_keys = set()
    if student_id:
        try:
            st = Student.objects.get(id=student_id)
            earned_keys = set(
                StudentBadge.objects.filter(student=st).values_list('badge__key', flat=True)
            )
        except Student.DoesNotExist:
            pass

    badges = Badge.objects.all().order_by('category', 'xp_reward')
    result = [
        {
            'key': b.key,
            'name': b.name,
            'description': b.description,
            'icon': b.icon,
            'category': b.category,
            'xp_reward': b.xp_reward,
            'earned': b.key in earned_keys,
        }
        for b in badges
    ]
    return Response(result)


# ─────────────────────────────────────────────────────────────────────────────
# AI Example Generation — Phase 1 (System 1: AI Free Hand)
# ─────────────────────────────────────────────────────────────────────────────

def _grade_to_group(grade: int) -> int:
    if grade <= 3:
        return 1
    if grade <= 6:
        return 2
    return 3


def _serialize_batch(batch):
    survey_data = None
    if hasattr(batch, 'survey'):
        s = batch.survey
        survey_data = {
            'q1_as_requested': s.q1_as_requested,
            'q2_solvable_display': s.q2_solvable_display,
            'q3_difficulty': s.q3_difficulty,
            'q4_has_errors': s.q4_has_errors,
            'q5_satisfied': s.q5_satisfied,
            'created_at': s.created_at.isoformat(),
        }
    return {
        'id': batch.id,
        'grade': batch.grade,
        'grade_group': batch.grade_group,
        'generation_mode': batch.generation_mode,
        'description': batch.description,
        'raw_json': batch.raw_json,
        'status': batch.status,
        'rejection_note': batch.rejection_note,
        'created_task_id': batch.created_task_id,
        'created_at': batch.created_at.isoformat(),
        'reviewed_at': batch.reviewed_at.isoformat() if batch.reviewed_at else None,
        'student_id': batch.student_id,
        'student_username': batch.student.username if batch.student else None,
        'survey': survey_data,
    }


DAILY_GENERATION_LIMIT = 5


@api_view(['GET'])
def generation_quota(request):
    """Return today's generation usage for the student."""
    student_id = request.GET.get('student_id')
    if not student_id:
        return Response({'used': 0, 'limit': DAILY_GENERATION_LIMIT, 'remaining': DAILY_GENERATION_LIMIT})
    try:
        student_id = int(student_id)
    except (ValueError, TypeError):
        return Response({'used': 0, 'limit': DAILY_GENERATION_LIMIT, 'remaining': DAILY_GENERATION_LIMIT})

    today = timezone.now().date()
    used = GeneratedTaskBatch.objects.filter(
        student_id=student_id,
        created_at__date=today,
    ).count()
    remaining = max(0, DAILY_GENERATION_LIMIT - used)
    return Response({'used': used, 'limit': DAILY_GENERATION_LIMIT, 'remaining': remaining})


@api_view(['POST'])
def generate_examples(request):
    """
    System 1: AI Free Hand.
    Calls Gemini with the student's description and returns generated examples.
    Requires a logged-in student (no anonymous sessions).
    """
    from .generators.ai_free_generator import generate_free

    student_id = request.data.get('student_id')
    if not student_id:
        return Response({'error': 'Login required to generate examples.'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Daily limit check
    today = timezone.now().date()
    used_today = GeneratedTaskBatch.objects.filter(
        student=student,
        created_at__date=today,
    ).count()
    if used_today >= DAILY_GENERATION_LIMIT:
        return Response(
            {'error': f'Denný limit {DAILY_GENERATION_LIMIT} generovaní bol dosiahnutý. Skús zajtra.', 'quota_exceeded': True},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    description = (request.data.get('description') or '').strip()
    if not description:
        return Response({'error': 'description is required'}, status=status.HTTP_400_BAD_REQUEST)

    grade = student.grade
    if not grade:
        grade = request.data.get('grade')
        try:
            grade = int(grade)
        except (TypeError, ValueError):
            return Response({'error': 'grade is required'}, status=status.HTTP_400_BAD_REQUEST)

    example_request_id = request.data.get('example_request_id')
    example_request_obj = None
    if example_request_id:
        try:
            example_request_obj = ExampleRequest.objects.get(id=example_request_id)
        except ExampleRequest.DoesNotExist:
            pass

    try:
        raw_json = generate_free(description, grade)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    grade_group = _grade_to_group(grade)

    with transaction.atomic():
        # Create private Task + Examples + Answers immediately so student can practice
        task = Task.objects.create(
            name=raw_json.get('task_name', 'Vygenerovaná úloha'),
            form=raw_json.get('form', 'classic'),
            is_private=True,
            owner_student=student,
        )

        # Link grade level
        try:
            gl = GradeLevel.objects.get(grade=grade)
            task.grade_levels.add(gl)
        except GradeLevel.DoesNotExist:
            pass

        for ex_data in raw_json.get('examples', []):
            ex_text = str(ex_data.get('example', '')).strip()
            input_type = str(ex_data.get('input_type', 'INLINE')).upper()
            answer_text = str(ex_data.get('answer', '')).strip()
            if not ex_text or not answer_text:
                continue
            ex_obj = Example.objects.create(
                example=ex_text,
                input_type=input_type,
                task=task,
            )
            Answer.objects.create(example=ex_obj, answer=answer_text)

        batch = GeneratedTaskBatch.objects.create(
            student=student,
            example_request=example_request_obj,
            grade=grade,
            grade_group=grade_group,
            generation_mode='ai_free',
            description=description,
            raw_json=raw_json,
            status='preview',
            created_task=task,
        )

    return Response({
        'batch_id': batch.id,
        'task_id': task.id,
        'raw_json': raw_json,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def submit_batch_survey(request, batch_id):
    """Submit the 5-question post-generation survey for a batch."""
    student_id = request.data.get('student_id')
    if not student_id:
        return Response({'error': 'Login required.'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        batch = GeneratedTaskBatch.objects.get(id=batch_id, student__id=student_id)
    except GeneratedTaskBatch.DoesNotExist:
        return Response({'error': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)

    if hasattr(batch, 'survey'):
        return Response({'error': 'Survey already submitted.'}, status=status.HTTP_409_CONFLICT)

    q1 = request.data.get('q1_as_requested')
    q2 = request.data.get('q2_solvable_display')
    q3 = request.data.get('q3_difficulty', 'ok')
    q4 = request.data.get('q4_has_errors')
    q5 = request.data.get('q5_satisfied')

    if any(v is None for v in [q1, q2, q4, q5]):
        return Response({'error': 'All survey questions are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if q3 not in ('easy', 'ok', 'hard'):
        return Response({'error': "q3_difficulty must be 'easy', 'ok', or 'hard'."}, status=status.HTTP_400_BAD_REQUEST)

    GeneratedTaskBatchSurvey.objects.create(
        batch=batch,
        q1_as_requested=bool(q1),
        q2_solvable_display=bool(q2),
        q3_difficulty=q3,
        q4_has_errors=bool(q4),
        q5_satisfied=bool(q5),
    )

    if bool(q5):
        batch.status = 'pending_review'
    else:
        batch.status = 'survey_done'
    batch.save(update_fields=['status'])

    return Response({
        'submitted_for_review': bool(q5),
        'status': batch.status,
    })


@api_view(['GET'])
def get_my_generated_batches(request):
    """Student: list their own generated batches."""
    student_id = request.query_params.get('student_id')
    if not student_id:
        return Response({'error': 'Login required.'}, status=status.HTTP_401_UNAUTHORIZED)

    batches = GeneratedTaskBatch.objects.filter(
        student__id=student_id
    ).select_related('student', 'survey').order_by('-created_at')

    return Response([_serialize_batch(b) for b in batches])


@api_view(['GET'])
def get_all_generated_batches(request):
    """Admin: list all generated batches, optionally filtered by status."""
    status_filter = request.query_params.get('status')
    qs = GeneratedTaskBatch.objects.select_related('student', 'survey').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)
    limit = request.query_params.get('limit', 200)
    try:
        limit = max(1, min(int(limit), 1000))
    except (TypeError, ValueError):
        limit = 200
    return Response([_serialize_batch(b) for b in qs[:limit]])


@api_view(['POST'])
def approve_generated_batch(request, batch_id):
    """Admin: approve a batch → make the private task public."""
    try:
        batch = GeneratedTaskBatch.objects.select_related('created_task').get(id=batch_id)
    except GeneratedTaskBatch.DoesNotExist:
        return Response({'error': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)

    if batch.status not in ('pending_review', 'preview'):
        return Response({'error': f'Batch cannot be approved (status: {batch.status}).'}, status=status.HTTP_409_CONFLICT)

    task = batch.created_task
    if not task:
        return Response({'error': 'No task associated with this batch.'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        task.is_private = False
        task.owner_student = None
        task.owner_session = None
        task.save(update_fields=['is_private', 'owner_student', 'owner_session'])

        # Ensure skill relations are up to date
        skill_ids = list(task.skills.values_list('id', flat=True))
        if skill_ids:
            create_skill_relations(skill_ids)

        batch.status = 'approved'
        batch.reviewed_at = timezone.now()
        batch.save(update_fields=['status', 'reviewed_at'])

    return Response({
        'task_id': task.id,
        'task_name': task.name,
        'status': 'approved',
    })


@api_view(['POST'])
def reject_generated_batch(request, batch_id):
    """Admin: reject a batch."""
    try:
        batch = GeneratedTaskBatch.objects.get(id=batch_id)
    except GeneratedTaskBatch.DoesNotExist:
        return Response({'error': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)

    note = (request.data.get('note') or '').strip()
    batch.status = 'rejected'
    batch.rejection_note = note
    batch.reviewed_at = timezone.now()
    batch.save(update_fields=['status', 'rejection_note', 'reviewed_at'])

    return Response({'status': 'rejected'})


@api_view(['DELETE'])
def delete_generated_batch(request, batch_id):
    """Student: delete own batch (and its private task)."""
    student_id = request.data.get('student_id') or request.query_params.get('student_id')
    try:
        batch = GeneratedTaskBatch.objects.get(id=batch_id)
    except GeneratedTaskBatch.DoesNotExist:
        return Response({'error': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not student_id or batch.student_id != int(student_id):
        return Response({'error': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

    with transaction.atomic():
        if batch.created_task and batch.created_task.is_private:
            batch.created_task.delete()
        batch.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Classroom Management ────────────────────────────────────────────────────

import string as _string

def generate_classroom_code(length=8):
    chars = _string.ascii_uppercase + _string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        if not Classroom.objects.filter(code=code).exists():
            return code


@api_view(['GET', 'POST'])
def manage_classrooms(request):
    if request.method == 'POST':
        teacher_id = request.data.get('teacher_id')
        name = request.data.get('name', '').strip()
        description = request.data.get('description', '').strip()

        if not teacher_id or not name:
            return Response({'error': 'teacher_id and name are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            teacher = Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

        code = generate_classroom_code()
        classroom = Classroom.objects.create(
            teacher=teacher,
            name=name,
            description=description,
            code=code,
        )

        return Response({
            'id': classroom.id,
            'name': classroom.name,
            'description': classroom.description,
            'code': classroom.code,
            'created_at': classroom.created_at,
            'student_count': 0,
        }, status=status.HTTP_201_CREATED)

    # GET — list classrooms for teacher
    teacher_id = request.GET.get('teacher_id')
    if not teacher_id:
        return Response({'error': 'teacher_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    classrooms = Classroom.objects.filter(teacher_id=teacher_id).annotate(
        student_count=Count('memberships')
    )

    data = [{
        'id': c.id,
        'name': c.name,
        'description': c.description,
        'code': c.code,
        'student_count': c.student_count,
        'created_at': c.created_at,
    } for c in classrooms]

    return Response(data)


@api_view(['GET', 'PATCH', 'DELETE'])
def classroom_detail(request, classroom_id):
    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        teacher_id = request.GET.get('teacher_id') or request.data.get('teacher_id')
        if not teacher_id or classroom.teacher_id != int(teacher_id):
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        classroom.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == 'PATCH':
        teacher_id = request.data.get('teacher_id')
        if not teacher_id or classroom.teacher_id != int(teacher_id):
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        name = request.data.get('name')
        description = request.data.get('description')
        if name is not None:
            classroom.name = name.strip()
        if description is not None:
            classroom.description = description.strip()
        classroom.save()

        return Response({
            'id': classroom.id,
            'name': classroom.name,
            'description': classroom.description,
            'code': classroom.code,
            'created_at': classroom.created_at,
        })

    # GET — full detail
    teacher_id = request.GET.get('teacher_id')
    student_id = request.GET.get('student_id')

    # Authorization: teacher who owns it, or student who is a member
    is_teacher = teacher_id and classroom.teacher_id == int(teacher_id)
    is_member = student_id and ClassroomStudent.objects.filter(
        classroom=classroom, student_id=student_id
    ).exists()

    if not is_teacher and not is_member:
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    # Students list
    memberships = ClassroomStudent.objects.filter(classroom=classroom).select_related('student')
    students = [{
        'id': m.student.id,
        'username': m.student.username,
        'grade': m.student.grade,
        'total_xp': m.student.total_xp,
        'level': m.student.level,
        'joined_at': m.joined_at,
    } for m in memberships]

    # Task assignments
    assignments = ClassroomTask.objects.filter(classroom=classroom).select_related('task')
    tasks = [{
        'id': a.id,
        'task_id': a.task.id,
        'task_name': a.task.name,
        'task_form': a.task.form,
        'is_homework': a.is_homework,
        'due_date': a.due_date,
        'assigned_at': a.assigned_at,
        'example_count': Example.objects.filter(task=a.task).count(),
        'grade_levels': list(a.task.grade_levels.values_list('grade', flat=True)),
    } for a in assignments]

    return Response({
        'id': classroom.id,
        'name': classroom.name,
        'description': classroom.description,
        'code': classroom.code,
        'created_at': classroom.created_at,
        'teacher_name': f"{classroom.teacher.first_name} {classroom.teacher.last_name}",
        'students': students,
        'task_assignments': tasks,
    })


# ─── Student Join / Leave ────────────────────────────────────────────────────

@api_view(['POST'])
def join_classroom(request):
    student_id = request.data.get('student_id')
    code = request.data.get('code', '').strip().upper()

    if not student_id or not code:
        return Response({'error': 'student_id and code are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        classroom = Classroom.objects.get(code=code)
    except Classroom.DoesNotExist:
        return Response({'error': 'Trieda s týmto kódom neexistuje'}, status=status.HTTP_404_NOT_FOUND)

    membership, created = ClassroomStudent.objects.get_or_create(
        classroom=classroom,
        student=student,
    )

    return Response({
        'classroom_id': classroom.id,
        'classroom_name': classroom.name,
        'teacher_name': f"{classroom.teacher.first_name} {classroom.teacher.last_name}",
        'joined_at': membership.joined_at,
        'already_member': not created,
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET'])
def get_student_classrooms(request):
    student_id = request.GET.get('student_id')
    if not student_id:
        return Response({'error': 'student_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    memberships = ClassroomStudent.objects.filter(
        student_id=student_id
    ).select_related('classroom', 'classroom__teacher')

    data = [{
        'id': m.classroom.id,
        'name': m.classroom.name,
        'code': m.classroom.code,
        'teacher_name': f"{m.classroom.teacher.first_name} {m.classroom.teacher.last_name}",
        'joined_at': m.joined_at,
        'task_count': ClassroomTask.objects.filter(classroom=m.classroom).count(),
    } for m in memberships]

    return Response(data)


@api_view(['DELETE'])
def leave_classroom(request, classroom_id):
    student_id = request.data.get('student_id')
    if not student_id:
        return Response({'error': 'student_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    deleted, _ = ClassroomStudent.objects.filter(
        classroom_id=classroom_id, student_id=student_id
    ).delete()

    if not deleted:
        return Response({'error': 'Not a member'}, status=status.HTTP_404_NOT_FOUND)

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def remove_student_from_classroom(request, classroom_id):
    teacher_id = request.data.get('teacher_id')
    student_id = request.data.get('student_id')

    if not teacher_id or not student_id:
        return Response({'error': 'teacher_id and student_id are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)

    if classroom.teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    deleted, _ = ClassroomStudent.objects.filter(
        classroom=classroom, student_id=student_id
    ).delete()

    if not deleted:
        return Response({'error': 'Student is not a member'}, status=status.HTTP_404_NOT_FOUND)

    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Classroom Task Assignment ───────────────────────────────────────────────

@api_view(['GET', 'POST'])
def manage_classroom_tasks(request, classroom_id):
    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        teacher_id = request.data.get('teacher_id')
        if not teacher_id or classroom.teacher_id != int(teacher_id):
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        task_id = request.data.get('task_id')
        is_homework = request.data.get('is_homework', False)
        due_date = request.data.get('due_date')

        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

        assignment, created = ClassroomTask.objects.get_or_create(
            classroom=classroom,
            task=task,
            defaults={
                'is_homework': is_homework,
                'due_date': due_date,
                'assigned_by': classroom.teacher,
            }
        )

        if not created:
            return Response({'error': 'Task already assigned'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'id': assignment.id,
            'task_id': task.id,
            'task_name': task.name,
            'task_form': task.form,
            'is_homework': assignment.is_homework,
            'due_date': assignment.due_date,
            'assigned_at': assignment.assigned_at,
            'example_count': Example.objects.filter(task=task).count(),
            'grade_levels': list(task.grade_levels.values_list('grade', flat=True)),
        }, status=status.HTTP_201_CREATED)

    # GET — list tasks for classroom
    assignments = ClassroomTask.objects.filter(classroom=classroom).select_related('task')
    data = [{
        'id': a.id,
        'task_id': a.task.id,
        'task_name': a.task.name,
        'task_form': a.task.form,
        'is_homework': a.is_homework,
        'due_date': a.due_date,
        'assigned_at': a.assigned_at,
        'example_count': Example.objects.filter(task=a.task).count(),
        'grade_levels': list(a.task.grade_levels.values_list('grade', flat=True)),
    } for a in assignments]

    return Response(data)


@api_view(['PATCH', 'DELETE'])
def classroom_task_detail(request, classroom_id, task_id):
    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)

    teacher_id = request.data.get('teacher_id') or request.GET.get('teacher_id')
    if not teacher_id or classroom.teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    try:
        assignment = ClassroomTask.objects.get(classroom=classroom, task_id=task_id)
    except ClassroomTask.DoesNotExist:
        return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    is_homework = request.data.get('is_homework')
    due_date = request.data.get('due_date')

    if is_homework is not None:
        assignment.is_homework = is_homework
    if due_date is not None:
        assignment.due_date = due_date if due_date else None

    assignment.save()

    return Response({
        'id': assignment.id,
        'task_id': assignment.task_id,
        'is_homework': assignment.is_homework,
        'due_date': assignment.due_date,
        'assigned_at': assignment.assigned_at,
    })


# ─── Task Browsing (for teachers) ───────────────────────────────────────────

@api_view(['GET'])
def browse_tasks(request):
    qs = Task.objects.filter(is_private=False)

    grade = request.GET.get('grade')
    if grade:
        qs = qs.filter(grade_levels__grade=int(grade))

    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(name__icontains=search)

    qs = qs.distinct().prefetch_related('grade_levels', 'skills')

    data = [{
        'task_id': t.id,
        'task_name': t.name,
        'task_form': t.form,
        'grade_levels': list(t.grade_levels.values_list('grade', flat=True)),
        'example_count': Example.objects.filter(task=t).count(),
        'skills': list(t.skills.values_list('name', flat=True)),
    } for t in qs[:200]]

    return Response(data)


# ─── Classroom Analytics ─────────────────────────────────────────────────────

@api_view(['GET'])
def get_classroom_analytics(request, classroom_id):
    teacher_id = request.GET.get('teacher_id')

    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)

    if not teacher_id or classroom.teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    student_ids = list(ClassroomStudent.objects.filter(
        classroom=classroom
    ).values_list('student_id', flat=True))

    total_students = len(student_ids)

    # Active in last 7 days
    seven_days_ago = timezone.now() - timezone.timedelta(days=7)
    active_students = StudentExample.objects.filter(
        student_id__in=student_ids,
        date__gte=seven_days_ago,
    ).values('student_id').distinct().count()

    # Aggregate stats from StudentExample
    records = StudentExample.objects.filter(student_id__in=student_ids)
    total_examples = records.count()
    solved_count = records.filter(solved=True).count()
    avg_accuracy = (solved_count / total_examples * 100) if total_examples > 0 else 0

    # Per-student summary
    from .mastery import compute_final_mastery

    student_summaries = []
    students = Student.objects.filter(id__in=student_ids)
    for student in students:
        st_records = records.filter(student=student)
        st_total = st_records.count()
        st_solved = st_records.filter(solved=True).count()
        st_accuracy = (st_solved / st_total * 100) if st_total > 0 else 0

        # Average mastery across all skills
        masteries = SkillMastery.objects.filter(student=student)
        avg_mastery = 0
        if masteries.exists():
            mastery_values = [compute_final_mastery(m)['final_mastery'] for m in masteries]
            avg_mastery = sum(mastery_values) / len(mastery_values) if mastery_values else 0

        student_summaries.append({
            'id': student.id,
            'username': student.username,
            'grade': student.grade,
            'total_xp': student.total_xp,
            'level': student.level,
            'examples_practiced': st_total,
            'solved_count': st_solved,
            'accuracy': round(st_accuracy, 1),
            'avg_mastery': round(avg_mastery * 100, 1),
        })

    # Sort by accuracy descending
    student_summaries.sort(key=lambda s: s['accuracy'], reverse=True)

    return Response({
        'total_students': total_students,
        'active_students': active_students,
        'total_examples': total_examples,
        'solved_count': solved_count,
        'avg_accuracy': round(avg_accuracy, 1),
        'student_summaries': student_summaries,
    })


@api_view(['GET'])
def get_classroom_student_detail(request, classroom_id, student_id):
    teacher_id = request.GET.get('teacher_id')

    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)

    if not teacher_id or classroom.teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    # Verify student is in this classroom
    if not ClassroomStudent.objects.filter(classroom=classroom, student_id=student_id).exists():
        return Response({'error': 'Student is not in this classroom'}, status=status.HTTP_404_NOT_FOUND)

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    from .mastery import compute_final_mastery
    from django.db.models import Avg

    # Skill mastery
    masteries = SkillMastery.objects.filter(student=student).select_related('skill')
    skill_mastery = []
    mastery_values = []
    for m in masteries:
        fm = compute_final_mastery(m)
        mastery_values.append(fm['final_mastery'])
        skill_mastery.append({
            'skill_id': m.skill_id,
            'skill_name': m.skill.name,
            'mastery': round(fm['final_mastery'] * 100, 1),
            'examples_count': fm['example_count'],
        })

    # Overall stats
    all_records = StudentExample.objects.filter(student=student)
    total_practiced = all_records.count()
    total_solved = all_records.filter(solved=True).count()
    accuracy = round(total_solved / total_practiced * 100, 1) if total_practiced > 0 else 0
    avg_mastery = round(sum(mastery_values) / len(mastery_values) * 100, 1) if mastery_values else 0

    # Task progress for tasks assigned in this classroom
    assigned_task_ids = list(ClassroomTask.objects.filter(
        classroom=classroom
    ).values_list('task_id', flat=True))

    task_progress = []
    for task_id in assigned_task_ids:
        task = Task.objects.get(id=task_id)
        total_examples = Example.objects.filter(task=task).count()
        records = StudentExample.objects.filter(student=student, task=task)
        practiced = records.count()
        correct = records.filter(solved=True).count()
        incorrect = records.filter(solved=False).count()
        avg_time = records.aggregate(avg=Avg('duration'))['avg']

        task_progress.append({
            'task_id': task.id,
            'task_name': task.name,
            'total_examples': total_examples,
            'practiced': practiced,
            'correct': correct,
            'incorrect': incorrect,
            'avg_time_ms': round(avg_time) if avg_time else None,
            'completion': round(correct / total_examples * 100, 1) if total_examples > 0 else 0,
        })

    # Problem examples for THIS student: grouped by example, worst success first
    grouped = {}
    for r in StudentExample.objects.filter(student=student).select_related('example'):
        g = grouped.setdefault(r.example_id, {'example': r.example, 'n': 0, 'solved': 0})
        g['n'] += 1
        g['solved'] += 1 if r.solved else 0
    weak_examples = []
    for ex_id, g in grouped.items():
        if g['n'] - g['solved'] <= 0:
            continue
        ans = g['example'].answers.first()
        weak_examples.append({
            'example_id': ex_id,
            'question': g['example'].example,
            'correct_answer': ans.answer if ans else '',
            'attempts': g['n'],
            'solved': g['solved'],
            'wrong': g['n'] - g['solved'],
            'accuracy': round(g['solved'] / g['n'] * 100, 1),
        })
    weak_examples.sort(key=lambda x: (x['accuracy'], -x['attempts']))
    weak_examples = weak_examples[:15]

    # Recent attempts (full log is paginated via student_attempt_log)
    total_attempts = ExampleAttempt.objects.filter(student=student).count()
    recent = ExampleAttempt.objects.filter(
        student=student
    ).select_related('example').order_by('-created_at')[:20]
    recent_attempts = [_serialize_attempt(a) for a in recent]

    # Badges
    badges = student.earned_badges.select_related('badge').all()
    badge_data = [{'key': sb.badge.key, 'name': sb.badge.name, 'icon': sb.badge.icon} for sb in badges]

    return Response({
        'classroom_name': classroom.name,
        'student': {
            'id': student.id,
            'username': student.username,
            'grade': student.grade,
            'total_xp': student.total_xp,
            'level': student.level,
        },
        'stats': {
            'examples_practiced': total_practiced,
            'accuracy': accuracy,
            'avg_mastery': avg_mastery,
            'streak_days': student.current_streak,
        },
        'skill_mastery': skill_mastery,
        'task_progress': task_progress,
        'weak_examples': weak_examples,
        'recent_attempts': recent_attempts,
        'total_attempts': total_attempts,
        'badges': badge_data,
    })


def _serialize_attempt(a):
    return {
        'id': a.id,
        'example_text': a.example_text or (a.example.example if a.example_id else ''),
        'typed': a.parsed_answer or a.transcription,
        'transcription': a.transcription,
        'correct_answer': a.correct_answer,
        'is_correct': a.is_correct,
        'attempt_number': a.attempt_number,
        'action': a.action,
        'created_at': a.created_at,
    }


@api_view(['GET'])
def student_attempt_log(request, classroom_id, student_id):
    """Full, paginated attempt history for one student — every example they
    answered, with what they typed and the correct answer."""
    teacher_id = request.GET.get('teacher_id')
    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)
    if not teacher_id or classroom.teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
    if not ClassroomStudent.objects.filter(classroom=classroom, student_id=student_id).exists():
        return Response({'error': 'Student is not in this classroom'}, status=status.HTTP_404_NOT_FOUND)

    try:
        limit = max(1, min(200, int(request.GET.get('limit', 100))))
    except (TypeError, ValueError):
        limit = 100
    try:
        offset = max(0, int(request.GET.get('offset', 0)))
    except (TypeError, ValueError):
        offset = 0
    only = request.GET.get('only', 'all')

    qs = ExampleAttempt.objects.filter(student_id=student_id).select_related('example')
    if only == 'wrong':
        qs = qs.filter(is_correct=False)
    elif only == 'correct':
        qs = qs.filter(is_correct=True)
    total = qs.count()
    rows = qs.order_by('-created_at')[offset:offset + limit]
    return Response({
        'count': total,
        'offset': offset,
        'limit': limit,
        'results': [_serialize_attempt(a) for a in rows],
    })


# ─── Classroom Info (public, for join page) ──────────────────────────────────

@api_view(['GET'])
def get_classroom_by_code(request):
    code = request.GET.get('code', '').strip().upper()
    if not code:
        return Response({'error': 'code is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        classroom = Classroom.objects.select_related('teacher').get(code=code)
    except Classroom.DoesNotExist:
        return Response({'error': 'Trieda s týmto kódom neexistuje'}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'id': classroom.id,
        'name': classroom.name,
        'code': classroom.code,
        'teacher_name': f"{classroom.teacher.first_name} {classroom.teacher.last_name}",
        'student_count': classroom.memberships.count(),
    })


# ─── Classroom Task Details ───────────────────────────────────────────────────

@api_view(['GET'])
def get_classroom_task_details(request, classroom_id, task_id):
    teacher_id = request.GET.get('teacher_id')

    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)

    if not teacher_id or classroom.teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

    student_ids = list(ClassroomStudent.objects.filter(
        classroom=classroom
    ).values_list('student_id', flat=True))

    data = []
    for ex in task.example_set.all().order_by('id'):
        records = StudentExample.objects.filter(student_id__in=student_ids, example=ex)
        total = records.count()
        solved = records.filter(solved=True).count()
        data.append({
            'id': ex.id,
            'question': ex.example,
            'attempts': total,
            'solved': solved,
            'accuracy': round(solved / total * 100, 1) if total > 0 else None,
        })

    return Response({
        'task_id': task.id,
        'task_name': task.name,
        'examples': data,
    })


# ─── Classroom hardest / easiest examples ────────────────────────────────────

def _classroom_example_rows(classroom, student_ids):
    """
    Per-example class stats across every task assigned to the classroom.
    Returns rows: {example_id, question, task_id, task_name, attempts, solved, accuracy}.
    """
    rows = []
    tasks = Task.objects.filter(classroom_assignments__classroom=classroom).distinct()
    for task in tasks:
        for ex in task.example_set.all().only('id', 'example'):
            records = StudentExample.objects.filter(student_id__in=student_ids, example=ex)
            total = records.count()
            if total == 0:
                continue
            solved = records.filter(solved=True).count()
            rows.append({
                'example_id': ex.id,
                'question': ex.example,
                'task_id': task.id,
                'task_name': task.name,
                'attempts': total,
                'solved': solved,
                'accuracy': round(solved / total * 100, 1),
            })
    return rows


@api_view(['GET'])
def get_classroom_hardest_examples(request, classroom_id):
    teacher_id = request.GET.get('teacher_id')

    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)

    if not teacher_id or classroom.teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    try:
        min_attempts = max(1, int(request.GET.get('min_attempts', 3)))
    except (TypeError, ValueError):
        min_attempts = 3
    try:
        limit = max(1, min(50, int(request.GET.get('limit', 10))))
    except (TypeError, ValueError):
        limit = 10

    student_ids = list(ClassroomStudent.objects.filter(
        classroom=classroom
    ).values_list('student_id', flat=True))

    rows = [r for r in _classroom_example_rows(classroom, student_ids)
            if r['attempts'] >= min_attempts]

    hardest = sorted(rows, key=lambda r: (r['accuracy'], -r['attempts']))[:limit]
    easiest = sorted(rows, key=lambda r: (-r['accuracy'], -r['attempts']))[:limit]

    return Response({
        'min_attempts': min_attempts,
        'evaluated_examples': len(rows),
        'hardest': hardest,
        'easiest': easiest,
    })


# ─── Student AI insight (on-demand, cached) ──────────────────────────────────

def _student_mastery_rows(student):
    """Returns (skill_mastery list, avg_mastery_pct) for a student."""
    from .mastery import compute_final_mastery
    masteries = SkillMastery.objects.filter(student=student).select_related('skill')
    rows, values = [], []
    for m in masteries:
        fm = compute_final_mastery(m)
        values.append(fm['final_mastery'])
        rows.append({
            'skill_id': m.skill_id,
            'skill_name': m.skill.name,
            'mastery': round(fm['final_mastery'] * 100, 1),
            'examples_count': fm['example_count'],
        })
    avg = round(sum(values) / len(values) * 100, 1) if values else 0
    return rows, avg


@api_view(['GET', 'POST'])
def student_ai_insight(request, classroom_id, student_id):
    teacher_id = request.GET.get('teacher_id') if request.method == 'GET' else request.data.get('teacher_id')

    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)

    if not teacher_id or classroom.teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    if not ClassroomStudent.objects.filter(classroom=classroom, student_id=student_id).exists():
        return Response({'error': 'Student is not in this classroom'}, status=status.HTTP_404_NOT_FOUND)

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    existing = StudentInsight.objects.filter(student=student, classroom=classroom).first()

    def _serialize(row):
        return {
            'payload': row.payload,
            'source_attempts': row.source_attempts,
            'model_used': row.model_used,
            'generated_at': row.generated_at,
        }

    if request.method == 'GET':
        return Response({'insight': _serialize(existing) if existing else None})

    # POST — regenerate (debounce rapid double-clicks)
    if existing and (timezone.now() - existing.generated_at).total_seconds() < 30:
        return Response({'insight': _serialize(existing), 'cached': True})

    attempts_qs = ExampleAttempt.objects.filter(
        student=student
    ).select_related('example').order_by('-created_at')[:60]
    attempts = [{
        'example': a.example_text or (a.example.example if a.example_id else ''),
        'typed': a.parsed_answer or a.transcription,
        'correct': a.correct_answer,
        'is_correct': a.is_correct,
        'skills': a.practiced_skill_names or [],
    } for a in attempts_qs]

    skill_mastery, avg_mastery = _student_mastery_rows(student)
    all_records = StudentExample.objects.filter(student=student)
    total = all_records.count()
    solved = all_records.filter(solved=True).count()
    overall_accuracy = round(solved / total * 100, 1) if total else 0

    from .generators.student_insight_generator import generate_student_insight
    try:
        payload = generate_student_insight({
            'grade': student.grade,
            'overall_accuracy': overall_accuracy,
            'skill_mastery': skill_mastery,
            'attempts': attempts,
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    row, _ = StudentInsight.objects.update_or_create(
        student=student, classroom=classroom,
        defaults={
            'payload': payload,
            'source_attempts': len(attempts),
            'model_used': payload.get('meta', {}).get('model', ''),
        },
    )
    return Response({'insight': _serialize(row)})


# ─── Classroom Task Homework Stats ───────────────────────────────────────────

@api_view(['GET'])
def get_classroom_task_homework_stats(request, classroom_id, task_id):
    teacher_id = request.GET.get('teacher_id')

    try:
        classroom = Classroom.objects.get(id=classroom_id)
    except Classroom.DoesNotExist:
        return Response({'error': 'Classroom not found'}, status=status.HTTP_404_NOT_FOUND)

    if not teacher_id or classroom.teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    try:
        ct = ClassroomTask.objects.get(classroom=classroom, task_id=task_id)
    except ClassroomTask.DoesNotExist:
        return Response({'error': 'Task not assigned'}, status=status.HTTP_404_NOT_FOUND)

    task = ct.task
    total_examples = Example.objects.filter(task=task).count()
    student_ids = list(ClassroomStudent.objects.filter(
        classroom=classroom
    ).values_list('student_id', flat=True))
    students = Student.objects.filter(id__in=student_ids).order_by('username')

    data = []
    for student in students:
        records = StudentExample.objects.filter(student=student, task=task)
        solved_count = records.filter(solved=True).count()
        completed = total_examples > 0 and solved_count >= total_examples

        on_time = None
        if completed and ct.due_date:
            last_solved = records.filter(solved=True).order_by('-date').first()
            if last_solved:
                on_time = last_solved.date <= ct.due_date

        data.append({
            'student_id': student.id,
            'username': student.username,
            'solved': solved_count,
            'total': total_examples,
            'completed': completed,
            'on_time': on_time,
        })

    return Response({
        'task_id': task.id,
        'task_name': task.name,
        'is_homework': ct.is_homework,
        'due_date': ct.due_date,
        'total_students': len(student_ids),
        'completed_count': sum(1 for d in data if d['completed']),
        'students': data,
    })


# ─── Teacher Task Generation ──────────────────────────────────────────────────

@api_view(['POST'])
def teacher_generate_task_preview(request):
    teacher_id = request.data.get('teacher_id')
    if not teacher_id:
        return Response({'error': 'teacher_id required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        teacher = Teacher.objects.get(id=int(teacher_id))
    except Teacher.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

    task_type = request.data.get('type', 'arithmetic')
    try:
        count = min(max(int(request.data.get('count', 10)), 1), 30)
    except (TypeError, ValueError):
        count = 10
    description = (request.data.get('description') or '').strip()
    if not description:
        return Response({'error': 'description is required'}, status=status.HTTP_400_BAD_REQUEST)
    language = request.data.get('language', 'sk')
    if language not in ('sk', 'cs', 'en'):
        language = 'sk'

    if task_type == 'mix':
        segments = request.data.get('segments', [])
        if not segments:
            return Response({'error': 'segments are required for mix type'}, status=status.HTTP_400_BAD_REQUEST)
        from .generators.teacher_generator import generate_teacher_task_mix
        try:
            data = generate_teacher_task_mix(segments, description, language)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except RuntimeError as e:
            return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    else:
        from .generators.teacher_generator import generate_teacher_task
        try:
            data = generate_teacher_task(task_type, count, description, language)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except RuntimeError as e:
            return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(data)


@api_view(['POST'])
def teacher_save_task(request):
    teacher_id = request.data.get('teacher_id')
    if not teacher_id:
        return Response({'error': 'teacher_id required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        teacher = Teacher.objects.get(id=int(teacher_id))
    except Teacher.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

    task_name = (request.data.get('task_name') or '').strip()
    if not task_name:
        return Response({'error': 'task_name required'}, status=status.HTTP_400_BAD_REQUEST)

    examples_data = request.data.get('examples', [])
    if not examples_data:
        return Response({'error': 'At least one example required'}, status=status.HTTP_400_BAD_REQUEST)

    grade = request.data.get('grade')
    form = request.data.get('form', 'classic')
    generation_prompt = (request.data.get('generation_prompt') or '').strip()
    generation_params = request.data.get('generation_params') or None

    with transaction.atomic():
        task = Task.objects.create(
            name=task_name,
            form=form if form in ('classic', 'word-problem') else 'classic',
            is_private=False,
            owner_teacher=teacher,
            generation_prompt=generation_prompt,
            generation_params=generation_params,
        )

        if grade:
            try:
                gl = GradeLevel.objects.get(grade=int(grade))
                task.grade_levels.add(gl)
            except (GradeLevel.DoesNotExist, ValueError):
                pass

        for ex_data in examples_data:
            ex_text = str(ex_data.get('example', '')).strip()
            input_type = str(ex_data.get('input_type', 'INLINE')).upper()
            answer_text = str(ex_data.get('answer', '')).strip()
            if not ex_text or not answer_text:
                continue
            ex = Example.objects.create(example=ex_text, input_type=input_type, task=task, owner_teacher=teacher)
            Answer.objects.create(example=ex, answer=answer_text)

    # Save prompt + result JSON locally and upload to MEGA (background, only for AI-generated tasks)
    if generation_prompt:
        import threading
        from .attempt_cloud_sync import sync_teacher_prompt_to_mega
        threading.Thread(
            target=sync_teacher_prompt_to_mega,
            args=(task, teacher, examples_data),
            daemon=True,
        ).start()

    return Response({'task_id': task.id, 'task_name': task.name}, status=status.HTTP_201_CREATED)


# ─── Teacher Example Library ─────────────────────────────────────────────────
# Teacher-owned examples (Example.owner_teacher set) live independently of any
# sada (task=None) until attached. Platform/admin examples (owner_teacher=None)
# are always read-only to teachers and are never mutated here — only cloned.

def _serialize_teacher_example(example):
    answer = example.answers.first()
    return {
        'id': example.id,
        'example': example.example,
        'input_type': example.input_type,
        'answer': answer.answer if answer else '',
        'steps': [s.text for s in example.steps.order_by('order')],
        'task_id': example.task_id,
        'task_name': example.task.name if example.task_id else None,
        'grade': example.grade,
    }


def _parse_grade(value):
    if value in (None, ''):
        return None
    try:
        grade = int(value)
    except (TypeError, ValueError):
        return None
    return grade if 1 <= grade <= 9 else None


def _clone_example(source_example, target_task, teacher):
    """Duplicate an Example (+ its Answer + Steps) into target_task, owned by teacher. Source is never modified."""
    new_example = Example.objects.create(
        example=source_example.example,
        input_type=source_example.input_type,
        task=target_task,
        owner_teacher=teacher,
    )
    answer = source_example.answers.first()
    if answer:
        Answer.objects.create(example=new_example, answer=answer.answer)
    for step in source_example.steps.order_by('order'):
        Step.objects.create(example=new_example, text=step.text, order=step.order)
    return new_example


@api_view(['GET'])
def teacher_examples_unassigned_count(request):
    teacher_id = request.GET.get('teacher_id')
    if not teacher_id:
        return Response({'error': 'teacher_id required'}, status=status.HTTP_400_BAD_REQUEST)
    count = Example.objects.filter(owner_teacher_id=teacher_id, task__isnull=True).count()
    return Response({'count': count})


@api_view(['GET', 'POST'])
def teacher_examples(request):
    if request.method == 'GET':
        teacher_id = request.GET.get('teacher_id')
        if not teacher_id:
            return Response({'error': 'teacher_id required'}, status=status.HTTP_400_BAD_REQUEST)

        qs = Example.objects.filter(owner_teacher_id=teacher_id).select_related('task').prefetch_related('answers', 'steps')

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(example__icontains=search) |
                Q(task__name__icontains=search) |
                Q(answers__answer__icontains=search)
            ).distinct()

        if request.GET.get('unattached_only') in ('1', 'true', 'True'):
            qs = qs.filter(task__isnull=True)

        task_id = request.GET.get('task_id')
        if task_id:
            qs = qs.filter(task_id=task_id)

        grade = _parse_grade(request.GET.get('grade'))
        if grade is not None:
            qs = qs.filter(grade=grade)

        data = [_serialize_teacher_example(ex) for ex in qs.order_by('-id')]
        return Response(data)

    # POST — create a standalone example, not attached to any sada yet
    teacher_id = request.data.get('teacher_id')
    if not teacher_id:
        return Response({'error': 'teacher_id required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        teacher = Teacher.objects.get(id=int(teacher_id))
    except Teacher.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

    example_text = (request.data.get('example') or '').strip()
    answer_text = (request.data.get('answer') or '').strip()
    input_type = (request.data.get('input_type') or 'INLINE').upper()
    steps = request.data.get('steps', [])

    if not example_text:
        return Response({'error': 'Nebyl zadán text příkladu'}, status=status.HTTP_400_BAD_REQUEST)
    if not answer_text:
        return Response({'error': 'Nebyla zadána odpověď'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        example = Example.objects.create(
            example=example_text, input_type=input_type, task=None, owner_teacher=teacher,
            grade=_parse_grade(request.data.get('grade')),
        )
        Answer.objects.create(example=example, answer=answer_text)
        for index, step_text in enumerate(steps, start=1):
            if step_text:
                Step.objects.create(example=example, text=step_text, order=index)

    return Response(_serialize_teacher_example(example), status=status.HTTP_201_CREATED)


@api_view(['PATCH', 'DELETE'])
def teacher_example_detail(request, example_id):
    example = get_object_or_404(Example, id=example_id)
    teacher_id = request.data.get('teacher_id') or request.GET.get('teacher_id')

    if not teacher_id or example.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'DELETE':
        with transaction.atomic():
            example.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    example_text = request.data.get('example')
    input_type = request.data.get('input_type')
    answer_text = request.data.get('answer')
    steps = request.data.get('steps')

    if example_text is not None:
        example.example = example_text.strip()
    if input_type is not None:
        example.input_type = input_type.upper()
    if 'grade' in request.data:
        example.grade = _parse_grade(request.data.get('grade'))
    example.save()

    if answer_text is not None:
        Answer.objects.update_or_create(example=example, defaults={'answer': answer_text.strip()})

    if steps is not None:
        Step.objects.filter(example=example).delete()
        for index, step_text in enumerate(steps, start=1):
            if step_text:
                Step.objects.create(example=example, text=step_text, order=index)

    return Response(_serialize_teacher_example(example))


@api_view(['POST'])
def teacher_examples_bulk_set_grade(request):
    teacher_id = request.data.get('teacher_id')
    example_ids = request.data.get('example_ids') or []
    if not teacher_id or not example_ids:
        return Response({'error': 'teacher_id and example_ids required'}, status=status.HTTP_400_BAD_REQUEST)

    grade = _parse_grade(request.data.get('grade'))
    with transaction.atomic():
        updated = Example.objects.filter(id__in=example_ids, owner_teacher_id=teacher_id).update(grade=grade)
    return Response({'updated': updated})


@api_view(['POST'])
def teacher_examples_bulk_delete(request):
    teacher_id = request.data.get('teacher_id')
    example_ids = request.data.get('example_ids') or []
    if not teacher_id or not example_ids:
        return Response({'error': 'teacher_id and example_ids required'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        qs = Example.objects.filter(id__in=example_ids, owner_teacher_id=teacher_id)
        deleted = qs.count()
        qs.delete()
    return Response({'deleted': deleted})


@api_view(['POST'])
def teacher_examples_bulk_add_to_task(request):
    teacher_id = request.data.get('teacher_id')
    example_ids = request.data.get('example_ids') or []
    task_id = request.data.get('task_id')
    if not teacher_id or not example_ids or not task_id:
        return Response({'error': 'teacher_id, example_ids and task_id required'}, status=status.HTTP_400_BAD_REQUEST)

    task = get_object_or_404(Task, id=task_id)
    if task.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    with transaction.atomic():
        updated = Example.objects.filter(id__in=example_ids, owner_teacher_id=teacher_id).update(task=task)
    return Response({'task_id': task.id, 'task_name': task.name, 'updated': updated})


@api_view(['POST'])
def teacher_examples_bulk_create_task(request):
    teacher_id = request.data.get('teacher_id')
    example_ids = request.data.get('example_ids') or []
    task_name = (request.data.get('task_name') or '').strip()
    if not teacher_id or not example_ids or not task_name:
        return Response({'error': 'teacher_id, example_ids and task_name required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        teacher = Teacher.objects.get(id=int(teacher_id))
    except Teacher.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

    with transaction.atomic():
        task = Task.objects.create(name=task_name, form='classic', owner_teacher=teacher, is_private=True)

        owned = Example.objects.filter(id__in=example_ids, owner_teacher_id=teacher_id)
        grades = set(owned.exclude(grade__isnull=True).values_list('grade', flat=True))
        if grades:
            task.grade_levels.set(GradeLevel.objects.filter(grade__in=grades))

        updated = owned.update(task=task)

    return Response({'task_id': task.id, 'task_name': task.name, 'updated': updated}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def teacher_my_tasks(request):
    teacher_id = request.GET.get('teacher_id')
    if not teacher_id:
        return Response({'error': 'teacher_id required'}, status=status.HTTP_400_BAD_REQUEST)

    tasks = Task.objects.filter(owner_teacher_id=teacher_id).prefetch_related('grade_levels').order_by('-id')
    data = [{
        'id': t.id,
        'name': t.name,
        'form': t.form,
        'example_count': t.example_set.count(),
        'grade_levels': list(t.grade_levels.values_list('grade', flat=True)),
    } for t in tasks]
    return Response(data)


@api_view(['GET'])
def teacher_task_examples(request, task_id):
    teacher_id = request.GET.get('teacher_id')
    task = get_object_or_404(Task, id=task_id)

    if not teacher_id or task.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    examples = task.example_set.select_related('task').prefetch_related('answers', 'steps').order_by('id')
    return Response({
        'task_id': task.id,
        'task_name': task.name,
        'examples': [_serialize_teacher_example(ex) for ex in examples],
    })


@api_view(['POST'])
def teacher_generate_more_examples_preview(request, task_id):
    teacher_id = request.data.get('teacher_id')
    task = get_object_or_404(Task, id=task_id)
    if not teacher_id or task.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    description = (request.data.get('description') or '').strip()
    if not description:
        return Response({'error': 'description is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        count = min(max(int(request.data.get('count', 10)), 1), 30)
    except (TypeError, ValueError):
        count = 10
    language = request.data.get('language', 'sk')
    if language not in ('sk', 'cs', 'en'):
        language = 'sk'

    # Example has no timestamp column; -id is a reliable insertion-order proxy. Reverse to chronological for the prompt.
    recent = list(task.example_set.prefetch_related('answers').order_by('-id')[:10])[::-1]
    reference_examples = [{
        'example': ex.example, 'input_type': ex.input_type,
        'answer': ex.answers.first().answer if ex.answers.first() else '',
    } for ex in recent]
    fallback_type = 'word' if task.form == 'word-problem' else 'arithmetic'

    from .generators.teacher_generator import generate_teacher_task_more
    try:
        data = generate_teacher_task_more(reference_examples, count, description, fallback_type, language)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(data)


@api_view(['POST'])
def teacher_save_generated_examples(request, task_id):
    teacher_id = request.data.get('teacher_id')
    task = get_object_or_404(Task, id=task_id)
    if not teacher_id or task.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    examples_data = request.data.get('examples') or []
    if not examples_data:
        return Response({'error': 'At least one example required'}, status=status.HTTP_400_BAD_REQUEST)
    description = (request.data.get('description') or '').strip()
    teacher = task.owner_teacher

    created = []
    with transaction.atomic():
        for ex_data in examples_data:
            ex_text = str(ex_data.get('example', '')).strip()
            input_type = str(ex_data.get('input_type', 'INLINE')).upper()
            answer_text = str(ex_data.get('answer', '')).strip()
            if not ex_text or not answer_text:
                continue
            ex = Example.objects.create(example=ex_text, input_type=input_type, task=task, owner_teacher=teacher)
            Answer.objects.create(example=ex, answer=answer_text)
            created.append(ex)

    if description:
        import threading
        from .attempt_cloud_sync import sync_teacher_prompt_to_mega
        threading.Thread(
            target=sync_teacher_prompt_to_mega,
            args=(task, teacher, examples_data),
            kwargs={'generation_prompt': description, 'generation_params': {'mode': 'generate_more', 'count': len(created)}},
            daemon=True,
        ).start()

    return Response({'created': [_serialize_teacher_example(ex) for ex in created]}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def teacher_attach_example(request, task_id):
    teacher_id = request.data.get('teacher_id')
    example_id = request.data.get('example_id')
    task = get_object_or_404(Task, id=task_id)

    if not teacher_id or task.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    example = get_object_or_404(Example, id=example_id)
    if example.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    if example.task_id is not None:
        return Response({'error': 'Príklad je už priradený do sady.'}, status=status.HTTP_409_CONFLICT)

    example.task = task
    example.save(update_fields=['task'])

    return Response(_serialize_teacher_example(example))


@api_view(['POST'])
def teacher_detach_example(request, task_id):
    teacher_id = request.data.get('teacher_id')
    example_id = request.data.get('example_id')
    task = get_object_or_404(Task, id=task_id)

    if not teacher_id or task.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    example = get_object_or_404(Example, id=example_id, task=task)
    if example.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    example.task = None
    example.save(update_fields=['task'])

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def teacher_copy_example_in(request, task_id):
    teacher_id = request.data.get('teacher_id')
    source_example_id = request.data.get('source_example_id')
    task = get_object_or_404(Task, id=task_id)

    if not teacher_id or task.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    try:
        teacher = Teacher.objects.get(id=int(teacher_id))
    except Teacher.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

    source_example = get_object_or_404(Example, id=source_example_id)

    with transaction.atomic():
        new_example = _clone_example(source_example, task, teacher)

    return Response(_serialize_teacher_example(new_example), status=status.HTTP_201_CREATED)


@api_view(['POST'])
def teacher_copy_task(request):
    teacher_id = request.data.get('teacher_id')
    source_task_id = request.data.get('source_task_id')
    new_name = (request.data.get('new_name') or '').strip()

    if not teacher_id:
        return Response({'error': 'teacher_id required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        teacher = Teacher.objects.get(id=int(teacher_id))
    except Teacher.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

    source_task = get_object_or_404(Task, id=source_task_id)

    with transaction.atomic():
        new_task = Task.objects.create(
            name=new_name or f"{source_task.name} (kópia)",
            form=source_task.form,
            owner_teacher=teacher,
            is_private=True,
        )
        new_task.grade_levels.set(source_task.grade_levels.all())

        for source_example in source_task.example_set.order_by('id'):
            _clone_example(source_example, new_task, teacher)

    return Response({'task_id': new_task.id, 'task_name': new_task.name}, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
def teacher_delete_task(request, task_id):
    teacher_id = request.data.get('teacher_id') or request.GET.get('teacher_id')
    task = get_object_or_404(Task, id=task_id)

    if not teacher_id or task.owner_teacher_id != int(teacher_id):
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

    try:
        with transaction.atomic():
            task.skills.clear()
            task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        return Response({'error': f"Error deleting task: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


# ─── Duel (preťahovanie lanom) ───────────────────────────────────────────────

_DUEL_ADJECTIVES = ['Rýchly', 'Šikovný', 'Odvážny', 'Bystrý', 'Hbitý', 'Silný', 'Múdry', 'Veselý', 'Smelý', 'Divoký']
_DUEL_NOUNS = ['Tiger', 'Vlk', 'Orol', 'Lev', 'Medveď', 'Sokol', 'Rys', 'Jazvec', 'Drak', 'Líška']


def _generate_duel_display_name():
    return f"{random.choice(_DUEL_ADJECTIVES)} {random.choice(_DUEL_NOUNS)} {random.randint(1, 99)}"


def _resolve_display_name(student, requested_name):
    """Registered students always show their username; anonymous players may
    pick their own name (checked at duel/quiz join), falling back to a random
    generated one if they didn't set one or typed only unusable characters."""
    if student:
        return student.username
    # display_name isn't a utf8mb4 column — strip 4-byte chars (emoji etc.),
    # the same issue that broke the bot's display name earlier this session.
    name = ''.join(c for c in (requested_name or '').strip() if ord(c) <= 0xFFFF)[:64]
    return name if name else _generate_duel_display_name()


_BOT_DISPLAY_NAMES = {
    # No emoji here — the display_name column isn't utf8mb4, so 4-byte chars
    # (like 🤖) break the INSERT. Frontend prepends its own icon via is_bot.
    'easy': 'Robot (ľahký)',
    'medium': 'Robot (stredný)',
    'hard': 'Robot (ťažký)',
}


def generate_duel_code(length=8):
    chars = _string.ascii_uppercase + _string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        if not DuelGame.objects.filter(code=code).exists():
            return code


def _duel_slot_order(mode):
    if mode == '1v1':
        return [('A', 1), ('B', 1)]
    return [('A', 1), ('B', 1), ('A', 2), ('B', 2)]


def _next_open_duel_slot(game):
    taken = set(game.participants.values_list('team', 'slot'))
    for team, slot in _duel_slot_order(game.mode):
        if (team, slot) not in taken:
            return team, slot
    return None


def _serialize_duel_game(game):
    required_count = 2 if game.mode == '1v1' else 4
    participants = [{
        'team': p.team,
        'slot': p.slot,
        'display_name': p.display_name,
        'is_founder': p.is_founder,
        'is_bot': p.is_bot,
        'connected': p.connected,
        'correct_count': p.correct_count,
        'is_student': p.student_id is not None,
    } for p in game.participants.all()]
    return {
        'code': game.code,
        'mode': game.mode,
        'visibility': game.visibility,
        'status': game.status,
        'task_id': game.task_id,
        'task_name': game.task.name,
        'time_limit_seconds': game.time_limit_seconds,
        'target_steps': game.target_steps,
        'rope_position': game.rope_position,
        'winner_team': game.winner_team,
        'started_at': game.started_at.isoformat() if game.started_at else None,
        'required_count': required_count,
        'vs_bot': game.vs_bot,
        'bot_difficulty': game.bot_difficulty,
        'participants': participants,
    }


@api_view(['POST'])
def create_duel_game(request):
    student, session = get_user_identity(request)
    if not student and not session:
        return Response({'error': 'student_id or session_id required'}, status=status.HTTP_400_BAD_REQUEST)

    vs_bot = bool(request.data.get('vs_bot'))
    bot_difficulty = request.data.get('bot_difficulty') or 'medium'
    if vs_bot and bot_difficulty not in ('easy', 'medium', 'hard'):
        return Response({'error': 'Invalid bot_difficulty'}, status=status.HTTP_400_BAD_REQUEST)

    # A bot game is always a private 1v1 — there's no one else to match it against.
    mode = '1v1' if vs_bot else request.data.get('mode')
    visibility = 'private' if vs_bot else request.data.get('visibility')
    task_id = request.data.get('task_id')
    time_limit_seconds = request.data.get('time_limit_seconds')

    if mode not in ('1v1', '2v2') or visibility not in ('public', 'private') or not task_id or not time_limit_seconds:
        return Response({'error': 'mode, visibility, task_id and time_limit_seconds are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        time_limit_seconds = int(time_limit_seconds)
    except (TypeError, ValueError):
        return Response({'error': 'Invalid time_limit_seconds'}, status=status.HTTP_400_BAD_REQUEST)

    task = get_object_or_404(Task, id=task_id)
    if not task.example_set.exists():
        return Response({'error': 'Sada neobsahuje žiadne príklady'}, status=status.HTTP_400_BAD_REQUEST)

    game = DuelGame.objects.create(
        code=generate_duel_code(),
        mode=mode,
        visibility=visibility,
        task=task,
        time_limit_seconds=time_limit_seconds,
        vs_bot=vs_bot,
        bot_difficulty=bot_difficulty if vs_bot else None,
    )

    display_name = _resolve_display_name(student, request.data.get('display_name'))
    participant = DuelParticipant.objects.create(
        game=game, student=student, anonymous_session=session,
        team='A', slot=1, display_name=display_name, is_founder=True,
    )

    if vs_bot:
        # connected=True from the start — the bot has no socket of its own to open.
        DuelParticipant.objects.create(
            game=game, team='B', slot=1, is_bot=True, connected=True,
            display_name=_BOT_DISPLAY_NAMES.get(bot_difficulty, 'Robot 🤖'),
        )

    return Response({**_serialize_duel_game(game), 'you': {'team': participant.team, 'slot': participant.slot}},
                     status=status.HTTP_201_CREATED)


@api_view(['POST'])
def join_duel_game(request):
    student, session = get_user_identity(request)
    if not student and not session:
        return Response({'error': 'student_id or session_id required'}, status=status.HTTP_400_BAD_REQUEST)

    code = (request.data.get('code') or '').strip().upper()
    if not code:
        return Response({'error': 'code is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        game = DuelGame.objects.get(code=code)
    except DuelGame.DoesNotExist:
        return Response({'error': 'Hra s týmto kódom neexistuje'}, status=status.HTTP_404_NOT_FOUND)

    # Rejoin case (e.g. reconnect after a page refresh) — same identity already has a slot.
    existing = game.participants.filter(student=student, anonymous_session=session).first()
    if existing:
        return Response({**_serialize_duel_game(game), 'you': {'team': existing.team, 'slot': existing.slot}},
                         status=status.HTTP_200_OK)

    if game.status != 'waiting':
        return Response({'error': 'Hra už začala alebo skončila'}, status=status.HTTP_409_CONFLICT)

    slot = _next_open_duel_slot(game)
    if slot is None:
        return Response({'error': 'Hra je plná'}, status=status.HTTP_409_CONFLICT)

    team, slot_num = slot
    display_name = _resolve_display_name(student, request.data.get('display_name'))
    participant = DuelParticipant.objects.create(
        game=game, student=student, anonymous_session=session,
        team=team, slot=slot_num, display_name=display_name,
    )

    return Response({**_serialize_duel_game(game), 'you': {'team': participant.team, 'slot': participant.slot}},
                     status=status.HTTP_201_CREATED)


@api_view(['GET'])
def list_public_duel_games(request):
    games = DuelGame.objects.filter(visibility='public', status='waiting').select_related('task').order_by('-created_at')[:50]
    data = []
    for g in games:
        required_count = 2 if g.mode == '1v1' else 4
        data.append({
            'code': g.code,
            'mode': g.mode,
            'task_id': g.task_id,
            'task_name': g.task.name,
            'time_limit_seconds': g.time_limit_seconds,
            'participant_count': g.participants.count(),
            'required_count': required_count,
        })
    return Response(data)


@api_view(['GET'])
def get_duel_game_state(request, code):
    game = get_object_or_404(DuelGame, code=code.upper())
    return Response(_serialize_duel_game(game))


# ─── Live Quiz (Kahoot-style, host-paced) ────────────────────────────────────

def generate_quiz_code(length=8):
    chars = _string.ascii_uppercase + _string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        if not QuizGame.objects.filter(code=code).exists():
            return code


def _serialize_quiz_game(game):
    participants = list(game.participants.all())
    leaderboard = sorted(
        [{'id': p.id, 'display_name': p.display_name, 'score': p.score, 'connected': p.connected} for p in participants],
        key=lambda p: -p['score']
    )
    return {
        'code': game.code,
        'status': game.status,
        'task_id': game.task_id,
        'task_name': game.task.name,
        'current_question_index': game.current_question_index,
        'total_questions': len(game.question_order),
        'participant_count': len(participants),
        'leaderboard': leaderboard,
    }


@api_view(['POST'])
def create_quiz_game(request):
    teacher_id = request.data.get('teacher_id')
    task_id = request.data.get('task_id')
    if not teacher_id or not task_id:
        return Response({'error': 'teacher_id and task_id are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        teacher = Teacher.objects.get(id=teacher_id)
    except Teacher.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

    task = get_object_or_404(Task, id=task_id)
    example_ids = list(task.example_set.values_list('id', flat=True))
    if not example_ids:
        return Response({'error': 'Sada neobsahuje žiadne príklady'}, status=status.HTTP_400_BAD_REQUEST)

    random.shuffle(example_ids)
    game = QuizGame.objects.create(
        code=generate_quiz_code(),
        teacher=teacher,
        task=task,
        question_order=example_ids,
    )

    return Response(_serialize_quiz_game(game), status=status.HTTP_201_CREATED)


@api_view(['POST'])
def join_quiz_game(request):
    student, session = get_user_identity(request)
    if not student and not session:
        return Response({'error': 'student_id or session_id required'}, status=status.HTTP_400_BAD_REQUEST)

    code = (request.data.get('code') or '').strip().upper()
    if not code:
        return Response({'error': 'code is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        game = QuizGame.objects.get(code=code)
    except QuizGame.DoesNotExist:
        return Response({'error': 'Kvíz s týmto kódom neexistuje'}, status=status.HTTP_404_NOT_FOUND)

    # Rejoin case (e.g. reconnect after a page refresh) — same identity already has a slot.
    existing = game.participants.filter(student=student, anonymous_session=session).first()
    if existing:
        return Response({**_serialize_quiz_game(game), 'you': {'participant_id': existing.id}}, status=status.HTTP_200_OK)

    if game.status != 'waiting':
        return Response({'error': 'Kvíz už začal alebo skončil'}, status=status.HTTP_409_CONFLICT)

    display_name = _resolve_display_name(student, request.data.get('display_name'))
    participant = QuizParticipant.objects.create(game=game, student=student, anonymous_session=session, display_name=display_name)

    return Response({**_serialize_quiz_game(game), 'you': {'participant_id': participant.id}}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_quiz_game_state(request, code):
    game = get_object_or_404(QuizGame, code=code.upper())
    return Response(_serialize_quiz_game(game))
