import time

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeChunk, KnowledgeDocument, QALog, RoutePreset, ScenicSpot
from app.services.audio import generate_tts_audio
from app.services.digital_video import generate_digital_video
from app.services.digital_human import get_or_create_config
from app.services.rag import retrieve_rag_chunks
from app.utils import looks_garbled, normalize_text, overlap_score, to_simplified_chinese


POSITIVE_HINTS = ("谢谢", "不错", "喜欢", "推荐", "怎么游", "历史", "文化", "亮点")
NEGATIVE_HINTS = ("不好", "失望", "投诉", "差", "不行", "麻烦", "卡", "崩溃")
ETIQUETTE_HINTS = ("礼仪", "礼貌", "注意", "禁忌", "规矩", "拍照", "殿堂", "寺院", "文明", "尊重", "秩序")
GENERIC_RECOMMEND_HINTS = ("景点推荐", "推荐景点", "推荐一下", "有什么推荐", "必去", "必看", "打卡")
ROUTE_QUESTION_HINTS = ("半天", "全天", "一天", "路线", "线路", "怎么游", "怎么玩", "游览", "行程")
STRUCTURAL_NOISE_HINTS = ("字段规范", "字段说明", "数据集", "结构化数据", "景点ID", "具体位置", "景区名称、")
KNOWLEDGE_GAP_MARKER = "知识库待补充"
PARKING_HINTS = ("停车", "停车场", "泊车", "停车位")
TICKET_HINTS = ("门票", "票价", "购票", "预约", "入园")
TRAFFIC_HINTS = ("怎么去", "怎么到", "交通", "接驳", "摆渡车", "公交", "地铁", "自驾")
SERVICE_HINTS = ("洗手间", "厕所", "餐饮", "吃饭", "寄存", "轮椅", "充电", "母婴")
SUPPORTED_TRANSLATION_LANGUAGES = {"en": "English"}


def infer_emotion(text: str) -> str:
    if any(token in text for token in NEGATIVE_HINTS):
        return "negative"
    if any(token in text for token in POSITIVE_HINTS):
        return "positive"
    return "neutral"


def active_document_names(db: Session) -> set[str]:
    documents = db.execute(select(KnowledgeDocument).where(KnowledgeDocument.status == "active")).scalars().all()
    return {item.name for item in documents}


def current_spot_names(db: Session) -> list[str]:
    return [item.name for item in db.execute(select(ScenicSpot)).scalars().all()]


def is_structural_noise(chunk: KnowledgeChunk) -> bool:
    text = f"{chunk.document_name} {chunk.title} {chunk.content} {chunk.tags}"
    if looks_garbled(chunk.title):
        return True
    return any(token in text for token in STRUCTURAL_NOISE_HINTS)


def chunk_belongs_to_current_scenic(chunk: KnowledgeChunk, scenic_area: str, spot_names: list[str]) -> bool:
    text = f"{chunk.document_name} {chunk.title} {chunk.content} {chunk.tags}"
    if chunk.document_name == "sample_scenic_spots":
        return True
    if scenic_area and scenic_area in text:
        return True
    return any(name in text for name in spot_names)


def retrieve_chunks(
    db: Session,
    question: str,
    top_k: int = 3,
    scenic_area: str = "",
    spot_names: list[str] | None = None,
) -> list[KnowledgeChunk]:
    active_docs = active_document_names(db)
    chunks = db.execute(select(KnowledgeChunk)).scalars().all()
    chunks = [
        item
        for item in chunks
        if (not active_docs or item.document_name in active_docs) and not is_structural_noise(item)
    ]

    scoped_spots = spot_names or []
    if scoped_spots or scenic_area:
        scoped = [item for item in chunks if chunk_belongs_to_current_scenic(item, scenic_area, scoped_spots)]
        chunks = scoped if scoped or scoped_spots else chunks

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


def build_references(
    db: Session,
    question: str,
    spot: ScenicSpot | None,
    scenic_area: str,
    top_k: int = 3,
) -> list[KnowledgeChunk]:
    spot_names = current_spot_names(db)
    ranked = retrieve_chunks(db, question, top_k=max(top_k * 2, 6), scenic_area=scenic_area, spot_names=spot_names)
    if spot is None:
        return dedupe_chunks(ranked)[:top_k]

    all_chunks = db.execute(select(KnowledgeChunk)).scalars().all()
    preferred = []
    for item in all_chunks:
        if is_structural_noise(item) or not chunk_belongs_to_current_scenic(item, scenic_area, spot_names):
            continue
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


def is_generic_recommendation_question(question: str) -> bool:
    if any(token in question for token in GENERIC_RECOMMEND_HINTS):
        return True
    return "推荐" in question and ("景点" in question or "游览" in question or "怎么玩" in question)


def build_spot_recommendation(db: Session, scenic_area: str) -> tuple[str, list[str]]:
    spots = db.execute(select(ScenicSpot).order_by(ScenicSpot.id)).scalars().all()
    if not spots:
        return f"抱歉，我暂时还没有整理好{scenic_area or '当前景区'}的推荐景点信息，你可以先咨询游客中心或换个问题试试。", []

    spot_map = {item.name: item for item in spots}
    preferred_names = [name for name in ("九龙灌浴", "灵山大佛", "灵山梵宫", "祥符禅寺", "五印坛城") if name in spot_map]
    if len(preferred_names) < 3:
        preferred_names = [item.name for item in spots[:5]]

    route = db.execute(select(RoutePreset).where(RoutePreset.name.like("%半日%")).limit(1)).scalar_one_or_none()
    route_text = ""
    if route:
        route_spots = " → ".join([item for item in route.spots.split("|") if item])
        route_text = f"如果时间有限，可以按“{route_spots}”的顺序走，{route.reason}"

    highlights = []
    for name in preferred_names[:5]:
        spot = spot_map[name]
        highlights.append(f"{spot.name}适合{spot.highlights.rstrip('。')}。")

    answer = (
        f"如果你想在{scenic_area or '当前景区'}做景点推荐，我建议优先看"
        f"{'、'.join(preferred_names[:3])}。"
        f"{''.join(highlights[:3])}"
        f"{route_text}"
    )
    return answer, preferred_names[:5]


def is_route_question(question: str) -> bool:
    return any(token in question for token in ROUTE_QUESTION_HINTS)


def build_route_answer(db: Session, question: str, scenic_area: str) -> tuple[str, list[str]]:
    duration = "全天" if any(token in question for token in ("全天", "一天", "深度")) else "半天"
    route = db.execute(
        select(RoutePreset)
        .where(RoutePreset.duration == duration)
        .order_by(RoutePreset.id)
        .limit(1)
    ).scalar_one_or_none()
    if route is None:
        route = db.execute(select(RoutePreset).order_by(RoutePreset.id).limit(1)).scalar_one_or_none()
    if route is None:
        return build_spot_recommendation(db, scenic_area)

    spots = [item for item in route.spots.split("|") if item]
    answer = (
        f"如果你计划在{scenic_area or '当前景区'}游览{duration}，建议走“{' → '.join(spots)}”。"
        f"这条路线叫“{route.name}”，{route.reason}"
        "建议把演出时间和现场排队情况留出弹性，先看核心景点，再根据体力补充周边点位。"
    )
    return answer, spots


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


def model_service_configured() -> bool:
    return bool(settings.model_api_key and settings.model_base_url and settings.model_name)


def call_model_messages(messages: list[dict], temperature: float = 0.2) -> str | None:
    if not model_service_configured():
        return None

    payload = {
        "model": settings.model_name,
        "messages": messages,
        "temperature": temperature,
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


def call_llm_with_context(question: str, references: list[KnowledgeChunk], scenic_area: str) -> str | None:
    if not model_service_configured():
        return None

    context = "\n".join(f"[{item.title}] {item.content}" for item in references)
    system_prompt = (
        f"你是{scenic_area or '当前景区'}的景区导览AI数字人。请严格基于给定知识库回答，优先准确，语气自然。"
        "只推荐当前景区内的景点，不要把其他景区、其他城市或原始数据字段当作导览答案。"
        "不要输出“字段规范、数据集、景点ID、具体位置”等数据库说明文字。"
        "如果知识库没有直接信息，要明确说明没有查到，不要编造。"
        "不得承诺功德收益、神迹效果、占卜预测、现实保佑结果或医疗财运等确定性结果。"
    )
    user_prompt = f"知识库内容：\n{context}\n\n用户问题：{question}"

    return call_model_messages(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )


def translate_answer_text(text: str, target_language: str = "en") -> str | None:
    language_name = SUPPORTED_TRANSLATION_LANGUAGES.get(target_language.lower())
    if not language_name or not model_service_configured():
        return None

    system_prompt = (
        "You are a translation assistant for a scenic-guide digital human. "
        "Translate Simplified Chinese answers into natural, visitor-friendly English. "
        "Do not add facts, do not omit concrete times or locations, and keep scenic spot names consistent. "
        "If there is no known official English name, use readable pinyin with capitalization. "
        "Output translation only."
    )
    user_prompt = f"Target language: {language_name}\nSource text:\n{text}"
    return call_model_messages(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )


def fallback_answer(question: str, references: list[KnowledgeChunk], spot: ScenicSpot | None) -> str:
    if spot is not None:
        return format_spot_answer(spot)
    if references:
        lead = "根据当前景区知识库，"
        body = " ".join(clean_chunk_content(item.content)[:220] for item in references[:2])
        return lead + body
    if any(token in question for token in PARKING_HINTS):
        return "抱歉，我暂时没有查到停车相关信息，建议查看景区停车指引牌，或咨询游客中心、现场服务台。"
    if any(token in question for token in TICKET_HINTS):
        return "抱歉，我暂时没有查到准确的票务信息，建议以景区官方购票页、游客中心或现场公告为准。"
    if any(token in question for token in TRAFFIC_HINTS):
        return "抱歉，我暂时没有查到准确的交通到达信息，建议查看景区官方出行指引，或咨询游客中心。"
    if any(token in question for token in SERVICE_HINTS):
        return "抱歉，我暂时没有查到这项配套服务信息，建议留意景区导览图，或咨询游客中心和现场工作人员。"
    return "抱歉，我暂时没有查到这项信息。你可以换个问法试试，或咨询游客中心和现场工作人员。"


def build_gap_marker(question: str) -> str:
    if any(token in question for token in PARKING_HINTS):
        return f"{KNOWLEDGE_GAP_MARKER}:停车服务"
    if any(token in question for token in TICKET_HINTS):
        return f"{KNOWLEDGE_GAP_MARKER}:票务信息"
    if any(token in question for token in TRAFFIC_HINTS):
        return f"{KNOWLEDGE_GAP_MARKER}:交通指引"
    if any(token in question for token in SERVICE_HINTS):
        return f"{KNOWLEDGE_GAP_MARKER}:配套服务"
    return KNOWLEDGE_GAP_MARKER


def clean_chunk_content(content: str) -> str:
    text = normalize_text(content)
    for prefix in ("景点名称：", "景点类型：", "介绍内容：", "详细介绍："):
        text = text.replace(prefix, "")
    return text


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
        if spot is None and is_route_question(question):
            answer, reference_titles = build_route_answer(db, question, digital_human.scenic_area)
            references = []
        elif spot is None and is_generic_recommendation_question(question):
            answer, reference_titles = build_spot_recommendation(db, digital_human.scenic_area)
            references = []
        else:
            references = []
            if settings.enable_rag:
                references = retrieve_rag_chunks(db, question, digital_human.scenic_area, top_k=settings.rag_top_k)
            if not references:
                references = build_references(db, question, spot, digital_human.scenic_area, top_k=3)
            if spot is not None:
                references = dedupe_chunks(
                    build_references(db, question, spot, digital_human.scenic_area, top_k=3) + references
                )[: settings.rag_top_k]
            answer = to_simplified_chinese(
                call_llm_with_context(question, references, digital_human.scenic_area)
                or fallback_answer(question, references, spot)
            )
            reference_titles = [to_simplified_chinese(item.title) for item in references]
            if not reference_titles and spot is None:
                reference_titles = [build_gap_marker(question)]

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
