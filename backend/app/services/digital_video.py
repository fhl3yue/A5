from dataclasses import dataclass
from uuid import uuid4

import httpx

from app.config import settings


@dataclass
class DigitalVideoResult:
    video_url: str | None = None
    video_status: str = "disabled"


def _build_endpoint_url() -> str:
    base_url = settings.digital_video_base_url.strip().rstrip("/")
    if base_url.endswith("/api/digital-video/generate"):
        return base_url
    return f"{base_url}/api/digital-video/generate"


def generate_digital_video(text: str, audio_url: str | None) -> DigitalVideoResult:
    if not settings.digital_video_enabled:
        return DigitalVideoResult(video_status="disabled")
    if not settings.digital_video_base_url.strip():
        return DigitalVideoResult(video_status="error")

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
        response = httpx.post(_build_endpoint_url(), json=payload, headers=headers, timeout=timeout_seconds + 1)
        response.raise_for_status()
        body = response.json()
    except httpx.TimeoutException:
        return DigitalVideoResult(video_status="timeout")
    except Exception:
        return DigitalVideoResult(video_status="error")

    status = str(body.get("status") or "").strip().lower()
    video_url = body.get("video_url") or None
    if video_url and status in {"", "ok", "success"}:
        status = "ready"
    if status == "ready" and video_url:
        return DigitalVideoResult(video_url=str(video_url), video_status="ready")
    return DigitalVideoResult(video_status=status or "error")
