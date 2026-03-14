"""
================================================================================
 Module: mega_cloud.py
 Description:
        Optional MEGA cloud uploader for audio attempt files.
        Uses environment variables and fails gracefully if disabled/unconfigured.
================================================================================
"""

import os
import asyncio
import types
from threading import Lock


# mega.py still expects asyncio.coroutine on newer Python versions.
if not hasattr(asyncio, "coroutine"):
    asyncio.coroutine = types.coroutine


_CLIENT = None
_CLIENT_ERROR = None
_LOCK = Lock()


def _as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def mega_upload_enabled():
    return _as_bool(os.getenv("MEGA_UPLOAD_ENABLED", "false"))


def _get_client():
    global _CLIENT, _CLIENT_ERROR

    if _CLIENT is not None:
        return _CLIENT

    if _CLIENT_ERROR is not None:
        raise RuntimeError(_CLIENT_ERROR)

    with _LOCK:
        if _CLIENT is not None:
            return _CLIENT

        email = os.getenv("MEGA_EMAIL", "").strip()
        password = os.getenv("MEGA_PASSWORD", "").strip()

        if not email or not password:
            _CLIENT_ERROR = "MEGA credentials are missing"
            raise RuntimeError(_CLIENT_ERROR)

        try:
            from mega import Mega  # type: ignore
        except Exception as exc:
            _CLIENT_ERROR = f"mega.py import failed: {exc}"
            raise RuntimeError(_CLIENT_ERROR)

        try:
            mega = Mega()
            _CLIENT = mega.login(email, password)
            return _CLIENT
        except Exception as exc:
            _CLIENT_ERROR = f"MEGA login failed: {exc}"
            raise RuntimeError(_CLIENT_ERROR)


def upload_file_to_mega(local_path):
    """
    Upload file to MEGA and return metadata.
    Returns dict:
      {
        'uploaded': bool,
        'public_url': str,
        'error': str,
      }
    """
    if not mega_upload_enabled():
        return {"uploaded": False, "public_url": "", "error": "MEGA upload disabled"}

    if not local_path or not os.path.exists(local_path):
        return {"uploaded": False, "public_url": "", "error": "Local file missing"}

    try:
        client = _get_client()
        uploaded = client.upload(local_path)
        public_url = client.get_upload_link(uploaded)
        return {"uploaded": True, "public_url": public_url or "", "error": ""}
    except Exception as exc:
        return {"uploaded": False, "public_url": "", "error": str(exc)}
