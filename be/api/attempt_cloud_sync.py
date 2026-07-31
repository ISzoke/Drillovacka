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


def ensure_attempt_sidecar(attempt):
    """
    Create or refresh a local JSON sidecar for the attempt and persist its path in meta.
    Returns absolute local path to the sidecar, or an empty string if unavailable.
    """
    if not attempt.audio_file_path:
        return ""

    local_audio = _resolve_local_path(attempt.audio_file_path)
    if local_audio:
        sidecar_path = _sidecar_path_for_audio(local_audio)
    else:
        candidate_audio = (
            attempt.audio_file_path
            if os.path.isabs(attempt.audio_file_path)
            else os.path.join(os.getcwd(), attempt.audio_file_path)
        )
        sidecar_path = _sidecar_path_for_audio(candidate_audio)

    if not sidecar_path:
        return ""

    sidecar_payload = _build_sidecar_payload(attempt)
    with open(sidecar_path, "w", encoding="utf-8") as sidecar_file:
        json.dump(sidecar_payload, sidecar_file, indent=2, ensure_ascii=False)

    meta = dict(attempt.meta or {})
    meta.update(
        {
            "paired_json_local_path": sidecar_path,
            "paired_json_name": os.path.basename(sidecar_path),
        }
    )
    attempt.meta = meta
    try:
        attempt.save(update_fields=["meta"])
    except ValueError:
        pass  # attempt was cascade-deleted (delete-record) before sync completed

    return sidecar_path


def sync_attempt_to_mega(attempt):
    """
    Uploads attempt audio and paired JSON sidecar to MEGA.
    Returns dict with upload status details.
    Skips silently if the same attempt is already being uploaded in another thread.
    """
    if not attempt.audio_file_path:
        return {"uploaded": False, "reason": "no_audio_path"}

    try:
        ensure_attempt_sidecar(attempt)
    except Exception as exc:
        return {"uploaded": False, "reason": f"sidecar_write_failed: {exc}"}

    if not mega_upload_enabled():
        return {"uploaded": False, "reason": "mega_disabled"}

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

    sidecar_path = ensure_attempt_sidecar(attempt)
    if not sidecar_path:
        return {"uploaded": False, "reason": "sidecar_missing_locally"}

    audio_upload = upload_file_to_mega(local_audio, dest_folder="audioprompts")
    json_upload = upload_file_to_mega(sidecar_path, dest_folder="audioprompts")

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
    try:
        attempt.save(update_fields=["meta"])
    except ValueError:
        pass  # attempt was cascade-deleted (delete-record) before sync completed

    # If both files are uploaded and cleanup is enabled, remove local copies.
    if _should_delete_local() and audio_upload.get("uploaded") and json_upload.get("uploaded"):
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
            try:
                attempt.save(update_fields=["meta"])
            except ValueError:
                pass  # attempt was cascade-deleted (delete-record) before sync completed

    return {
        "uploaded": audio_upload.get("uploaded", False) and json_upload.get("uploaded", False),
        "audio_uploaded": audio_upload.get("uploaded", False),
        "json_uploaded": json_upload.get("uploaded", False),
        "audio_error": audio_upload.get("error", ""),
        "json_error": json_upload.get("error", ""),
    }


WRITE_ATTEMPT_DIR = "write_attempts"
os.makedirs(WRITE_ATTEMPT_DIR, exist_ok=True)

TEACHER_PROMPTS_DIR = "teacher_prompts"
os.makedirs(TEACHER_PROMPTS_DIR, exist_ok=True)


def _should_delete_local():
    return str(os.getenv("MEGA_DELETE_LOCAL_AFTER_UPLOAD", "false")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def sync_write_attempt_to_mega(attempt):
    """
    Upload a JSON record for a write/text attempt to MEGA.
    No audio file — only metadata JSON is uploaded.
    """
    if not mega_upload_enabled():
        return {"uploaded": False, "reason": "mega_disabled"}

    with _upload_lock:
        if attempt.id in _uploading_ids:
            return {"uploaded": False, "reason": "already_uploading"}
        _uploading_ids.add(attempt.id)

    try:
        return _do_write_sync(attempt)
    finally:
        with _upload_lock:
            _uploading_ids.discard(attempt.id)


def _do_write_sync(attempt):
    local_path = os.path.join(WRITE_ATTEMPT_DIR, f"attempt_{attempt.id}.json")

    try:
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(_build_sidecar_payload(attempt), f, indent=2, ensure_ascii=False)
    except Exception as exc:
        return {"uploaded": False, "reason": f"json_write_failed: {exc}"}

    upload_result = upload_file_to_mega(local_path, dest_folder="audioprompts")

    meta = dict(attempt.meta or {})
    meta.update({
        "mega_json_uploaded": upload_result.get("uploaded", False),
        "mega_json_url": upload_result.get("public_url", ""),
        "mega_json_error": upload_result.get("error", ""),
        "write_json_local_path": local_path,
    })
    attempt.meta = meta
    try:
        attempt.save(update_fields=["meta"])
    except ValueError:
        pass  # attempt was cascade-deleted (delete-record) before sync completed

    if _should_delete_local() and upload_result.get("uploaded"):
        try:
            os.remove(local_path)
        except Exception:
            pass

    uploaded = upload_result.get("uploaded", False)
    return {
        "uploaded": uploaded,
        "json_uploaded": uploaded,
        "json_error": upload_result.get("error", ""),
    }


def sync_teacher_prompt_to_mega(task, teacher, examples, generation_prompt=None, generation_params=None):
    """
    Save teacher AI generation prompt + result as a JSON file locally and upload to MEGA.
    Called after teacher_save_task in a background thread.
    File saved to teacher_prompts/task_{id}_{timestamp}.json regardless of MEGA status.
    """
    from datetime import timezone as tz
    timestamp = datetime.now(tz.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"task_{task.id}_{timestamp}.json"
    local_path = os.path.join(TEACHER_PROMPTS_DIR, filename)

    payload = {
        "task_id": task.id,
        "task_name": task.name,
        "form": task.form,
        "created_at": task.id,  # placeholder — teacher just created it
        "teacher": {
            "id": teacher.id,
            "email": teacher.email,
            "name": f"{teacher.first_name} {teacher.last_name}",
        },
        "generation_prompt": generation_prompt if generation_prompt is not None else task.generation_prompt,
        "generation_params": generation_params if generation_params is not None else task.generation_params,
        "examples": [
            {
                "example": ex.get("example", ""),
                "input_type": ex.get("input_type", ""),
                "answer": ex.get("answer", ""),
            }
            for ex in examples
        ],
    }

    try:
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        return {"saved": False, "reason": f"json_write_failed: {exc}"}

    result = {"saved": True, "local_path": local_path}

    if mega_upload_enabled():
        upload = upload_file_to_mega(local_path, dest_folder="teacher_prompts")
        result["mega_uploaded"] = upload.get("uploaded", False)
        result["mega_url"] = upload.get("public_url", "")
        result["mega_error"] = upload.get("error", "")

        if _should_delete_local() and upload.get("uploaded"):
            try:
                os.remove(local_path)
            except Exception:
                pass

    return result


def _retry_pending(source, sync_fn, done_check, limit):
    """
    Shared retry loop: fetches recent attempts of the given source, skips already-uploaded
    ones via done_check, and calls sync_fn on the rest until limit is reached.
    Over-fetches by 10x so that already-completed records can be skipped cheaply in Python.
    """
    if not mega_upload_enabled():
        return {"processed": 0, "uploaded": 0, "reason": "mega_disabled"}

    candidates = ExampleAttempt.objects.filter(
        source=source,
    ).order_by('-created_at')[:max(limit * 10, 50)]

    processed = 0
    uploaded = 0

    for attempt in candidates:
        if processed >= limit:
            break

        if done_check(attempt.meta or {}):
            continue

        with _upload_lock:
            if attempt.id in _uploading_ids:
                continue

        result = sync_fn(attempt)
        processed += 1
        if result.get("uploaded"):
            uploaded += 1

    return {"processed": processed, "uploaded": uploaded}


def retry_pending_write_uploads(limit=10):
    """
    Retry pending MEGA uploads for recent write/text attempts.
    Trigger this opportunistically after each new write attempt.
    """
    return _retry_pending(
        source='text',
        sync_fn=sync_write_attempt_to_mega,
        done_check=lambda meta: bool(meta.get("mega_json_uploaded")),
        limit=limit,
    )


def retry_pending_attempt_uploads(limit=10):
    """
    Retry pending MEGA uploads for recent speech attempts.
    Trigger this opportunistically after each new speech attempt.
    """
    return _retry_pending(
        source='speech',
        sync_fn=sync_attempt_to_mega,
        done_check=lambda meta: bool(meta.get("mega_uploaded") and meta.get("mega_json_uploaded")),
        limit=limit,
    )
