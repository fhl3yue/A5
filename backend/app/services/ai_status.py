from app.config import settings
from app.services.audio import get_tts_runtime_status
from app.services.digital_video import get_digital_video_status
from app.services.embedding import embedding_configured
from app.services.lipsync import lipsync_status
from app.services.openavatar import get_openavatar_status
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
    lipsync = lipsync_status()
    openavatar = get_openavatar_status()
    notes: list[str] = []

    if not settings.model_api_key and settings.english_model_api_key:
        notes.append("Main Chinese model is not configured; do not reuse English-only credentials for production.")
    if not embedding_configured():
        notes.append("Embedding is not configured; RAG falls back to keyword retrieval.")
    if settings.enable_vision_guide and not vision_model_configured():
        notes.append("Vision guide is enabled but the vision model key is missing.")
    if not video_status["enabled"]:
        notes.append("Digital video is disabled; audio-driven lipsync remains the fallback.")
    elif video_status.get("avatar_only_enabled") and not video_status.get("avatar_only_ready"):
        notes.append("Avatar-only LiteAvatar sidecar is enabled but not ready.")
    if not lipsync["rhubarb_enabled"]:
        notes.append("Rhubarb lipsync is disabled; frontend RMS/rhythm lipsync is used as fallback.")
    if openavatar["enabled"] and not openavatar["ready"]:
        notes.append("OpenAvatarChat sidecar is not ready; visitor page keeps the current 2D avatar fallback.")

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
        "edge_tts_cache_enabled": tts_status["edge_tts_cache_enabled"],
        "edge_tts_cache_items": tts_status["edge_tts_cache_items"],
        "edge_tts_cache_last_hit": tts_status["edge_tts_cache_last_hit"],
        "server_tts_ready": tts_status["server_tts_ready"],
        "server_tts_last_provider": tts_status["last_provider"],
        "server_tts_last_error": tts_status["last_error"],
        "server_tts_last_elapsed_seconds": tts_status["last_elapsed_seconds"],
        "english_available": _english_configured(),
        "english_tts_enabled": settings.enable_english_tts,
        "lipsync_available": True,
        "rhubarb_lipsync_enabled": lipsync["rhubarb_enabled"],
        "rhubarb_lipsync_available": lipsync["rhubarb_available"],
        "lipsync_cache_enabled": lipsync["lipsync_cache_enabled"],
        "lipsync_cache_items": lipsync["lipsync_cache_items"],
        "digital_video_enabled": video_status["enabled"],
        "digital_video_configured": video_status["configured"],
        "avatar_only_enabled": video_status["avatar_only_enabled"],
        "avatar_only_configured": video_status["avatar_only_configured"],
        "avatar_only_ready": video_status["avatar_only_ready"],
        "avatar_only_base_url": video_status["avatar_only_base_url"],
        "openavatar_enabled": openavatar["enabled"],
        "openavatar_configured": openavatar["configured"],
        "openavatar_ready": openavatar["ready"],
        "openavatar_ui_url": openavatar["ui_url"],
        "openavatar_mode": openavatar["mode"],
        "openavatar_profile": openavatar["profile"],
        "openavatar_last_error": openavatar["last_error"],
        "openavatar_last_elapsed_seconds": openavatar["last_elapsed_seconds"],
        "status_notes": notes,
    }
