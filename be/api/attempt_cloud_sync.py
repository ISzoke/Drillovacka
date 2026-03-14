"""
================================================================================
 Module: attempt_cloud_sync.py
 Description:
        Synchronizes speech attempt assets (audio + paired JSON sidecar)
        to MEGA cloud with retry support.
================================================================================
"""

import json
import os
import threading
from datetime import datetime

from .mega_cloud import mega_upload_enabled, upload_file_to_mega
from .models import ExampleAttempt

# Track attempt IDs currently being uploaded to prevent concurrent duplicates.
_upload_lock = threading.Lock()
_uploading_ids: set = set()


def _resolve_local_path(path_value):
    if not path_value:
        return ""

    if os.path.exists(path_value) and os.path.isfile(path_value):
        return path_value

    abs_candidate = os.path.join(os.getcwd(), path_value)
    if os.path.exists(abs_candidate) and os.path.isfile(abs_candidate):
        return abs_candidate

    return ""


def _sidecar_path_for_audio(audio_path):
    if not audio_path:
        return ""
    base, _ = os.path.splitext(audio_path)
    return f"{base}.json"


def _build_sidecar_payload(attempt):
    return {
        "attempt_id": attempt.id,
        "created_at": attempt.created_at.isoformat() if attempt.created_at else datetime.utcnow().isoformat(),
        "student_id": attempt.student_id,
        "anonymous_session_id": attempt.anonymous_session_id,
        "example_id": attempt.example_id,
        "attempt_number": attempt.attempt_number,
        "source": attempt.source,
        "input_type": attempt.input_type,
        "language": attempt.language,
        "action": attempt.action,
        "is_correct": attempt.is_correct,
        "duration_ms": attempt.duration,
        "transcription": attempt.transcription,
        "parsed_answer": attempt.parsed_answer,
        "example_text": attempt.example_text,
        "correct_answer": attempt.correct_answer,
        "practiced_skill_ids": attempt.practiced_skill_ids,
        "practiced_skill_names": attempt.practiced_skill_names,
        "meta": attempt.meta,
    }


def sync_attempt_to_mega(attempt):
    """
    Uploads attempt audio and paired JSON sidecar to MEGA.
    Returns dict with upload status details.
    Skips silently if the same attempt is already being uploaded in another thread.
    """
    if not mega_upload_enabled():
        return {"uploaded": False, "reason": "mega_disabled"}

    if not attempt.audio_file_path:
        return {"uploaded": False, "reason": "no_audio_path"}

    # Guard against concurrent duplicate uploads of the same attempt.
    with _upload_lock:
        if attempt.id in _uploading_ids:
            return {"uploaded": False, "reason": "already_uploading"}
        _uploading_ids.add(attempt.id)

    try:
        return _do_sync(attempt)
    finally:
        with _upload_lock:
            _uploading_ids.discard(attempt.id)


def _do_sync(attempt):
    local_audio = _resolve_local_path(attempt.audio_file_path)
    if not local_audio:
        return {"uploaded": False, "reason": "audio_missing_locally"}

    # Build paired JSON file with same basename as audio.
    sidecar_path = _sidecar_path_for_audio(local_audio)
    sidecar_payload = _build_sidecar_payload(attempt)
    try:
        with open(sidecar_path, "w", encoding="utf-8") as sidecar_file:
            json.dump(sidecar_payload, sidecar_file, indent=2, ensure_ascii=False)
    except Exception as exc:
        return {"uploaded": False, "reason": f"sidecar_write_failed: {exc}"}

    audio_upload = upload_file_to_mega(local_audio)
    json_upload = upload_file_to_mega(sidecar_path)

    meta = dict(attempt.meta or {})
    meta.update(
        {
            "mega_uploaded": audio_upload.get("uploaded", False),
            "mega_audio_url": audio_upload.get("public_url", ""),
            "mega_json_uploaded": json_upload.get("uploaded", False),
            "mega_json_url": json_upload.get("public_url", ""),
            "mega_error": audio_upload.get("error", ""),
            "mega_json_error": json_upload.get("error", ""),
            "paired_json_local_path": sidecar_path,
            "paired_json_name": os.path.basename(sidecar_path),
        }
    )
    attempt.meta = meta
    attempt.save(update_fields=["meta"])

    # If both files are uploaded and cleanup is enabled, remove local copies.
    delete_local = str(os.getenv("MEGA_DELETE_LOCAL_AFTER_UPLOAD", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if delete_local and audio_upload.get("uploaded") and json_upload.get("uploaded"):
        cleanup_error = ""
        try:
            os.remove(local_audio)
        except Exception as exc:
            cleanup_error = f"audio_cleanup_failed: {exc}"

        try:
            if os.path.exists(sidecar_path):
                os.remove(sidecar_path)
        except Exception as exc:
            cleanup_error = f"{cleanup_error}; json_cleanup_failed: {exc}" if cleanup_error else f"json_cleanup_failed: {exc}"

        if cleanup_error:
            meta = dict(attempt.meta or {})
            meta["mega_cleanup_error"] = cleanup_error
            attempt.meta = meta
            attempt.save(update_fields=["meta"])

    return {
        "uploaded": audio_upload.get("uploaded", False) and json_upload.get("uploaded", False),
        "audio_uploaded": audio_upload.get("uploaded", False),
        "json_uploaded": json_upload.get("uploaded", False),
        "audio_error": audio_upload.get("error", ""),
        "json_error": json_upload.get("error", ""),
    }


def retry_pending_attempt_uploads(limit=10):
    """
    Retry pending MEGA uploads for recent speech attempts.
    Trigger this opportunistically after each new speech attempt.
    """
    if not mega_upload_enabled():
        return {"processed": 0, "uploaded": 0, "reason": "mega_disabled"}

    candidates = ExampleAttempt.objects.filter(
        source='speech',
    ).order_by('-created_at')[: max(limit * 10, 50)]

    processed = 0
    uploaded = 0

    for attempt in candidates:
        if processed >= limit:
            break

        meta = attempt.meta or {}
        if meta.get("mega_uploaded") and meta.get("mega_json_uploaded"):
            continue

        # Skip attempts currently being uploaded in another thread.
        with _upload_lock:
            if attempt.id in _uploading_ids:
                continue

        result = sync_attempt_to_mega(attempt)
        processed += 1
        if result.get("uploaded"):
            uploaded += 1

    return {"processed": processed, "uploaded": uploaded}
