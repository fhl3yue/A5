import asyncio
import base64
import hashlib
import json
from pathlib import Path
import time
from uuid import uuid4

import edge_tts
import httpx

from app.config import settings


_TTS_RUNTIME_STATUS = {
    "server_tts_provider": "auto",
    "local_tts_enabled": False,
    "local_tts_provider": "moss_onnx",
    "local_tts_base_url": "",
    "edge_tts_cache_enabled": True,
    "edge_tts_cache_items": 0,
    "edge_tts_cache_last_hit": False,
    "server_tts_ready": False,
    "last_provider": "",
    "last_error": "",
    "last_elapsed_seconds": 0.0,
}


def reset_tts_runtime_status() -> None:
    _TTS_RUNTIME_STATUS.update(
        {
            "server_tts_provider": _normalize_server_provider(settings.server_tts_provider),
            "local_tts_enabled": bool(settings.local_tts_enabled),
            "local_tts_provider": settings.local_tts_provider,
            "local_tts_base_url": settings.local_tts_base_url,
            "edge_tts_cache_enabled": bool(settings.edge_tts_cache_enabled),
            "edge_tts_cache_items": _edge_cache_count(),
            "edge_tts_cache_last_hit": False,
            "server_tts_ready": False,
            "last_provider": "",
            "last_error": "",
            "last_elapsed_seconds": 0.0,
        }
    )


def get_tts_runtime_status() -> dict:
    status = dict(_TTS_RUNTIME_STATUS)
    status.update(
        {
            "server_tts_provider": _normalize_server_provider(settings.server_tts_provider),
            "local_tts_enabled": bool(settings.local_tts_enabled),
            "local_tts_provider": settings.local_tts_provider,
            "local_tts_base_url": settings.local_tts_base_url,
            "edge_tts_cache_enabled": bool(settings.edge_tts_cache_enabled),
            "edge_tts_cache_items": _edge_cache_count(),
        }
    )
    return status


def _normalize_server_provider(raw_provider: str) -> str:
    provider = (raw_provider or "auto").strip().lower()
    if provider not in {"auto", "local", "edge"}:
        return "auto"
    return provider


def _normalize_local_provider(raw_provider: str) -> str:
    provider = (raw_provider or "moss_onnx").strip().lower()
    return provider or "moss_onnx"


def _set_tts_runtime_status(
    *,
    ready: bool,
    provider: str = "",
    error: str = "",
    elapsed_seconds: float = 0.0,
    edge_cache_hit: bool = False,
) -> None:
    _TTS_RUNTIME_STATUS.update(
        {
            "server_tts_provider": _normalize_server_provider(settings.server_tts_provider),
            "local_tts_enabled": bool(settings.local_tts_enabled),
            "local_tts_provider": settings.local_tts_provider,
            "local_tts_base_url": settings.local_tts_base_url,
            "edge_tts_cache_enabled": bool(settings.edge_tts_cache_enabled),
            "edge_tts_cache_items": _edge_cache_count(),
            "edge_tts_cache_last_hit": bool(edge_cache_hit),
            "server_tts_ready": bool(ready),
            "last_provider": provider,
            "last_error": error,
            "last_elapsed_seconds": round(float(elapsed_seconds), 3),
        }
    )


async def _synthesize_to_file(text: str, output_path: Path, voice_name: str | None = None) -> None:
    communicate = edge_tts.Communicate(text=text[: settings.tts_max_chars], voice=voice_name or settings.tts_voice)
    await communicate.save(str(output_path))


def _new_output_path(extension: str) -> tuple[str, Path]:
    safe_extension = extension if extension.startswith(".") else f".{extension}"
    output_name = f"answer_{uuid4().hex}{safe_extension}"
    return output_name, settings.audio_output_dir / output_name


def _edge_cache_dir() -> Path:
    return settings.audio_output_dir / "cache"


def _edge_cache_count() -> int:
    cache_dir = _edge_cache_dir()
    if not cache_dir.exists():
        return 0
    return sum(1 for _item in cache_dir.glob("edge_*.mp3"))


def _edge_cache_payload(text: str, voice_name: str | None) -> dict:
    return {
        "provider": "edge_tts",
        "cache_version": settings.edge_tts_cache_version,
        "voice_name": voice_name or settings.tts_voice,
        "tts_max_chars": settings.tts_max_chars,
        "text": text[: settings.tts_max_chars],
    }


def _edge_cache_path(text: str, voice_name: str | None) -> Path:
    payload = json.dumps(_edge_cache_payload(text, voice_name), ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return _edge_cache_dir() / f"edge_{digest}.mp3"


def _audio_url_from_path(path: Path) -> str:
    relative_path = path.relative_to(settings.audio_output_dir).as_posix()
    return f"/generated/audio/{relative_path}"


def _prune_edge_cache() -> None:
    max_items = int(settings.edge_tts_cache_max_items or 0)
    if max_items <= 0:
        return

    cache_dir = _edge_cache_dir()
    if not cache_dir.exists():
        return

    cached_files = sorted(
        cache_dir.glob("edge_*.mp3"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for stale_file in cached_files[max_items:]:
        stale_file.unlink(missing_ok=True)


def _delete_partial_file(output_path: Path) -> None:
    if output_path.exists():
        output_path.unlink(missing_ok=True)


def _write_audio_bytes(audio_bytes: bytes, extension: str) -> str | None:
    if not audio_bytes:
        return None
    output_name, output_path = _new_output_path(extension)
    output_path.write_bytes(audio_bytes)
    return f"/generated/audio/{output_name}"


def _extension_from_content_type(content_type: str) -> str:
    normalized = (content_type or "").lower()
    if "mpeg" in normalized or "mp3" in normalized:
        return ".mp3"
    if "ogg" in normalized:
        return ".ogg"
    if "webm" in normalized:
        return ".webm"
    return ".wav"


def _decode_json_audio(payload: dict) -> tuple[bytes, str]:
    audio_base64 = str(payload.get("audio_base64") or payload.get("audio") or "").strip()
    if not audio_base64:
        raise RuntimeError(str(payload.get("error") or "local TTS response did not include audio_base64"))
    return base64.b64decode(audio_base64), ".wav"


def _generate_moss_onnx_audio(text: str) -> str | None:
    base_url = (settings.local_tts_base_url or "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("LOCAL_TTS_BASE_URL is empty")

    data = {
        "text": text[: settings.tts_max_chars],
        "demo_id": settings.local_tts_demo_id,
        "max_new_frames": str(settings.local_tts_max_new_frames),
        "voice_clone_max_text_tokens": str(settings.local_tts_voice_clone_max_text_tokens),
        "enable_text_normalization": "1",
        "enable_normalize_tts_text": "1",
        "cpu_threads": str(settings.local_tts_cpu_threads),
        "attn_implementation": "fixed",
        "do_sample": "1",
        "seed": "0",
    }
    with httpx.Client(timeout=settings.local_tts_timeout_seconds, trust_env=False) as client:
        response = client.post(f"{base_url}/api/generate", data=data)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        audio_bytes, extension = _decode_json_audio(response.json())
    else:
        audio_bytes = response.content
        extension = _extension_from_content_type(content_type)
    return _write_audio_bytes(audio_bytes, extension)


def _generate_local_tts_audio(text: str, _voice_name: str | None = None) -> str | None:
    provider = _normalize_local_provider(settings.local_tts_provider)
    if provider != "moss_onnx":
        raise RuntimeError(f"Unsupported LOCAL_TTS_PROVIDER: {provider}")
    return _generate_moss_onnx_audio(text)


def _generate_edge_tts_audio(text: str, voice_name: str | None = None) -> tuple[str | None, bool]:
    if settings.edge_tts_cache_enabled:
        cache_path = _edge_cache_path(text, voice_name)
        if cache_path.exists() and cache_path.stat().st_size > 0:
            cache_path.touch()
            return _audio_url_from_path(cache_path), True

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = cache_path.with_name(f"{cache_path.stem}.{uuid4().hex}.tmp.mp3")
        try:
            asyncio.run(_synthesize_to_file(text, temp_path, voice_name))
            temp_path.replace(cache_path)
            _prune_edge_cache()
            return _audio_url_from_path(cache_path), False
        except Exception:
            _delete_partial_file(temp_path)
            raise

    output_name, output_path = _new_output_path(".mp3")
    try:
        asyncio.run(_synthesize_to_file(text, output_path, voice_name))
        return f"/generated/audio/{output_name}", False
    except Exception:
        _delete_partial_file(output_path)
        raise


def generate_tts_audio(text: str, voice_name: str | None = None, enabled: bool | None = None) -> str | None:
    if enabled is None:
        enabled = settings.enable_tts
    if not enabled:
        _set_tts_runtime_status(ready=False, error="TTS disabled")
        return None

    provider = _normalize_server_provider(settings.server_tts_provider)
    local_error = ""
    started = time.perf_counter()

    if provider in {"auto", "local"} and settings.local_tts_enabled:
        try:
            audio_url = _generate_local_tts_audio(text, voice_name)
            if audio_url:
                _set_tts_runtime_status(
                    ready=True,
                    provider=f"local_{_normalize_local_provider(settings.local_tts_provider)}",
                    elapsed_seconds=time.perf_counter() - started,
                )
                return audio_url
            local_error = "local TTS returned empty audio"
        except Exception as exc:
            local_error = str(exc)
        if provider == "local":
            _set_tts_runtime_status(
                ready=False,
                provider=f"local_{_normalize_local_provider(settings.local_tts_provider)}",
                error=local_error,
                elapsed_seconds=time.perf_counter() - started,
            )
            return None

    if provider in {"auto", "edge"}:
        try:
            audio_url, cache_hit = _generate_edge_tts_audio(text, voice_name)
            if audio_url:
                _set_tts_runtime_status(
                    ready=True,
                    provider="edge_tts_cache" if cache_hit else "edge_tts",
                    elapsed_seconds=time.perf_counter() - started,
                    edge_cache_hit=cache_hit,
                )
                return audio_url
        except Exception as exc:
            edge_error = str(exc)
            joined_error = "; ".join(item for item in (local_error, edge_error) if item)
            _set_tts_runtime_status(
                ready=False,
                provider="edge_tts",
                error=joined_error,
                elapsed_seconds=time.perf_counter() - started,
            )
            return None

    _set_tts_runtime_status(
        ready=False,
        error=local_error or "No TTS provider attempted",
        elapsed_seconds=time.perf_counter() - started,
    )
    return None
