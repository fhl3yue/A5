from dataclasses import dataclass
import time
from uuid import uuid4

import httpx

from app.config import settings


@dataclass
class DigitalVideoResult:
    video_url: str | None = None
    video_status: str = "disabled"
    message: str = ""


_VIDEO_STATS = {
    "total_requests": 0,
    "fallback_count": 0,
    "total_response_seconds": 0.0,
    "last_status": "disabled",
    "last_message": "",
    "last_failure_reason": "",
}


def _record_status(status: str, elapsed: float = 0.0, message: str = "") -> None:
    _VIDEO_STATS["last_status"] = status
    _VIDEO_STATS["last_message"] = message
    if status != "disabled":
        _VIDEO_STATS["total_requests"] += 1
        _VIDEO_STATS["total_response_seconds"] += elapsed
    if status not in {"ready", "disabled"}:
        _VIDEO_STATS["fallback_count"] += 1
        _VIDEO_STATS["last_failure_reason"] = message or status
    elif status == "ready":
        _VIDEO_STATS["last_failure_reason"] = ""


def get_digital_video_status() -> dict:
    total_requests = int(_VIDEO_STATS["total_requests"])
    average = 0.0
    if total_requests:
        average = round(float(_VIDEO_STATS["total_response_seconds"]) / total_requests, 3)
    return {
        "enabled": settings.digital_video_enabled,
        "configured": bool(settings.digital_video_base_url.strip()),
        "avatar_id": settings.digital_video_avatar_id,
        "last_status": str(_VIDEO_STATS["last_status"]),
        "last_message": str(_VIDEO_STATS["last_message"]),
        "last_failure_reason": str(_VIDEO_STATS["last_failure_reason"]),
        "average_response_seconds": average,
        "fallback_count": int(_VIDEO_STATS["fallback_count"]),
        "total_requests": total_requests,
    }


def _build_endpoint_url() -> str:
    base_url = settings.digital_video_base_url.strip().rstrip("/")
    if base_url.endswith("/api/digital-video/generate"):
        return base_url
    return f"{base_url}/api/digital-video/generate"


def generate_digital_video(text: str, audio_url: str | None) -> DigitalVideoResult:
    if not settings.digital_video_enabled:
        _record_status("disabled", message="digital video disabled")
        return DigitalVideoResult(video_status="disabled")
    if not settings.digital_video_base_url.strip():
        _record_status("error", message="digital video base url missing")
        return DigitalVideoResult(video_status="error", message="digital video base url missing")

    timeout_seconds = max(1, int(settings.digital_video_timeout_seconds or 8))
    payload = {
        "request_id": uuid4().hex,
        "avatar_id": settings.digital_video_avatar_id,
        "text": text,
        "audio_url": audio_url,
        "max_wait_seconds": timeout_seconds,
    }
    headers = {}
    if settings.digital_video_api_key:
        headers["Authorization"] = f"Bearer {settings.digital_video_api_key}"

    try:
        started = time.perf_counter()
        response = httpx.post(_build_endpoint_url(), json=payload, headers=headers, timeout=timeout_seconds + 1)
        response.raise_for_status()
        body = response.json()
        elapsed = time.perf_counter() - started
    except httpx.TimeoutException:
        _record_status("timeout", elapsed=timeout_seconds, message="digital video timeout")
        return DigitalVideoResult(video_status="timeout", message="digital video timeout")
    except Exception as exc:
        _record_status("error", message=str(exc)[:180])
        return DigitalVideoResult(video_status="error", message=str(exc)[:180])

    status = str(body.get("status") or "").strip().lower()
    video_url = body.get("video_url") or None
    message = str(body.get("message") or "")
    if video_url and status in {"", "ok", "success"}:
        status = "ready"
    if status == "ready" and video_url:
        _record_status("ready", elapsed=elapsed, message=message or "ready")
        return DigitalVideoResult(video_url=str(video_url), video_status="ready", message=message)
    final_status = status or "error"
    _record_status(final_status, elapsed=elapsed, message=message or final_status)
    return DigitalVideoResult(video_status=final_status, message=message)
