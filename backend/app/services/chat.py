import time

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeChunk, QALog, ScenicSpot
from app.services.audio import generate_tts_audio
from app.services.digital_video import generate_digital_video
from app.services.digital_human import get_or_create_config
from app.utils import normalize_text, overlap_score, to_simplified_chinese


POSITIVE_HINTS = ("谢谢", "不错", "喜欢", "推荐", "怎么游", "历史", "文化", "亮点")
NEGATIVE_HINTS = ("不好", "失望", "投诉", "差", "不行", "麻烦", "卡", "崩溃")
ETIQUETTE_HINTS = ("礼仪", "礼貌", "注意", "禁忌", "规矩", "拍照", "殿堂", "寺院", "文明", "尊重", "秩序")


def infer_emotion(text: str) -> str:
    if any(token in text for token in NEGATIVE_HINTS):
        return "negative"
    if any(token in text for token in POSITIVE_HINTS):
        return "positive"
    return "neutral"


def retrieve_chunks(db: Session, question: str, top_k: int = 3) -> list[KnowledgeChunk]:
    chunks = db.execute(select(KnowledgeChunk)).scalars().all()
    ranked = sorted(chunks, key=lambda item: overlap_score(question, f"{item.title} {item.content}"), reverse=True)
    ranked = [item for item in ranked if overlap_score(question, f"{item.title} {item.content}") > 0]
    return ranked[:top_k]


def dedupe_chunks(chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
    seen: set[str] = set()
    result: list[KnowledgeChunk] = []
    for item in chunks:
        key = f"{item.title}|{item.content[:80]}"
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def build_references(db: Session, question: str, spot: ScenicSpot | None, top_k: int = 3) -> list[KnowledgeChunk]:
    ranked = retrieve_chunks(db, question, top_k=max(top_k * 2, 6))
    if spot is None:
        return dedupe_chunks(ranked)[:top_k]

    all_chunks = db.execute(select(KnowledgeChunk)).scalars().all()
    preferred = []
    for item in all_chunks:
        if item.title == spot.name or spot.name in item.content:
            preferred.append(item)
    preferred = sorted(
        preferred,
        key=lambda item: (
            item.title != spot.name,
            len(item.title),
        ),
    )
    combined = dedupe_chunks([*preferred, *ranked])
    return combined[:top_k]


def match_spot(db: Session, question: str) -> ScenicSpot | None:
    spots = db.execute(select(ScenicSpot)).scalars().all()
    for spot in spots:
        if spot.name in question:
            return spot
    return None


def format_spot_answer(spot: ScenicSpot) -> str:
    parts = [
        f"{spot.name}位于{spot.location}。",
        f"文化内涵方面，{spot.cultural_meaning}",
        f"详细介绍：{spot.description}",
        f"游玩亮点：{spot.highlights}",
    ]
    if spot.schedule:
        parts.append(f"开放或演出信息：{spot.schedule}")
    return "".join(parts)


def is_etiquette_question(question: str) -> bool:
    return any(token in question for token in ETIQUETTE_HINTS)


def format_etiquette_answer(scenic_area: str) -> str:
    area = scenic_area or "景区"
    return (
        f"参观{area}时建议注意四点文化礼仪："
        "第一，进入殿堂、展馆、演出区域前先看现场标识，拍照、录音和使用闪光灯以现场提示为准；"
        "第二，在寺院、佛教文化展示区和室内展陈空间保持安静，不攀爬、不触摸展品或供奉设施；"
        "第三，排队礼让，服装整洁，遇到法会、演出或人流管控时听从工作人员指引；"
        "第四，把祈愿和参观理解为文化体验，不宣称功德收益、神迹保证或占卜预测。"
    )


def call_llm_with_context(question: str, references: list[KnowledgeChunk]) -> str | None:
    if not (settings.model_api_key and settings.model_base_url and settings.model_name):
        return None

    context = "\n".join(f"[{item.title}] {item.content}" for item in references)
    system_prompt = (
        "你是景区导览AI数字人。请严格基于给定知识库回答，优先准确，语气自然。"
        "如果知识库没有直接信息，要明确说明没有查到，不要编造。"
        "不得承诺功德收益、神迹效果、占卜预测、现实保佑结果或医疗财运等确定性结果。"
    )
    user_prompt = f"知识库内容：\n{context}\n\n用户问题：{question}"

    payload = {
        "model": settings.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {settings.model_api_key}"}
    url = settings.model_base_url.rstrip("/") + "/chat/completions"

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        body = response.json()
        return body["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def fallback_answer(question: str, references: list[KnowledgeChunk], spot: ScenicSpot | None) -> str:
    if spot is not None:
        return format_spot_answer(spot)
    if references:
        lead = "根据当前景区知识库，"
        body = " ".join(item.content[:220] for item in references[:2])
        return lead + body
    return "当前知识库没有检索到足够信息，建议补充相关景区资料后再试。"


def answer_question(db: Session, question: str, user_id: str = "guest") -> dict:
    started = time.perf_counter()
    question = normalize_text(question)
    digital_human = get_or_create_config(db)
    emotion = infer_emotion(question)

    if is_etiquette_question(question):
        references: list[KnowledgeChunk] = []
        reference_titles = ["文化礼仪提示"]
        answer = format_etiquette_answer(digital_human.scenic_area)
    else:
        spot = match_spot(db, question)
        references = build_references(db, question, spot, top_k=3)
        answer = to_simplified_chinese(call_llm_with_context(question, references) or fallback_answer(question, references, spot))
        reference_titles = [to_simplified_chinese(item.title) for item in references]

    audio_url = generate_tts_audio(answer, digital_human.voice_name)
    digital_video = generate_digital_video(answer, audio_url)
    elapsed = round(time.perf_counter() - started, 3)

    log = QALog(
        user_id=user_id,
        question=question,
        answer=answer,
        source_titles="|".join(reference_titles),
        emotion=emotion,
        response_seconds=elapsed,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "log_id": log.id,
        "answer": answer,
        "audio_url": audio_url,
        "video_url": digital_video.video_url,
        "video_status": digital_video.video_status,
        "emotion": emotion,
        "reference": reference_titles,
        "response_seconds": elapsed,
    }
