from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DigitalHumanConfig


DEFAULT_CONFIG = {
    "name": "灵灵",
    "role_title": "景区 AI 导览员",
    "scenic_area": "灵山胜境",
    "outfit_theme": "ling-shan",
    "voice_name": "zh-CN-XiaoxiaoNeural",
    "greeting": "当前示范景区为灵山胜境，已接入对应知识库、路线推荐与语音播报能力。",
}


def get_or_create_config(db: Session) -> DigitalHumanConfig:
    config = db.execute(select(DigitalHumanConfig).order_by(DigitalHumanConfig.id).limit(1)).scalar_one_or_none()
    if config is not None:
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
    }


def update_config(db: Session, payload: dict) -> DigitalHumanConfig:
    config = get_or_create_config(db)
    for key in DEFAULT_CONFIG:
        if key in payload:
            setattr(config, key, payload[key])
    db.commit()
    db.refresh(config)
    return config
