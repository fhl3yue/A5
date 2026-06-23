import os
import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_base_dir() -> Path:
    override = os.environ.get("SCENIC_AI_BASE_DIR")
    if override:
        return Path(override).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


BASE_DIR = resolve_base_dir()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Scenic AI Guide Backend"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    cors_origins: str = "http://127.0.0.1:5173,http://127.0.0.1:5174"
    database_url: str = "sqlite:///./data/generated/scenic_ai.db"
    model_api_key: str = ""
    model_base_url: str = ""
    model_name: str = ""
    model_timeout_seconds: float = 1.2
    enable_english_translation: bool = True
    english_model_api_key: str = ""
    english_model_base_url: str = ""
    english_model_name: str = ""
    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.edgefn.net/v1"
    embedding_model: str = "BAAI/bge-m3"
    enable_rag: bool = True
    rag_top_k: int = 5
    enable_vision_guide: bool = True
    vision_model_api_key: str = ""
    vision_model_base_url: str = "https://api.edgefn.net/v1"
    vision_model_name: str = "GLM-4.5V"
    vision_model_timeout_seconds: float = 45.0
    vision_image_max_mb: int = 8
    admin_username: str = "admin"
    admin_password: str = "admin123"
    official_materials_dir: str = "C:/Users/LWQ/Documents/Playground/cnsoftbei_a5_data"
    enable_tts: bool = True
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_max_chars: int = 520
    server_tts_provider: str = "auto"
    edge_tts_cache_enabled: bool = True
    edge_tts_cache_max_items: int = 300
    edge_tts_cache_version: str = "v1"
    enable_rhubarb_lipsync: bool = False
    rhubarb_bin_path: str = "tools/rhubarb/rhubarb.exe"
    lipsync_cache_enabled: bool = True
    lipsync_timeout_seconds: float = 12.0
    local_tts_enabled: bool = False
    local_tts_provider: str = "moss_onnx"
    local_tts_base_url: str = "http://127.0.0.1:18083"
    local_tts_timeout_seconds: float = 8.0
    local_tts_demo_id: str = "demo-1"
    local_tts_max_new_frames: int = 240
    local_tts_voice_clone_max_text_tokens: int = 75
    local_tts_cpu_threads: int = 0
    enable_english_tts: bool = True
    english_tts_voice: str = "en-US-JennyNeural"
    digital_video_enabled: bool = False
    digital_video_base_url: str = ""
    digital_video_api_key: str = ""
    digital_video_avatar_id: str = "default"
    digital_video_timeout_seconds: int = 8
    avatar_only_enabled: bool = False
    avatar_only_base_url: str = "http://127.0.0.1:18085"
    avatar_only_timeout_seconds: float = 45.0
    openavatar_enabled: bool = False
    openavatar_base_url: str = "http://127.0.0.1:8282"
    openavatar_ui_url: str = "http://127.0.0.1:8282/ui/index.html"
    openavatar_mode: str = "disabled"
    openavatar_profile: str = "Legacy full OpenAvatarChat iframe"
    openavatar_timeout_seconds: float = 2.0
    enable_asr: bool = True
    asr_model_size: str = "base"
    asr_device: str = "cpu"
    asr_compute_type: str = "int8"
    asr_language: str = "zh"
    asr_initial_prompt: str = (
        "灵山胜境，九龙灌浴，菩提大道，灵山大佛，灵山梵宫，祥符禅寺，五印坛城，佛教文化，景区导览"
    )
    raw_data_dir: Path = Field(default=BASE_DIR / "data" / "raw")
    processed_data_dir: Path = Field(default=BASE_DIR / "data" / "processed")
    generated_data_dir: Path = Field(default=BASE_DIR / "data" / "generated")
    sample_data_dir: Path = Field(default=BASE_DIR / "data" / "sample")
    audio_output_dir: Path = Field(default=BASE_DIR / "data" / "generated" / "audio")
    lipsync_output_dir: Path = Field(default=BASE_DIR / "data" / "generated" / "lipsync")
    avatar_output_dir: Path = Field(default=BASE_DIR / "data" / "generated" / "avatar")
    upload_temp_dir: Path = Field(default=BASE_DIR / "data" / "generated" / "uploads")

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()


def ensure_runtime_dirs() -> None:
    for path in (
        settings.raw_data_dir,
        settings.processed_data_dir,
        settings.generated_data_dir,
        settings.sample_data_dir,
        settings.audio_output_dir,
        settings.lipsync_output_dir,
        settings.avatar_output_dir,
        settings.upload_temp_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
