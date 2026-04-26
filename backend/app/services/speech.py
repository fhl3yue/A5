from pathlib import Path
from threading import Lock

from faster_whisper import WhisperModel

from app.config import settings
from app.utils import normalize_text


_model_instance: WhisperModel | None = None
_model_name: str | None = None
_model_lock = Lock()


def _load_model(model_name: str) -> WhisperModel:
    return WhisperModel(
        model_name,
        device=settings.asr_device,
        compute_type=settings.asr_compute_type,
    )


def get_asr_model() -> WhisperModel:
    global _model_instance, _model_name
    if _model_instance is None:
        with _model_lock:
            if _model_instance is None:
                preferred = settings.asr_model_size
                fallbacks = []
                if preferred != "tiny":
                    fallbacks.append("tiny")
                last_error: Exception | None = None
                for candidate in [preferred, *fallbacks]:
                    try:
                        _model_instance = _load_model(candidate)
                        _model_name = candidate
                        break
                    except Exception as exc:
                        last_error = exc
                        _model_instance = None
                        _model_name = None
                if _model_instance is None and last_error is not None:
                    raise last_error
    return _model_instance


def transcribe_audio_file(file_path: Path) -> str:
    if not settings.enable_asr:
        raise RuntimeError("ASR is disabled.")

    model = get_asr_model()
    try:
        segments, _info = model.transcribe(
            str(file_path),
            beam_size=3,
            language=settings.asr_language or None,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=settings.asr_initial_prompt or None,
        )
    except Exception:
        global _model_instance, _model_name
        if _model_name != "tiny":
            with _model_lock:
                _model_instance = _load_model("tiny")
                _model_name = "tiny"
            segments, _info = _model_instance.transcribe(
                str(file_path),
                beam_size=3,
                language=settings.asr_language or None,
                vad_filter=True,
                condition_on_previous_text=False,
                initial_prompt=settings.asr_initial_prompt or None,
            )
        else:
            raise
    transcript = "".join(segment.text for segment in segments)
    return normalize_text(transcript)
