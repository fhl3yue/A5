import threading
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import QALog
from app.services.audio import generate_tts_audio


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
        return {
            "log_id": log.id,
            "audio_status": (log.audio_status or "pending").strip() or "pending",
            "audio_url": audio_url,
            "lipsync_available": bool(audio_url),
            "tts_mode_used": "server_async" if audio_url or log.audio_status != "not_requested" else "browser_local",
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
        db.commit()
        queue_answer_audio(log.id, log.answer, voice_name)
        audio_status = "pending"

    return {
        "log_id": log.id,
        "audio_status": audio_status,
        "audio_url": audio_url,
        "lipsync_available": bool(audio_url),
        "tts_mode_used": "server_async",
    }


def _build_answer_audio(log_id: int, text: str, voice_name: str | None = None) -> None:
    started = time.perf_counter()
    audio_url = generate_tts_audio(text, voice_name)
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
    finally:
        db.close()
