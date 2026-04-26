from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


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
    admin_username: str = "admin"
    admin_password: str = "admin123"
    official_materials_dir: str = "C:/Users/LWQ/Documents/Playground/cnsoftbei_a5_data"
    enable_tts: bool = True
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
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
        settings.upload_temp_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
