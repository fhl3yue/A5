import hashlib
import json
from pathlib import Path
import subprocess
from uuid import uuid4

from app.config import BASE_DIR, settings


DEFAULT_MOUTH_CUES = {
    "metadata": {"soundFile": "", "duration": 0},
    "mouthCues": [],
}


def _resolve_rhubarb_path() -> Path:
    raw_path = Path(settings.rhubarb_bin_path)
    if raw_path.is_absolute():
        return raw_path
    return BASE_DIR / raw_path


def rhubarb_available() -> bool:
    return _resolve_rhubarb_path().exists()


def _audio_path_from_url(audio_url: str) -> Path | None:
    prefix = "/generated/audio/"
    if not audio_url or not audio_url.startswith(prefix):
        return None
    relative = audio_url[len(prefix) :].replace("/", "\\")
    candidate = (settings.audio_output_dir / relative).resolve()
    try:
        candidate.relative_to(settings.audio_output_dir.resolve())
    except ValueError:
        return None
    return candidate if candidate.exists() else None


def _cache_key(audio_path: Path) -> str:
    stat = audio_path.stat()
    payload = {
        "provider": "rhubarb",
        "audio_path": str(audio_path.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _lipsync_url_from_path(path: Path) -> str:
    relative_path = path.relative_to(settings.lipsync_output_dir).as_posix()
    return f"/generated/lipsync/{relative_path}"


def _read_mouth_cue_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    cues = payload.get("mouthCues")
    return len(cues) if isinstance(cues, list) else 0


def generate_lipsync_for_audio(audio_url: str) -> dict:
    audio_path = _audio_path_from_url(audio_url)
    if audio_path is None:
        return _empty_result("unavailable")

    settings.lipsync_output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = settings.lipsync_output_dir / f"rhubarb_{_cache_key(audio_path)}.json"
    if settings.lipsync_cache_enabled and cache_path.exists() and cache_path.stat().st_size > 0:
        return {
            "lipsync_url": _lipsync_url_from_path(cache_path),
            "lipsync_provider": "rhubarb_cache",
            "mouth_cue_count": _read_mouth_cue_count(cache_path),
        }

    if not settings.enable_rhubarb_lipsync:
        return _empty_result("disabled")

    rhubarb_path = _resolve_rhubarb_path()
    if not rhubarb_path.exists():
        return _empty_result("missing_rhubarb")

    temp_path = cache_path.with_name(f"{cache_path.stem}.{uuid4().hex}.tmp.json")
    command = [
        str(rhubarb_path),
        "-f",
        "json",
        "-o",
        str(temp_path),
        str(audio_path),
    ]
    try:
        subprocess.run(
            command,
            cwd=str(BASE_DIR),
            check=True,
            capture_output=True,
            text=True,
            timeout=settings.lipsync_timeout_seconds,
        )
        temp_path.replace(cache_path)
        return {
            "lipsync_url": _lipsync_url_from_path(cache_path),
            "lipsync_provider": "rhubarb",
            "mouth_cue_count": _read_mouth_cue_count(cache_path),
        }
    except Exception:
        temp_path.unlink(missing_ok=True)
        return _empty_result("failed")


def _empty_result(provider: str) -> dict:
    return {
        "lipsync_url": None,
        "lipsync_provider": provider,
        "mouth_cue_count": 0,
    }


def lipsync_status() -> dict:
    return {
        "rhubarb_enabled": bool(settings.enable_rhubarb_lipsync),
        "rhubarb_available": rhubarb_available(),
        "rhubarb_bin_path": str(_resolve_rhubarb_path()),
        "lipsync_cache_enabled": bool(settings.lipsync_cache_enabled),
        "lipsync_cache_items": sum(1 for _item in settings.lipsync_output_dir.glob("rhubarb_*.json"))
        if settings.lipsync_output_dir.exists()
        else 0,
    }
