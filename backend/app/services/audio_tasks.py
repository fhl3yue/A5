import re
import threading
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import QALog
from app.services.audio import generate_tts_audio
from app.services.digital_video import generate_digital_video
from app.services.lipsync import generate_lipsync_for_audio


SPOKEN_TEXT_MIN_CHARS = 80
SPOKEN_TEXT_MAX_CHARS = 360
_SPOKEN_METADATA_HINTS = (
    "参考来源",
    "引用来源",
    "来源：",
    "来源:",
    "RAG",
    "answer_source",
    "model_name",
)


def _prefer_guide_narration(text: str) -> str:
    """For image answers, keep the actual guide explanation ahead of raw vision description."""
    if "多模态识别：" not in text:
        return text

    candidates: list[str] = []
    for marker in (
        "的文化含义是：",
        "的开放或演出时间是：",
        "的参观亮点是：",
        "位于",
        "坐落",
        "地处",
    ):
        index = text.find(marker)
        if index < 0:
            continue
        start = index
        while start > 0 and text[start - 1] not in "。！？!?；;\n":
            start -= 1
        candidates.append(text[start:].strip())

    if candidates:
        return min(candidates, key=len)

    marker = "初步判断为"
    index = text.find(marker)
    if index >= 0:
        end = text.find("。", index)
        if end >= 0:
            return text[end + 1 :].strip() or text
    return text


def _safe_spoken_cut(text: str, max_chars: int = SPOKEN_TEXT_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text.strip()

    window = text[:max_chars]
    cut_at = -1
    for mark in ("。", "！", "？", "；", ";"):
        cut_at = max(cut_at, window.rfind(mark))
    if cut_at < SPOKEN_TEXT_MIN_CHARS:
        for mark in ("，", "、", ","):
            cut_at = max(cut_at, window.rfind(mark))
    selected = window[: cut_at + 1] if cut_at >= SPOKEN_TEXT_MIN_CHARS else window

    quote_marks = "“”‘’\"'"
    if sum(1 for char in selected if char in quote_marks) % 2 == 1:
        last_quote = max(selected.rfind(mark) for mark in quote_marks)
        if last_quote >= SPOKEN_TEXT_MIN_CHARS:
            selected = selected[:last_quote]

    selected = selected.strip(" ，,；;、")
    if selected and selected[-1] not in "。！？!?":
        selected = f"{selected}。"
    return selected


def build_spoken_answer_text(answer: str) -> str:
    """Build a short, natural narration text for server-side TTS."""
    text = re.sub(r"<[^>]+>", "", answer or "")
    lines = []
    for raw_line in text.replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if any(hint in line for hint in _SPOKEN_METADATA_HINTS):
            continue
        line = re.sub(r"^\s*(?:[-*•]+|\d+[.、])\s*", "", line)
        lines.append(line)

    text = re.sub(r"\s+", " ", " ".join(lines)).strip()
    text = _prefer_guide_narration(text)
    if not text:
        return ""
    if len(text) <= SPOKEN_TEXT_MAX_CHARS:
        return text

    sentences = [item.strip() for item in re.split(r"(?<=[。！？!?；;])", text) if item.strip()]
    selected = ""
    for sentence in sentences:
        candidate = f"{selected}{sentence}" if selected else sentence
        if len(candidate) > SPOKEN_TEXT_MAX_CHARS:
            break
        selected = candidate
        if len(selected) >= SPOKEN_TEXT_MIN_CHARS:
            break

    if not selected:
        return _safe_spoken_cut(text)

    return _safe_spoken_cut(selected)


def queue_answer_audio(log_id: int, text: str, voice_name: str | None = None) -> None:
    worker = threading.Thread(
        target=_build_answer_audio,
        args=(log_id, text, voice_name),
        daemon=True,
        name=f"qa-audio-{log_id}",
    )
    worker.start()


def get_audio_status(log_id: int) -> dict | None:
    db = SessionLocal()
    try:
        log = db.get(QALog, log_id)
        if log is None:
            return None
        audio_url = log.audio_url.strip() or None
        lipsync = generate_lipsync_for_audio(audio_url) if audio_url else {
            "lipsync_url": None,
            "lipsync_provider": "",
            "mouth_cue_count": 0,
        }
        return {
            "log_id": log.id,
            "audio_status": (log.audio_status or "pending").strip() or "pending",
            "audio_url": audio_url,
            "lipsync_available": bool(lipsync.get("lipsync_url")) or bool(audio_url),
            "lipsync_url": lipsync.get("lipsync_url"),
            "lipsync_provider": lipsync.get("lipsync_provider", ""),
            "mouth_cue_count": lipsync.get("mouth_cue_count", 0),
            "tts_mode_used": "server_async" if audio_url or log.audio_status != "not_requested" else "browser_local",
            "video_url": log.video_url.strip() or None,
            "video_status": (log.video_status or "disabled").strip() or "disabled",
            "video_message": log.video_message or "",
        }
    finally:
        db.close()


def request_answer_audio(db: Session, log_id: int, voice_name: str | None = None) -> dict | None:
    log = db.get(QALog, log_id)
    if log is None:
        return None

    audio_url = log.audio_url.strip() or None
    audio_status = (log.audio_status or "pending").strip() or "pending"
    if audio_url:
        audio_status = "ready"
    elif audio_status != "pending":
        log.audio_status = "pending"
        log.audio_ready_seconds = 0.0
        log.video_status = "waiting_audio"
        log.video_message = ""
        db.commit()
        queue_answer_audio(log.id, log.answer, voice_name)
        audio_status = "pending"

    lipsync = generate_lipsync_for_audio(audio_url) if audio_url else {
        "lipsync_url": None,
        "lipsync_provider": "",
        "mouth_cue_count": 0,
    }
    return {
        "log_id": log.id,
        "audio_status": audio_status,
        "audio_url": audio_url,
        "lipsync_available": bool(lipsync.get("lipsync_url")) or bool(audio_url),
        "lipsync_url": lipsync.get("lipsync_url"),
        "lipsync_provider": lipsync.get("lipsync_provider", ""),
        "mouth_cue_count": lipsync.get("mouth_cue_count", 0),
        "tts_mode_used": "server_async",
        "video_url": log.video_url.strip() or None,
        "video_status": (log.video_status or "disabled").strip() or "disabled",
        "video_message": log.video_message or "",
    }


def _build_answer_audio(log_id: int, text: str, voice_name: str | None = None) -> None:
    started = time.perf_counter()
    spoken_text = build_spoken_answer_text(text)
    audio_url = generate_tts_audio(spoken_text, voice_name) if spoken_text else None
    elapsed = round(time.perf_counter() - started, 3)

    db = SessionLocal()
    try:
        log = db.execute(select(QALog).where(QALog.id == log_id)).scalar_one_or_none()
        if log is None:
            return
        log.audio_url = audio_url or ""
        log.audio_status = "ready" if audio_url else "failed"
        log.audio_ready_seconds = elapsed
        db.commit()
        if audio_url:
            generate_lipsync_for_audio(audio_url)
            _build_answer_video(log.id, spoken_text, audio_url)
    finally:
        db.close()


def _build_answer_video(log_id: int, text: str, audio_url: str) -> None:
    started = time.perf_counter()
    db = SessionLocal()
    try:
        log = db.execute(select(QALog).where(QALog.id == log_id)).scalar_one_or_none()
        if log is None:
            return
        log.video_status = "pending"
        log.video_message = "avatar-only rendering"
        db.commit()
    finally:
        db.close()

    result = generate_digital_video(text, audio_url)
    elapsed = round(time.perf_counter() - started, 3)

    db = SessionLocal()
    try:
        log = db.execute(select(QALog).where(QALog.id == log_id)).scalar_one_or_none()
        if log is None:
            return
        log.video_url = result.video_url or ""
        log.video_status = result.video_status or "disabled"
        log.video_message = result.message[:255] if result.message else ""
        log.video_ready_seconds = elapsed
        db.commit()
    finally:
        db.close()
