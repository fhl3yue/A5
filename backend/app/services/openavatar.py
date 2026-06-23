from __future__ import annotations

import time
from urllib.parse import urljoin

import httpx

from app.config import settings


_last_status: dict = {
    "ready": False,
    "last_error": "",
    "last_elapsed_seconds": 0.0,
    "checked_at": 0.0,
}


def _base_url() -> str:
    return settings.openavatar_base_url.strip().rstrip("/")


def _probe_url(path: str) -> str:
    return urljoin(f"{_base_url()}/", path.lstrip("/"))


def get_openavatar_status() -> dict:
    enabled = bool(settings.openavatar_enabled)
    configured = bool(_base_url() and settings.openavatar_ui_url.strip())
    status = {
        "enabled": enabled,
        "configured": configured,
        "ready": False,
        "base_url": _base_url(),
        "ui_url": settings.openavatar_ui_url.strip(),
        "mode": settings.openavatar_mode.strip() or "iframe",
        "profile": settings.openavatar_profile.strip(),
        "last_error": "",
        "last_elapsed_seconds": 0.0,
    }

    if not enabled:
        status["last_error"] = "OpenAvatarChat sidecar disabled"
        return status
    if not configured:
        status["last_error"] = "OpenAvatarChat sidecar URL missing"
        return status

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=max(0.5, float(settings.openavatar_timeout_seconds)), trust_env=False) as client:
            response = client.get(_probe_url("/readiness"))
            if response.status_code >= 400:
                response = client.get(_probe_url("/liveness"))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        elapsed = round(time.perf_counter() - started, 3)
        _last_status.update(
            {
                "ready": False,
                "last_error": str(exc)[:220],
                "last_elapsed_seconds": elapsed,
                "checked_at": time.time(),
            }
        )
    else:
        elapsed = round(time.perf_counter() - started, 3)
        _last_status.update(
            {
                "ready": True,
                "last_error": "",
                "last_elapsed_seconds": elapsed,
                "checked_at": time.time(),
            }
        )

    status.update(_last_status)
    return status
