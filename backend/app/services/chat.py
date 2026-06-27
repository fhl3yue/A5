import re
import time

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeChunk, KnowledgeDocument, QALog, RoutePreset, ScenicSpot
from app.services.audio import generate_tts_audio
from app.services.audio_tasks import queue_answer_audio
from app.services.digital_video import generate_digital_video
from app.services.digital_human import get_or_create_config
from app.services.rag import retrieve_rag_chunks
from app.services.routes import recommend_route
from app.utils import looks_garbled, normalize_text, overlap_score, to_simplified_chinese


POSITIVE_HINTS = ("谢谢", "不错", "喜欢", "推荐", "怎么游", "历史", "文化", "亮点")
NEGATIVE_HINTS = ("不好", "失望", "投诉", "差", "不行", "麻烦", "卡", "崩溃")
ETIQUETTE_HINTS = ("礼仪", "礼貌", "注意", "禁忌", "规矩", "拍照", "殿堂", "寺院", "文明", "尊重", "秩序")
GENERIC_RECOMMEND_HINTS = ("景点推荐", "推荐景点", "推荐一下", "有什么推荐", "必去", "必看", "打卡")
ROUTE_QUESTION_HINTS = ("半天", "全天", "一天", "路线", "线路", "怎么游", "怎么玩", "游览", "行程", "轻松", "不累", "逛一下", "逛逛")
STRUCTURAL_NOISE_HINTS = ("字段规范", "字段说明", "数据集", "结构化数据", "景点ID", "具体位置", "景区名称、")
KNOWLEDGE_GAP_MARKER = "知识库待补充"
OUT_OF_SCOPE_MARKER = "超出当前景区知识库范围"
PARKING_HINTS = ("停车", "停车场", "泊车", "停车位")
TICKET_HINTS = ("门票", "票价", "购票", "预约", "入园")
TRAFFIC_HINTS = ("怎么去", "怎么到", "交通", "接驳", "摆渡车", "公交", "地铁", "自驾")
SERVICE_HINTS = ("洗手间", "厕所", "餐饮", "吃饭", "寄存", "轮椅", "充电", "母婴")
LOCATION_QUESTION_HINTS = ("在哪", "哪里", "位置", "位于", "坐落", "地址", "省市", "哪个市", "哪个省")
LOCATION_FINE_GRAIN_HINTS = ("具体地点", "具体地址", "详细地址", "哪里", "哪儿", "无锡哪里", "景区里面哪里")
PROVINCE_CITY_HINTS = ("哪个省", "哪个市", "省市", "在哪个市", "在哪个省")
SUPPORTED_TRANSLATION_LANGUAGES = {"en": "English"}
SCHEDULE_HINTS = ("几点", "时间", "开始", "表演", "演出", "开放", "场次", "何时", "什么时候")
CULTURE_HINTS = ("文化", "含义", "寓意", "象征", "意义", "由来", "内涵", "为什么")
HIGHLIGHT_HINTS = ("亮点", "特色", "看点", "值得看", "必看什么", "推荐理由")
OVERVIEW_HINTS = ("介绍", "讲讲", "是什么", "详情", "了解一下", "简介")
SERVICE_INTENTS = {"parking", "ticket", "traffic", "service"}
SPECIFIC_LOCATION_HINTS = ("滨湖区", "马山", "太湖", "度假区", "菩提大道", "入口处", "北端", "中轴线", "核心区域")
SCHEDULE_ANSWER_HINTS = ("开放", "演出", "表演", "场次", "全天", "公告为准")
CULTURE_ANSWER_HINTS = ("文化", "寓意", "象征", "内涵", "体现", "由来", "意味")
PROVINCE_CITY_PATTERN = re.compile(
    r"((?:河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|台湾)省[\u4e00-\u9fff]{2,6}市|(?:北京|上海|天津|重庆)市)"
)
TIME_PATTERN = re.compile(r"(?:[01]?\d|2[0-3])[:：][0-5]\d")
BROKEN_SENTENCE_TAIL_PATTERN = re.compile(r"[，,、：:](?:地|位|坐|在|处|位于|坐落|地处|介绍|详细|文化|开放|演出|游玩|亮点)\s*[。；;]?$")
FIELD_PREFIX_PATTERN = re.compile(
    r"^(?:景点名称|景点类型|位置|地址|景区名称|介绍内容|详细介绍|文化内涵方面|文化内涵|游玩亮点|开放或演出信息|开放信息|演出信息)[:：]\s*"
)
WEATHER_HINTS = ("天气", "气温", "温度", "多少度", "几度", "下雨", "降雨", "降雪", "空气质量", "aqi", "穿衣", "紫外线", "台风", "雷阵雨", "风力", "风大")
GENERAL_WEB_HINTS = ("新闻", "热搜", "股票", "股价", "基金", "汇率", "彩票", "电影票", "外卖", "菜谱", "红烧肉", "写代码", "数学题")
EXTERNAL_PLACE_HINTS = (
    "徐州", "南京", "苏州", "常州", "扬州", "镇江", "南通", "连云港", "盐城", "淮安", "泰州", "宿迁",
    "北京", "上海", "杭州", "宁波", "合肥", "黄山", "武汉", "长沙", "成都", "重庆", "广州", "深圳", "西安",
    "故宫", "长城", "颐和园", "外滩", "西湖", "迪士尼", "泰山", "华山", "兵马俑", "高家庄", "崇明",
)
CURRENT_SCENIC_ALIASES = ("灵山", "灵山胜境", "灵山大佛", "九龙灌浴", "灵山梵宫", "祥符禅寺", "五印坛城", "拈花湾", "无锡", "马山", "太湖")
SCENIC_DOMAIN_HINTS = (
    "景区", "景点", "导览", "讲解", "游客", "游玩", "游览", "参观", "路线", "线路", "行程",
    "表演", "演出", "开放", "场次", "门票", "票价", "停车", "交通", "厕所", "洗手间", "餐饮",
    "文化", "历史", "含义", "寓意", "象征", "特色", "看点", "亮点", "拍照", "礼仪", "祈福",
)
BASIC_CHAT_HINTS = ("你好", "您好", "嗨", "hello", "hi", "你是谁", "你叫什么", "谢谢", "感谢")


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


def current_scope_terms(db: Session, scenic_area: str) -> set[str]:
    terms = {term for term in CURRENT_SCENIC_ALIASES if term}
    if scenic_area:
        terms.add(scenic_area)
    for spot in db.execute(select(ScenicSpot)).scalars().all():
        if spot.name:
            terms.add(spot.name)
        if spot.location:
            for token in SPECIFIC_LOCATION_HINTS:
                if token in spot.location:
                    terms.add(token)
    return terms


def has_current_scope_signal(question: str, scope_terms: set[str]) -> bool:
    return any(term and term in question for term in scope_terms)


def is_basic_chat_question(question: str) -> bool:
    normalized = question.strip().lower()
    return bool(normalized) and any(token in normalized for token in BASIC_CHAT_HINTS)


def is_realtime_external_question(question: str, scope_terms: set[str]) -> bool:
    if has_current_scope_signal(question, scope_terms):
        return False
    return any(token in question for token in WEATHER_HINTS)


def is_explicit_external_place_question(question: str, scope_terms: set[str]) -> bool:
    if has_current_scope_signal(question, scope_terms):
        return False
    return any(token in question for token in EXTERNAL_PLACE_HINTS)


def is_supported_scenic_domain_question(question: str, scope_terms: set[str]) -> bool:
    if has_current_scope_signal(question, scope_terms):
        return True
    if is_basic_chat_question(question):
        return True
    if any(token in question for token in GENERAL_WEB_HINTS):
        return False
    if any(token in question for token in WEATHER_HINTS):
        return False
    if any(token in question for token in EXTERNAL_PLACE_HINTS):
        return False
    return any(token in question for token in SCENIC_DOMAIN_HINTS)


def build_out_of_scope_answer(question: str, scenic_area: str, scope_terms: set[str]) -> str | None:
    if is_realtime_external_question(question, scope_terms):
        return (
            f"抱歉，我当前只接入了{scenic_area or '当前景区'}本地知识库，"
            "没有启用联网天气查询，所以无法准确回答这个城市的实时天气。"
        )
    if is_explicit_external_place_question(question, scope_terms):
        return (
            f"抱歉，我当前只接入了{scenic_area or '当前景区'}本地知识库，"
            "没有查到你提到的外部城市或景区资料。"
        )
    if not is_supported_scenic_domain_question(question, scope_terms):
        return (
            f"抱歉，我当前主要负责{scenic_area or '当前景区'}导览讲解。"
            "这个问题没有在当前景区知识库中查到可靠资料。"
        )
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


def build_route_answer(db: Session, question: str, scenic_area: str, user_id: str = "guest") -> tuple[str, list[str]]:
    duration = "全天" if any(token in question for token in ("全天", "一天", "深度")) else "半天"
    route_data = recommend_route(db, question, duration, user_id=user_id)
    spots = route_data.get("route_spots", [])
    if not spots:
        return build_spot_recommendation(db, scenic_area)

    spots_text = " → ".join(spots)
    answer = (
        f"{duration}游览建议走：{spots_text}。"
        "先看核心景点，演出和排队时间留出弹性；"
        "如果时间和体力还有余量，再补充周边点位。"
    )
    return answer, spots


def is_etiquette_question(question: str) -> bool:
    if any(token in question for token in ("礼仪", "礼貌", "注意", "禁忌", "规矩", "殿堂", "寺院", "文明", "尊重", "秩序")):
        return True
    if "拍照" in question:
        return any(token in question for token in ("能不能", "可以吗", "允许", "禁止", "闪光灯", "录音"))
    return False


def is_location_question(question: str) -> bool:
    return any(token in question for token in LOCATION_QUESTION_HINTS)


def wants_province_city(question: str) -> bool:
    return any(token in question for token in PROVINCE_CITY_HINTS)


def wants_fine_grain_location(question: str) -> bool:
    if wants_province_city(question):
        return False
    return any(token in question for token in LOCATION_FINE_GRAIN_HINTS)


def extract_concise_location(sentence: str, scenic_area: str) -> str | None:
    cleaned = re.sub(r"^(位置|地址|景区名称|介绍内容|详细介绍)[:：]", "", sentence).strip()
    match = re.search(
        r"((?:江苏省)?无锡市[^，。；;]{0,36}(?:马山镇|度假区|景区|大道|区域|位置|地带|入口处|北端|核心位置|中轴线核心位置))",
        cleaned,
    )
    if not match:
        return None
    location = match.group(1).rstrip("，,。；; ")
    subject = scenic_area or "该景区"
    return f"{subject}位于{location}。"


def extract_location_answer(
    question: str,
    references: list[KnowledgeChunk],
    scenic_area: str,
    spot: ScenicSpot | None,
) -> str | None:
    if not is_location_question(question):
        return None

    province_city_mode = wants_province_city(question)
    fine_grain_mode = wants_fine_grain_location(question)
    if spot is not None and spot.location:
        if province_city_mode:
            province_city = PROVINCE_CITY_PATTERN.search(spot.location)
            if province_city:
                return f"{spot.name}位于{province_city.group(1)}。"
        elif fine_grain_mode:
            if has_specific_location_detail(spot.location):
                return f"{spot.name}位于{spot.location}。"
        else:
            return f"{spot.name}位于{spot.location}。"

    target = scenic_area if scenic_area and scenic_area in question else ""
    candidates: list[str] = []
    for chunk in references:
        # Titles imported from Word can be truncated; prefer full content for exact location extraction.
        text = normalize_text(chunk.content or chunk.title)
        candidates.extend(part.strip() for part in re.split(r"[。；;\n]", text) if part.strip())

    location_words = ("位于", "坐落", "地处", "地址", "省", "市")
    for sentence in candidates:
        if target and target not in sentence:
            continue
        if not any(word in sentence for word in location_words):
            continue
        province_city = re.search(
            r"((?:河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|台湾)省[\u4e00-\u9fff]{2,6}市|(?:北京|上海|天津|重庆)市)",
            sentence,
        )
        if province_city_mode and province_city:
            return f"{scenic_area or target or '该景区'}位于{province_city.group(1)}。"
        concise_location = extract_concise_location(sentence, scenic_area or target)
        if concise_location and (not fine_grain_mode or has_specific_location_detail(concise_location)):
            return concise_location
        if any(word in sentence for word in ("位于", "坐落", "地处")):
            cleaned = re.sub(r"^(位置|地址|景区名称|介绍内容|详细介绍)[:：]", "", sentence).strip()
            if cleaned and len(cleaned) <= 90:
                if fine_grain_mode and province_city and any(token in cleaned for token in ("太湖", "马山", "北端", "入口", "核心区域", "中轴线")):
                    specific_match = re.search(r"(无锡市[\u4e00-\u9fff]{2,20}(?:度假区|景区|大道|区域|位置|地带|镇))", cleaned)
                    if specific_match:
                        return f"{scenic_area or '该景区'}位于{specific_match.group(1)}。"
                    return cleaned if cleaned.endswith("。") else f"{cleaned}。"
                if fine_grain_mode:
                    continue
                if scenic_area and not cleaned.startswith(scenic_area):
                    return f"{scenic_area}{cleaned}"
                return cleaned if cleaned.endswith("。") else f"{cleaned}。"
    if fine_grain_mode and province_city_mode is False:
        for sentence in candidates:
            if target and target not in sentence:
                continue
            if any(token in sentence for token in ("太湖", "马山镇", "菩提大道", "中轴线", "核心区域", "入口处")):
                cleaned = re.sub(r"^(位置|地址|景区名称|介绍内容|详细介绍)[:：]", "", sentence).strip()
                return cleaned if cleaned.endswith("。") else f"{cleaned}。"
    return None


def classify_question_intent(question: str) -> str:
    if any(token in question for token in PARKING_HINTS):
        return "parking"
    if any(token in question for token in TICKET_HINTS):
        return "ticket"
    if any(token in question for token in TRAFFIC_HINTS):
        return "traffic"
    if any(token in question for token in SERVICE_HINTS):
        return "service"
    if is_location_question(question):
        if wants_province_city(question):
            return "location_province_city"
        if wants_fine_grain_location(question):
            return "location_fine_grain"
        return "location_general"
    if any(token in question for token in SCHEDULE_HINTS):
        return "schedule"
    if any(token in question for token in CULTURE_HINTS):
        return "culture"
    if any(token in question for token in HIGHLIGHT_HINTS):
        return "highlight"
    if any(token in question for token in OVERVIEW_HINTS):
        return "overview"
    return "generic"


def split_reference_sentences(references: list[KnowledgeChunk]) -> list[str]:
    sentences: list[str] = []
    for chunk in references:
        text = normalize_text(f"{chunk.title}。{chunk.content}")
        sentences.extend(part.strip() for part in re.split(r"[。；;\n]", text) if part.strip())
    return sentences


def clean_answer_fragment(text: str) -> str:
    cleaned = normalize_text(text)
    cleaned = FIELD_PREFIX_PATTERN.sub("", cleaned).strip()
    return cleaned.rstrip("。；; ")


def ensure_sentence(text: str) -> str:
    cleaned = normalize_text(text).strip()
    if not cleaned:
        return ""
    return cleaned if cleaned.endswith("。") else f"{cleaned}。"


def clean_final_answer(text: str) -> str:
    cleaned = normalize_text(text).strip()
    if not cleaned:
        return ""
    cleaned = FIELD_PREFIX_PATTERN.sub("", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"(。){2,}", "。", cleaned)
    cleaned = BROKEN_SENTENCE_TAIL_PATTERN.sub("", cleaned).rstrip("，,、：:；; ")
    return ensure_sentence(cleaned)


def compose_named_answer(subject: str, prefix: str, body: str) -> str:
    cleaned = clean_answer_fragment(body)
    if not cleaned:
        return ""
    if subject and cleaned.startswith(subject):
        return ensure_sentence(cleaned)
    return f"{subject}{prefix}{cleaned}。"


def best_matching_sentence(
    question: str,
    references: list[KnowledgeChunk],
    *,
    match_tokens: tuple[str, ...] = (),
    pattern: re.Pattern[str] | None = None,
    spot: ScenicSpot | None = None,
    scenic_area: str = "",
) -> str | None:
    scored: list[tuple[int, int, str]] = []
    for sentence in split_reference_sentences(references):
        if match_tokens and not any(token in sentence for token in match_tokens):
            if pattern is None or not pattern.search(sentence):
                continue
        elif pattern is not None and not pattern.search(sentence) and not any(token in sentence for token in match_tokens):
            continue
        if any(token in sentence for token in STRUCTURAL_NOISE_HINTS):
            continue
        score = overlap_score(question, sentence)
        if spot is not None and spot.name in sentence:
            score += 3
        elif scenic_area and scenic_area in sentence:
            score += 1
        scored.append((score, -len(sentence), sentence))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][2]


def build_gap_answer(question: str) -> str | None:
    if any(token in question for token in PARKING_HINTS):
        return "抱歉，我暂时没有查到停车相关信息，建议查看景区停车指引牌，或咨询游客中心、现场服务台。"
    if any(token in question for token in TICKET_HINTS):
        return "抱歉，我暂时没有查到准确的票务信息，建议以景区官方购票页、游客中心或现场公告为准。"
    if any(token in question for token in TRAFFIC_HINTS):
        return "抱歉，我暂时没有查到准确的交通到达信息，建议查看景区官方出行指引，或咨询游客中心。"
    if any(token in question for token in SERVICE_HINTS):
        return "抱歉，我暂时没有查到这项配套服务信息，建议留意景区导览图，或咨询游客中心和现场工作人员。"
    return None


def extract_schedule_answer(
    question: str,
    references: list[KnowledgeChunk],
    scenic_area: str,
    spot: ScenicSpot | None,
) -> str | None:
    if spot is not None and spot.schedule:
        return compose_named_answer(spot.name, "的开放或演出时间是：", spot.schedule)
    sentence = best_matching_sentence(
        question,
        references,
        match_tokens=SCHEDULE_ANSWER_HINTS,
        pattern=TIME_PATTERN,
        spot=spot,
        scenic_area=scenic_area,
    )
    if not sentence:
        return None
    if spot is not None:
        return compose_named_answer(spot.name, "的开放或演出时间是：", sentence)
    return ensure_sentence(sentence)


def extract_culture_answer(
    question: str,
    references: list[KnowledgeChunk],
    scenic_area: str,
    spot: ScenicSpot | None,
) -> str | None:
    if spot is not None and spot.cultural_meaning:
        return compose_named_answer(spot.name, "的文化含义是：", spot.cultural_meaning)
    sentence = best_matching_sentence(
        question,
        references,
        match_tokens=CULTURE_ANSWER_HINTS,
        spot=spot,
        scenic_area=scenic_area,
    )
    if not sentence:
        return None
    if spot is not None:
        return compose_named_answer(spot.name, "的文化含义是：", sentence)
    return ensure_sentence(sentence)


def extract_highlight_answer(
    question: str,
    references: list[KnowledgeChunk],
    scenic_area: str,
    spot: ScenicSpot | None,
) -> str | None:
    if spot is not None and spot.highlights:
        return compose_named_answer(spot.name, "的参观亮点是：", spot.highlights)
    sentence = best_matching_sentence(question, references, match_tokens=HIGHLIGHT_HINTS, spot=spot, scenic_area=scenic_area)
    if not sentence:
        return None
    if spot is not None:
        return compose_named_answer(spot.name, "的参观亮点是：", sentence)
    return ensure_sentence(sentence)


def extract_overview_answer(
    question: str,
    references: list[KnowledgeChunk],
    scenic_area: str,
    spot: ScenicSpot | None,
) -> str | None:
    if spot is not None:
        parts = [
            compose_named_answer(spot.name, "：", spot.description),
            compose_named_answer(spot.name, "的参观亮点是：", spot.highlights),
        ]
        return "".join(part for part in parts if part)
    sentence = best_matching_sentence(question, references, spot=spot, scenic_area=scenic_area)
    if sentence:
        return ensure_sentence(sentence)
    if references:
        return "根据当前景区知识库，" + " ".join(clean_chunk_content(item.content)[:120] for item in references[:2])
    return None


def extract_service_answer(question: str, references: list[KnowledgeChunk], scenic_area: str, spot: ScenicSpot | None) -> str | None:
    intent = classify_question_intent(question)
    token_map = {
        "parking": PARKING_HINTS,
        "ticket": TICKET_HINTS,
        "traffic": TRAFFIC_HINTS,
        "service": SERVICE_HINTS,
    }
    sentence = best_matching_sentence(
        question,
        references,
        match_tokens=token_map.get(intent, ()),
        spot=spot,
        scenic_area=scenic_area,
    )
    if sentence:
        return ensure_sentence(sentence)
    return build_gap_answer(question)


def extract_targeted_local_answer(
    question: str,
    references: list[KnowledgeChunk],
    scenic_area: str,
    spot: ScenicSpot | None,
) -> str | None:
    intent = classify_question_intent(question)
    if intent.startswith("location_"):
        return extract_location_answer(question, references, scenic_area, spot)
    if intent == "schedule":
        return extract_schedule_answer(question, references, scenic_area, spot)
    if intent == "culture":
        return extract_culture_answer(question, references, scenic_area, spot)
    if intent == "highlight":
        return extract_highlight_answer(question, references, scenic_area, spot)
    if intent == "overview":
        return extract_overview_answer(question, references, scenic_area, spot)
    if intent in SERVICE_INTENTS:
        return extract_service_answer(question, references, scenic_area, spot)
    return None


def is_spot_bundle_answer(answer: str) -> bool:
    return all(marker in answer for marker in ("文化内涵方面", "详细介绍：", "游玩亮点："))


def has_specific_location_detail(text: str) -> bool:
    return any(token in text for token in SPECIFIC_LOCATION_HINTS)


def validate_local_answer(
    question: str,
    answer: str,
    references: list[KnowledgeChunk],
    spot: ScenicSpot | None,
) -> tuple[bool, str]:
    normalized_answer = normalize_text(answer).strip()
    if not normalized_answer:
        return False, "empty"

    intent = classify_question_intent(question)
    if normalized_answer.startswith("根据当前景区知识库，") and intent not in {"generic", "overview"}:
        return False, "too_generic"
    if spot is not None and intent in {"schedule", "culture", "highlight", "overview"} and is_spot_bundle_answer(normalized_answer):
        return False, "bundle_too_broad"

    if intent == "location_province_city":
        return bool(PROVINCE_CITY_PATTERN.search(normalized_answer)), "province_city"
    if intent == "location_fine_grain":
        return has_specific_location_detail(normalized_answer), "fine_grain_location"
    if intent == "location_general":
        return any(token in normalized_answer for token in ("位于", "坐落", "地处", "地址")), "location"
    if intent == "schedule":
        return bool(TIME_PATTERN.search(normalized_answer) or any(token in normalized_answer for token in SCHEDULE_ANSWER_HINTS)), "schedule"
    if intent == "culture":
        return any(token in normalized_answer for token in CULTURE_ANSWER_HINTS), "culture"
    if intent == "highlight":
        return any(token in normalized_answer for token in ("亮点", "适合", "推荐", "值得看")), "highlight"
    if intent == "overview":
        if spot is not None and spot.name not in normalized_answer:
            return False, "missing_spot_name"
        return len(normalized_answer) >= 18, "overview"
    if intent in SERVICE_INTENTS:
        service_token_map = {
            "parking": ("停车", "停车场", "泊车"),
            "ticket": ("门票", "票务", "购票", "预约"),
            "traffic": ("交通", "到达", "接驳", "公交", "地铁", "自驾"),
            "service": ("服务", "洗手间", "厕所", "餐饮", "寄存", "轮椅", "充电", "母婴"),
        }
        return any(token in normalized_answer for token in service_token_map[intent]) or "暂时没有查到" in normalized_answer, intent
    if spot is not None or references:
        return True, "supported"
    return KNOWLEDGE_GAP_MARKER not in normalized_answer and "暂时没有查到" not in normalized_answer, "generic"


def review_local_answer(
    question: str,
    answer: str,
    references: list[KnowledgeChunk],
    scenic_area: str,
    spot: ScenicSpot | None,
) -> tuple[str, bool, bool]:
    valid, _ = validate_local_answer(question, answer, references, spot)
    if valid:
        return answer, False, True

    repaired = extract_targeted_local_answer(question, references, scenic_area, spot)
    if repaired:
        repaired = ensure_sentence(repaired)
        repaired_valid, _ = validate_local_answer(question, repaired, references, spot)
        if repaired_valid:
            return repaired, True, True
    return answer, False, False


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
    return bool(main_model_api_key() and main_model_base_url() and main_model_name())


def main_model_api_key() -> str:
    return settings.model_api_key or settings.english_model_api_key


def main_model_base_url() -> str:
    return settings.model_base_url or settings.english_model_base_url


def main_model_name() -> str:
    return settings.model_name or settings.english_model_name


def english_service_configured() -> bool:
    return bool(
        settings.enable_english_translation
        and settings.english_model_api_key
        and settings.english_model_base_url
        and settings.english_model_name
    )


def call_openai_compatible_messages(
    *,
    api_key: str,
    base_url: str,
    model_name: str,
    messages: list[dict],
    temperature: float = 0.2,
    timeout_seconds: float = 30.0,
) -> str | None:
    if not api_key or not base_url or not model_name:
        return None

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    url = base_url.rstrip("/") + "/chat/completions"

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        body = response.json()
        return body["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def call_model_messages(
    messages: list[dict],
    temperature: float = 0.2,
    timeout_seconds: float | None = None,
) -> str | None:
    if not model_service_configured():
        return None

    return call_openai_compatible_messages(
        api_key=main_model_api_key(),
        base_url=main_model_base_url(),
        model_name=main_model_name(),
        messages=messages,
        temperature=temperature,
        timeout_seconds=timeout_seconds or settings.model_timeout_seconds,
    )


def call_english_model_messages(messages: list[dict], temperature: float = 0.1) -> str | None:
    if not english_service_configured():
        return None

    return call_openai_compatible_messages(
        api_key=settings.english_model_api_key,
        base_url=settings.english_model_base_url,
        model_name=settings.english_model_name,
        messages=messages,
        temperature=temperature,
        timeout_seconds=30.0,
    )


def call_llm_with_context(
    question: str,
    references: list[KnowledgeChunk],
    scenic_area: str,
    timeout_seconds: float | None = None,
) -> str | None:
    if not model_service_configured() or not references:
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
        timeout_seconds=timeout_seconds,
    )


def translate_answer_text(text: str, target_language: str = "en") -> str | None:
    language_name = SUPPORTED_TRANSLATION_LANGUAGES.get(target_language.lower())
    if not language_name or not english_service_configured():
        return None

    system_prompt = (
        "You are a translation assistant for a scenic-guide digital human. "
        "Translate Simplified Chinese answers into natural, visitor-friendly English. "
        "Do not add facts, do not omit concrete times or locations, and keep scenic spot names consistent. "
        "If there is no known official English name, use readable pinyin with capitalization. "
        "Output translation only."
    )
    user_prompt = f"Target language: {language_name}\nSource text:\n{text}"
    return call_english_model_messages(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )


def build_translation_result(text: str, target_language: str = "en") -> dict | None:
    translation = translate_answer_text(text, target_language)
    if not translation:
        return None

    audio_url = generate_tts_audio(
        translation,
        settings.english_tts_voice,
        enabled=settings.enable_english_tts,
    )
    return {
        "translation": translation,
        "audio_url": audio_url,
    }


def fallback_answer(question: str, references: list[KnowledgeChunk], spot: ScenicSpot | None) -> str:
    gap_answer = build_gap_answer(question)
    if spot is not None:
        return format_spot_answer(spot)
    if references and classify_question_intent(question) not in SERVICE_INTENTS:
        lead = "根据当前景区知识库，"
        body = " ".join(clean_chunk_content(item.content)[:220] for item in references[:2])
        return lead + body
    if gap_answer:
        return gap_answer
    return "抱歉，我暂时没有查到这项信息。你可以换个问法试试，或咨询游客中心和现场工作人员。"


def has_reliable_local_answer(question: str, references: list[KnowledgeChunk], spot: ScenicSpot | None, answer: str) -> bool:
    valid, _ = validate_local_answer(question, answer, references, spot)
    if valid:
        return True
    if spot is not None or references:
        return False
    if any(token in question for token in (*PARKING_HINTS, *TICKET_HINTS, *TRAFFIC_HINTS, *SERVICE_HINTS)):
        return True
    return KNOWLEDGE_GAP_MARKER not in answer and "暂时没有查到" not in answer


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


def answer_question(
    db: Session,
    question: str,
    user_id: str = "guest",
    enqueue_audio: bool = True,
    tts_mode: str = "auto",
) -> dict:
    started = time.perf_counter()
    question = normalize_text(question)
    digital_human = get_or_create_config(db)
    emotion = infer_emotion(question)
    answer_source = "local"
    scope_terms = current_scope_terms(db, digital_human.scenic_area)
    out_of_scope_answer = build_out_of_scope_answer(question, digital_human.scenic_area, scope_terms)

    if out_of_scope_answer:
        references = []
        reference_titles = [f"{OUT_OF_SCOPE_MARKER}:{digital_human.scenic_area or '当前景区'}"]
        answer = out_of_scope_answer
        answer_source = "out_of_scope"
    elif is_etiquette_question(question):
        references: list[KnowledgeChunk] = []
        reference_titles = ["文化礼仪提示"]
        answer = format_etiquette_answer(digital_human.scenic_area)
        answer_source = "etiquette_template"
    else:
        spot = match_spot(db, question)
        if spot is None and is_route_question(question):
            answer, reference_titles = build_route_answer(db, question, digital_human.scenic_area, user_id=user_id)
            references = []
            answer_source = "route_template"
        elif spot is None and is_generic_recommendation_question(question):
            answer, reference_titles = build_spot_recommendation(db, digital_human.scenic_area)
            references = []
            answer_source = "recommendation_template"
        else:
            references = []
            rag_used = False
            if settings.enable_rag:
                references = retrieve_rag_chunks(db, question, digital_human.scenic_area, top_k=settings.rag_top_k)
                rag_used = bool(references)
            if not references:
                references = build_references(db, question, spot, digital_human.scenic_area, top_k=3)
            if spot is not None:
                references = dedupe_chunks(
                    build_references(db, question, spot, digital_human.scenic_area, top_k=3) + references
                )[: settings.rag_top_k]
            direct_answer = extract_location_answer(question, references, digital_human.scenic_area, spot)
            local_answer = direct_answer or fallback_answer(question, references, spot)
            local_answer, repaired_local, local_answer_valid = review_local_answer(
                question,
                local_answer,
                references,
                digital_human.scenic_area,
                spot,
            )
            llm_answer = None
            if not local_answer_valid and not has_reliable_local_answer(question, references, spot, local_answer):
                llm_answer = call_llm_with_context(
                    question,
                    references,
                    digital_human.scenic_area,
                    timeout_seconds=min(settings.model_timeout_seconds, 0.9),
                )
                if llm_answer:
                    llm_answer = to_simplified_chinese(llm_answer)
                    llm_valid, _ = validate_local_answer(question, llm_answer, references, spot)
                    if not llm_valid:
                        llm_answer = None
            answer = llm_answer or local_answer or fallback_answer(question, references, spot)
            if llm_answer:
                answer_source = "rag_model_repair" if rag_used else "keyword_model_repair"
            elif direct_answer and not repaired_local:
                answer_source = "location_direct"
            elif repaired_local:
                if direct_answer:
                    answer_source = "location_repaired"
                elif references:
                    answer_source = "rag_local_repaired" if rag_used else "keyword_local_repaired"
                else:
                    answer_source = "local_repaired"
            elif references:
                answer_source = "rag_local" if rag_used else "keyword_local"
            else:
                answer_source = "knowledge_gap"
            reference_titles = [to_simplified_chinese(item.title) for item in references]
            if not reference_titles and spot is None:
                reference_titles = [build_gap_marker(question)]

    answer = clean_final_answer(answer)
    tts_mode = tts_mode if tts_mode in {"auto", "local_preferred", "server_only"} else "auto"
    should_enqueue_audio = bool(settings.enable_tts and enqueue_audio and tts_mode != "local_preferred")
    tts_mode_used = "browser_local" if tts_mode == "local_preferred" else "server_async"
    if tts_mode == "local_preferred":
        audio_status = "not_requested"
    else:
        audio_status = "pending" if should_enqueue_audio else "failed"
    audio_url = None
    video_status = "waiting_audio" if should_enqueue_audio and settings.avatar_only_enabled else "disabled"
    elapsed = round(time.perf_counter() - started, 3)

    log = QALog(
        user_id=user_id,
        question=question,
        answer=answer,
        source_titles="|".join(reference_titles),
        emotion=emotion,
        response_seconds=elapsed,
        audio_url="",
        audio_status=audio_status,
        audio_ready_seconds=0.0,
        video_url="",
        video_status=video_status,
        video_message="",
        video_ready_seconds=0.0,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    if should_enqueue_audio:
        queue_answer_audio(log.id, answer, digital_human.voice_name)

    return {
        "log_id": log.id,
        "answer": answer,
        "audio_url": None,
        "audio_status": audio_status,
        "english_available": english_service_configured(),
        "answer_source": answer_source,
        "model_name": main_model_name() if model_service_configured() else "",
        "lipsync_available": tts_mode == "local_preferred",
        "tts_mode_used": tts_mode_used,
        "video_url": None,
        "video_status": video_status,
        "emotion": emotion,
        "reference": reference_titles,
        "response_seconds": elapsed,
    }
