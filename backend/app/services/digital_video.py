from dataclasses import dataclass
from pathlib import Path
import time
from uuid import uuid4
from urllib.parse import urljoin

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


def _avatar_only_base_url() -> str:
    return settings.avatar_only_base_url.strip().rstrip("/")


def _avatar_only_endpoint(path: str) -> str:
    return urljoin(f"{_avatar_only_base_url()}/", path.lstrip("/"))


def _audio_path_from_url(audio_url: str | None) -> Path | None:
    if not audio_url:
        return None
    prefix = "/generated/audio/"
    if not audio_url.startswith(prefix):
        return None
    relative = audio_url[len(prefix) :].replace("/", "\\")
    candidate = (settings.audio_output_dir / relative).resolve()
    try:
        candidate.relative_to(settings.audio_output_dir.resolve())
    except ValueError:
        return None
    return candidate if candidate.exists() else None


def _copy_avatar_video_from_sidecar(client: httpx.Client, body: dict, request_id: str) -> str | None:
    file_path = str(body.get("file_path") or "").strip()
    output_path = settings.avatar_output_dir / f"avatar_{request_id}.mp4"
    if file_path:
        source = Path(file_path)
        if source.exists() and source.is_file():
            output_path.write_bytes(source.read_bytes())
            return f"/generated/avatar/{output_path.name}"

    video_url = str(body.get("video_url") or "").strip()
    if not video_url:
        return None
    media_url = video_url if video_url.startswith(("http://", "https://")) else _avatar_only_endpoint(video_url)
    response = client.get(media_url, timeout=max(5.0, float(settings.avatar_only_timeout_seconds)))
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return f"/generated/avatar/{output_path.name}"


def _probe_avatar_only() -> tuple[bool, str, float]:
    if not settings.avatar_only_enabled:
        return False, "avatar-only disabled", 0.0
    if not _avatar_only_base_url():
        return False, "avatar-only base url missing", 0.0
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=min(3.0, max(0.5, float(settings.openavatar_timeout_seconds))), trust_env=False) as client:
            response = client.get(_avatar_only_endpoint("/health"))
            response.raise_for_status()
    except Exception as exc:
        return False, str(exc)[:180], round(time.perf_counter() - started, 3)
    return True, "", round(time.perf_counter() - started, 3)


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
    avatar_ready, avatar_error, avatar_elapsed = _probe_avatar_only()
    return {
        "enabled": settings.digital_video_enabled or settings.avatar_only_enabled,
        "configured": bool(settings.digital_video_base_url.strip()) or bool(_avatar_only_base_url()),
        "avatar_id": settings.digital_video_avatar_id,
        "last_status": str(_VIDEO_STATS["last_status"]),
        "last_message": str(_VIDEO_STATS["last_message"]) or avatar_error,
        "last_failure_reason": str(_VIDEO_STATS["last_failure_reason"]),
        "average_response_seconds": average,
        "fallback_count": int(_VIDEO_STATS["fallback_count"]),
        "total_requests": total_requests,
        "provider": "avatar_only" if settings.avatar_only_enabled else "external",
        "avatar_only_enabled": settings.avatar_only_enabled,
        "avatar_only_configured": bool(_avatar_only_base_url()),
        "avatar_only_ready": avatar_ready,
        "avatar_only_base_url": _avatar_only_base_url(),
        "avatar_only_last_elapsed_seconds": avatar_elapsed,
    }


def _build_endpoint_url() -> str:
    base_url = settings.digital_video_base_url.strip().rstrip("/")
    if base_url.endswith("/api/digital-video/generate"):
        return base_url
    return f"{base_url}/api/digital-video/generate"


def _generate_avatar_only_video(text: str, audio_url: str | None) -> DigitalVideoResult:
    if not settings.avatar_only_enabled:
        return DigitalVideoResult(video_status="disabled")
    if not _avatar_only_base_url():
        _record_status("error", message="avatar-only base url missing")
        return DigitalVideoResult(video_status="error", message="avatar-only base url missing")

    audio_path = _audio_path_from_url(audio_url)
    if audio_path is None:
        _record_status("waiting_audio", message="avatar-only waiting for local audio file")
        return DigitalVideoResult(video_status="waiting_audio", message="avatar-only waiting for local audio file")

    timeout_seconds = max(3.0, float(settings.avatar_only_timeout_seconds or 45))
    request_id = uuid4().hex
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout_seconds + 3, trust_env=False) as client:
            with audio_path.open("rb") as audio_file:
                files = {"audio": (audio_path.name, audio_file, "audio/mpeg")}
                data = {
                    "request_id": request_id,
                    "text": text or "",
                    "voice_hint": settings.tts_voice or "",
                }
                response = client.post(_avatar_only_endpoint("/avatar/speak"), data=data, files=files)
            response.raise_for_status()
            body = response.json()
            video_url = _copy_avatar_video_from_sidecar(client, body, request_id)
            elapsed = time.perf_counter() - started
    except httpx.TimeoutException:
        _record_status("timeout", elapsed=timeout_seconds, message="avatar-only timeout")
        return DigitalVideoResult(video_status="timeout", message="avatar-only timeout")
    except Exception as exc:
        _record_status("error", elapsed=time.perf_counter() - started, message=f"avatar-only: {str(exc)[:160]}")
        return DigitalVideoResult(video_status="error", message=f"avatar-only: {str(exc)[:160]}")

    if video_url:
        _record_status("ready", elapsed=elapsed, message="avatar-only ready")
        return DigitalVideoResult(video_url=video_url, video_status="ready", message="avatar-only ready")
    _record_status("error", elapsed=elapsed, message="avatar-only returned no video")
    return DigitalVideoResult(video_status="error", message="avatar-only returned no video")


def generate_digital_video(text: str, audio_url: str | None) -> DigitalVideoResult:
    if settings.avatar_only_enabled:
        return _generate_avatar_only_video(text, audio_url)

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
