from app.config import settings
from app.services.digital_video import get_digital_video_status
from app.services.embedding import embedding_configured


def _main_model_name() -> str:
    return settings.model_name or settings.english_model_name


def _main_model_configured() -> bool:
    return bool(
        (settings.model_api_key or settings.english_model_api_key)
        and (settings.model_base_url or settings.english_model_base_url)
        and _main_model_name()
    )


def _english_configured() -> bool:
    return bool(
        settings.enable_english_translation
        and settings.english_model_api_key
        and settings.english_model_base_url
        and settings.english_model_name
    )


def build_ai_status() -> dict:
    video_status = get_digital_video_status()
    notes: list[str] = []
    if not settings.model_api_key and settings.english_model_api_key:
        notes.append("中文主模型复用本机英文模型中转配置，未复制密钥。")
    if not embedding_configured():
        notes.append("Embedding 未配置时，RAG 自动降级为关键词检索。")
    if not video_status["enabled"]:
        notes.append("外部数字人视频未启用，当前使用本地音频驱动口型同步。")

    return {
        "main_model_configured": _main_model_configured(),
        "main_model_name": _main_model_name(),
        "rag_enabled": settings.enable_rag,
        "rag_configured": embedding_configured(),
        "tts_enabled": settings.enable_tts,
        "english_available": _english_configured(),
        "english_tts_enabled": settings.enable_english_tts,
        "lipsync_available": True,
        "digital_video_enabled": video_status["enabled"],
        "digital_video_configured": video_status["configured"],
        "status_notes": notes,
    }
