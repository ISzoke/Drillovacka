"""
================================================================================
 Module: example_report_cloud_sync.py
 Description:
        Synchronizes example report JSON payloads to MEGA cloud.
================================================================================
"""

import json
import os
import threading
from datetime import datetime

from .mega_cloud import mega_upload_enabled, upload_file_to_mega
from .models import ExampleReport


REPORT_DIR = "survey"
os.makedirs(REPORT_DIR, exist_ok=True)

_upload_lock = threading.Lock()
_uploading_ids: set = set()


def _report_json_path(report):
    timestamp = report.created_at.strftime("%Y%m%d%H%M%S") if report.created_at else datetime.utcnow().strftime("%Y%m%d%H%M%S")
    actor = str(report.student_id) if report.student_id else report.anonymous_session.session_id if report.anonymous_session_id else "unknown"
    filename = f"example_report_{timestamp}_{actor}_{report.id}.json"
    return os.path.join(REPORT_DIR, filename)


def _build_report_payload(report):
    return {
        "record_kind": "example_report",
        "report_id": report.id,
        "created_at": report.created_at.isoformat() if report.created_at else datetime.utcnow().isoformat(),
        "student_id": report.student_id,
        "anonymous_session_id": report.anonymous_session_id,
        "example_id": report.example_id,
        "report_type": report.report_type,
        "note": report.note,
        "input_type": report.input_type,
        "language": report.language,
        "example_text": report.example_text,
        "correct_answer": report.correct_answer,
        "practiced_skill_ids": report.practiced_skill_ids,
        "practiced_skill_names": report.practiced_skill_names,
        "meta": report.meta,
    }


def sync_report_to_mega(report):
    if not mega_upload_enabled():
        return {"uploaded": False, "reason": "mega_disabled"}

    with _upload_lock:
        if report.id in _uploading_ids:
            return {"uploaded": False, "reason": "already_uploading"}
        _uploading_ids.add(report.id)

    try:
        json_path = _report_json_path(report)
        payload = _build_report_payload(report)
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

        upload_result = upload_file_to_mega(json_path)
        meta = dict(report.meta or {})
        meta.update(
            {
                "record_kind": "example_report",
                "mega_uploaded": upload_result.get("uploaded", False),
                "mega_json_url": upload_result.get("public_url", ""),
                "mega_error": upload_result.get("error", ""),
                "local_json_path": json_path,
                "local_json_name": os.path.basename(json_path),
            }
        )
        report.meta = meta
        report.save(update_fields=["meta"])

        delete_local = str(os.getenv("MEGA_DELETE_LOCAL_AFTER_UPLOAD", "false")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if delete_local and upload_result.get("uploaded") and os.path.exists(json_path):
            try:
                os.remove(json_path)
            except Exception as exc:
                meta = dict(report.meta or {})
                meta["mega_cleanup_error"] = f"json_cleanup_failed: {exc}"
                report.meta = meta
                report.save(update_fields=["meta"])

        return {
            "uploaded": upload_result.get("uploaded", False),
            "error": upload_result.get("error", ""),
            "public_url": upload_result.get("public_url", ""),
        }
    except Exception as exc:
        meta = dict(report.meta or {})
        meta["mega_error"] = str(exc)
        report.meta = meta
        report.save(update_fields=["meta"])
        return {"uploaded": False, "error": str(exc), "public_url": ""}
    finally:
        with _upload_lock:
            _uploading_ids.discard(report.id)


def retry_pending_report_uploads(limit=10):
    if not mega_upload_enabled():
        return {"processed": 0, "uploaded": 0, "reason": "mega_disabled"}

    candidates = ExampleReport.objects.order_by('-created_at')[: max(limit * 10, 50)]

    processed = 0
    uploaded = 0
    for report in candidates:
        if processed >= limit:
            break

        meta = report.meta or {}
        if meta.get("mega_uploaded"):
            continue

        with _upload_lock:
            if report.id in _uploading_ids:
                continue

        result = sync_report_to_mega(report)
        processed += 1
        if result.get("uploaded"):
            uploaded += 1

    return {"processed": processed, "uploaded": uploaded}
