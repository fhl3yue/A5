from app.config import settings
from app.services.digital_video import get_digital_video_status
from app.services.embedding import embedding_configured
from app.services.audio import get_tts_runtime_status
from app.services.vision import vision_model_configured, vision_model_display_name


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
    tts_status = get_tts_runtime_status()
    notes: list[str] = []
    if not settings.model_api_key and settings.english_model_api_key:
        notes.append("中文主模型复用本机英文模型中转配置，未复制密钥。")
    if not embedding_configured():
        notes.append("Embedding 未配置时，RAG 自动降级为关键词检索。")
    if settings.enable_vision_guide and not vision_model_configured():
        notes.append("多模态视觉模型未配置时，图片识别导览不可用。")
    if not video_status["enabled"]:
        notes.append("外部数字人视频未启用，当前使用本地音频驱动口型同步。")

    return {
        "main_model_configured": _main_model_configured(),
        "main_model_name": _main_model_name(),
        "rag_enabled": settings.enable_rag,
        "rag_configured": embedding_configured(),
        "vision_enabled": settings.enable_vision_guide,
        "vision_configured": vision_model_configured(),
        "vision_model_name": vision_model_display_name(),
        "tts_enabled": settings.enable_tts,
        "server_tts_provider": tts_status["server_tts_provider"],
        "local_tts_enabled": tts_status["local_tts_enabled"],
        "local_tts_provider": tts_status["local_tts_provider"],
        "local_tts_base_url": tts_status["local_tts_base_url"],
        "server_tts_ready": tts_status["server_tts_ready"],
        "server_tts_last_provider": tts_status["last_provider"],
        "server_tts_last_error": tts_status["last_error"],
        "server_tts_last_elapsed_seconds": tts_status["last_elapsed_seconds"],
        "english_available": _english_configured(),
        "english_tts_enabled": settings.enable_english_tts,
        "lipsync_available": True,
        "digital_video_enabled": video_status["enabled"],
        "digital_video_configured": video_status["configured"],
        "status_notes": notes,
    }
