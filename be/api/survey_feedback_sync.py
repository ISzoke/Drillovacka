"""
================================================================================
 Module: survey_feedback_sync.py
 Description:
        Stores survey/final-feedback answers in DB and synchronizes their JSON
        payloads plus optional voice audio to MEGA cloud.
================================================================================
"""

import io
import json
import os
import re
import threading
import uuid
import wave
from datetime import datetime

from .mega_cloud import mega_upload_enabled, upload_file_to_mega
from .models import AnonymousSession, Skill, Student, SurveyFeedback


SURVEY_DIR = "survey"
os.makedirs(SURVEY_DIR, exist_ok=True)

_upload_lock = threading.Lock()
_uploading_ids: set = set()


def _slugify(value):
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "feedback"


def _serialize_actor(student, anonymous_session):
    if student:
        return str(student.id)
    if anonymous_session:
        return anonymous_session.session_id
    return "unknown"


def _skill_names(skill_ids):
    if not skill_ids:
        return []
    return list(Skill.objects.filter(id__in=skill_ids).values_list("name", flat=True))


def _convert_pcm_to_wav(pcm_data):
    with io.BytesIO() as wav_io:
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm_data)
        return wav_io.getvalue()


def _feedback_json_path(feedback):
    timestamp = feedback.created_at.strftime("%Y%m%d%H%M%S") if feedback.created_at else datetime.utcnow().strftime("%Y%m%d%H%M%S")
    actor = _serialize_actor(feedback.student, feedback.anonymous_session)
    question_type = _slugify(feedback.question_type)
    filename = f"survey_feedback_{question_type}_{feedback.source}_{timestamp}_{actor}_{feedback.id}.json"
    return os.path.join(SURVEY_DIR, filename)


def _build_feedback_payload(feedback):
    return {
        "record_kind": "survey_feedback",
        "feedback_id": feedback.id,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else datetime.utcnow().isoformat(),
        "student_id": feedback.student_id,
        "anonymous_session_id": feedback.anonymous_session_id,
        "question_type": feedback.question_type,
        "question_text": feedback.question_text,
        "answer": feedback.answer,
        "source": feedback.source,
        "language": feedback.language,
        "practiced_skill_ids": feedback.practiced_skill_ids,
        "practiced_skill_names": feedback.practiced_skill_names,
        "audio_file_name": os.path.basename(feedback.audio_file_path or ""),
        "meta": feedback.meta,
    }


def _save_feedback_audio(feedback, audio_bytes):
    if not audio_bytes:
        return ""

    timestamp = feedback.created_at.strftime("%Y%m%d%H%M%S") if feedback.created_at else datetime.utcnow().strftime("%Y%m%d%H%M%S")
    actor = _serialize_actor(feedback.student, feedback.anonymous_session)
    question_type = _slugify(feedback.question_type)
    filename = f"survey_feedback_{question_type}_voice_{timestamp}_{actor}_{feedback.id}_{uuid.uuid4().hex[:8]}.wav"
    path = os.path.join(SURVEY_DIR, filename)

    with open(path, "wb") as handle:
        handle.write(_convert_pcm_to_wav(audio_bytes))

    return path


def create_survey_feedback(
    *,
    question_type,
    question_text,
    answer,
    skills=None,
    student_id=None,
    session_id=None,
    language="",
    source="text",
    audio_bytes=None,
    audio_format="",
):
    student = None
    anonymous_session = None

    if student_id:
        student = Student.objects.filter(id=student_id).first()
    elif session_id:
        anonymous_session = AnonymousSession.objects.filter(session_id=session_id).first()

    if not student and not anonymous_session:
        raise ValueError("Student ID or Session ID is required")

    skill_ids = [int(skill_id) for skill_id in (skills or [])]
    skill_names = _skill_names(skill_ids)

    feedback = SurveyFeedback.objects.create(
        student=student,
        anonymous_session=anonymous_session,
        question_type=question_type or "",
        question_text=question_text or "",
        answer=answer or "",
        source=source or "text",
        language=language or "",
        practiced_skill_ids=skill_ids,
        practiced_skill_names=skill_names,
        audio_format=audio_format or "",
        meta={
            "record_kind": "survey_feedback",
            "question_type": question_type or "",
            "source": source or "text",
        },
    )

    if audio_bytes:
        feedback.audio_file_path = _save_feedback_audio(feedback, audio_bytes)
        feedback.save(update_fields=["audio_file_path"])

    return feedback


def sync_survey_feedback_to_mega(feedback):
    if not mega_upload_enabled():
        return {"uploaded": False, "reason": "mega_disabled"}

    with _upload_lock:
        if feedback.id in _uploading_ids:
            return {"uploaded": False, "reason": "already_uploading"}
        _uploading_ids.add(feedback.id)

    try:
        json_path = _feedback_json_path(feedback)
        payload = _build_feedback_payload(feedback)
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

        json_upload = upload_file_to_mega(json_path, dest_folder="survey")

        audio_upload = {"uploaded": False, "public_url": "", "error": ""}
        local_audio = feedback.audio_file_path
        if local_audio:
            if os.path.exists(local_audio):
                audio_upload = upload_file_to_mega(local_audio, dest_folder="survey")
            else:
                audio_upload = {"uploaded": False, "public_url": "", "error": "Local audio missing"}

        uploaded_all = json_upload.get("uploaded", False) and (
            audio_upload.get("uploaded", False) if local_audio else True
        )

        meta = dict(feedback.meta or {})
        meta.update(
            {
                "record_kind": "survey_feedback",
                "mega_uploaded": uploaded_all,
                "mega_json_uploaded": json_upload.get("uploaded", False),
                "mega_json_url": json_upload.get("public_url", ""),
                "mega_json_error": json_upload.get("error", ""),
                "mega_audio_uploaded": audio_upload.get("uploaded", False),
                "mega_audio_url": audio_upload.get("public_url", ""),
                "mega_audio_error": audio_upload.get("error", ""),
                "local_json_path": json_path,
                "local_json_name": os.path.basename(json_path),
            }
        )
        feedback.meta = meta
        feedback.save(update_fields=["meta"])

        delete_local = str(os.getenv("MEGA_DELETE_LOCAL_AFTER_UPLOAD", "false")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if delete_local and uploaded_all:
            cleanup_error = ""
            try:
                if os.path.exists(json_path):
                    os.remove(json_path)
            except Exception as exc:
                cleanup_error = f"json_cleanup_failed: {exc}"

            if local_audio:
                try:
                    if os.path.exists(local_audio):
                        os.remove(local_audio)
                except Exception as exc:
                    msg = f"audio_cleanup_failed: {exc}"
                    cleanup_error = f"{cleanup_error}; {msg}" if cleanup_error else msg

            if cleanup_error:
                meta = dict(feedback.meta or {})
                meta["mega_cleanup_error"] = cleanup_error
                feedback.meta = meta
                feedback.save(update_fields=["meta"])

        return {
            "uploaded": uploaded_all,
            "json_uploaded": json_upload.get("uploaded", False),
            "audio_uploaded": audio_upload.get("uploaded", False),
            "json_error": json_upload.get("error", ""),
            "audio_error": audio_upload.get("error", ""),
            "json_public_url": json_upload.get("public_url", ""),
            "audio_public_url": audio_upload.get("public_url", ""),
        }
    except Exception as exc:
        meta = dict(feedback.meta or {})
        meta["mega_error"] = str(exc)
        feedback.meta = meta
        feedback.save(update_fields=["meta"])
        return {"uploaded": False, "error": str(exc)}
    finally:
        with _upload_lock:
            _uploading_ids.discard(feedback.id)


def retry_pending_survey_feedback_uploads(limit=10):
    if not mega_upload_enabled():
        return {"processed": 0, "uploaded": 0, "reason": "mega_disabled"}

    candidates = SurveyFeedback.objects.order_by("-created_at")[: max(limit * 10, 50)]

    processed = 0
    uploaded = 0
    for feedback in candidates:
        if processed >= limit:
            break

        meta = feedback.meta or {}
        if meta.get("mega_uploaded"):
            continue

        with _upload_lock:
            if feedback.id in _uploading_ids:
                continue

        result = sync_survey_feedback_to_mega(feedback)
        processed += 1
        if result.get("uploaded"):
            uploaded += 1

    return {"processed": processed, "uploaded": uploaded}
