from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DigitalHumanConfig


DEFAULT_CONFIG = {
    "name": "灵灵",
    "role_title": "景区 AI 导览员",
    "scenic_area": "灵山胜境",
    "outfit_theme": "asset-avatar",
    "voice_name": "zh-CN-XiaoxiaoNeural",
    "greeting": "当前示范景区为灵山胜境，已接入对应知识库、路线推荐与语音播报能力。",
    "avatar_asset_url": "/app/assets/avatar/avatar-guide-v1.png",
    "video_provider_status": "外部视频 API",
    "fallback_message": "数字人视频暂不可用，已切换为语音讲解。",
    "service_boundary": "仅基于景区知识库进行导览讲解，不提供功德承诺、神迹保证或占卜预测。",
}
LEGACY_DEFAULT_AVATAR_URL = "/app/assets/avatar/default-guide-avatar.png"


def get_or_create_config(db: Session) -> DigitalHumanConfig:
    config = db.execute(select(DigitalHumanConfig).order_by(DigitalHumanConfig.id).limit(1)).scalar_one_or_none()
    if config is not None:
        if config.avatar_asset_url == LEGACY_DEFAULT_AVATAR_URL:
            config.avatar_asset_url = DEFAULT_CONFIG["avatar_asset_url"]
            config.outfit_theme = "asset-avatar"
            db.commit()
            db.refresh(config)
        return config

    config = DigitalHumanConfig(**DEFAULT_CONFIG)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def serialize_config(config: DigitalHumanConfig) -> dict:
    return {
        "name": config.name,
        "role_title": config.role_title,
        "scenic_area": config.scenic_area,
        "outfit_theme": config.outfit_theme,
        "voice_name": config.voice_name,
        "greeting": config.greeting,
        "avatar_asset_url": config.avatar_asset_url,
        "video_provider_status": config.video_provider_status,
        "fallback_message": config.fallback_message,
        "service_boundary": config.service_boundary,
    }


def update_config(db: Session, payload: dict) -> DigitalHumanConfig:
    config = get_or_create_config(db)
    for key in DEFAULT_CONFIG:
        if key in payload:
            setattr(config, key, payload[key])
    db.commit()
    db.refresh(config)
    return config
