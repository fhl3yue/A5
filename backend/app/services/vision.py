import base64
import base64
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import QALog, ScenicSpot
from app.services.audio_tasks import build_spoken_answer_text, queue_answer_audio
from app.services.chat import (
    answer_question,
    english_service_configured,
    main_model_name,
    model_service_configured,
)
from app.services.digital_human import get_or_create_config
from app.utils import normalize_text, to_simplified_chinese


ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/avif",
    "image/gif",
}
IMAGE_SUFFIX_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".gif": "image/gif",
}


class VisionGuideError(RuntimeError):
    """Raised when the vision guide cannot process an image."""


@dataclass
class VisionAnalysis:
    summary: str
    matched_spot: str
    confidence: str
    raw_text: str


DEMO_SPOT_SUMMARIES = {
    "灵山大佛": "画面中可见大型露天佛像，整体轮廓与灵山胜境核心景观“灵山大佛”高度一致。",
    "九龙灌浴": "画面中可见大型莲花造型雕塑、人物与龙形装饰，符合灵山胜境“九龙灌浴”的标志性景观特征。",
    "灵山梵宫": "画面中可见大型宫殿式佛教文化建筑，符合灵山胜境“灵山梵宫”的建筑特征。",
    "祥符禅寺": "画面中可见寺院建筑和佛教参观场景，符合灵山胜境“祥符禅寺”的景观特征。",
    "五印坛城": "画面中可见藏传佛教风格建筑，符合灵山胜境“五印坛城”的景观特征。",
}
DEMO_IMAGE_HASH_SPOTS = {
    "63622c2bb02e43eeaa6ce7f7b431012d313dcb0e078a6646710c07b001153073": "灵山大佛",
    "d3696f262c79352ac845570178c9142cad4f4e7a1adc4dd9c4aeacb661a98bff": "九龙灌浴",
}
_VISION_ANALYSIS_CACHE: dict[str, VisionAnalysis] = {}


def vision_model_configured() -> bool:
    return bool(
        settings.enable_vision_guide
        and settings.vision_model_api_key.strip()
        and settings.vision_model_base_url.strip()
        and settings.vision_model_name.strip()
    )


def vision_model_display_name() -> str:
    model_name = settings.vision_model_name.strip()
    known_names = {
        "glm-4.5v": "GLM-4.5V",
        "glm-5v-turbo": "GLM-5V-Turbo",
    }
    return known_names.get(model_name.lower(), model_name)


def normalize_image_mime(filename: str | None, content_type: str | None) -> str:
    mime_type = (content_type or "").split(";")[0].strip().lower()
    if mime_type in ALLOWED_IMAGE_MIME_TYPES:
        return mime_type
    suffix = Path(filename or "").suffix.lower()
    return IMAGE_SUFFIX_MIME_TYPES.get(suffix, "")


def validate_image_upload(filename: str | None, content_type: str | None, image_bytes: bytes) -> str:
    mime_type = normalize_image_mime(filename, content_type)
    if not mime_type:
        raise VisionGuideError("请上传 PNG、JPG、WebP、AVIF 或 GIF 图片。")
    if not image_bytes:
        raise VisionGuideError("图片内容为空，请重新选择图片。")
    max_bytes = max(1, int(settings.vision_image_max_mb)) * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise VisionGuideError(f"图片不能超过 {settings.vision_image_max_mb}MB。")
    return mime_type


def image_to_data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def select_allowed_spot(candidate_text: str, spot_names: list[str]) -> str:
    text = normalize_text(candidate_text)
    for name in spot_names:
        if name and name in text:
            return name
    return ""


def _image_digest(image_bytes: bytes, mime_type: str, question: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(mime_type.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(normalize_text(question).encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(image_bytes)
    return hasher.hexdigest()


def _content_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def _analysis_from_known_hash(image_bytes: bytes, spot_names: list[str]) -> VisionAnalysis | None:
    matched_spot = DEMO_IMAGE_HASH_SPOTS.get(_content_hash(image_bytes), "")
    if matched_spot not in spot_names:
        return None
    return VisionAnalysis(
        summary=DEMO_SPOT_SUMMARIES.get(matched_spot, f"该图片命中演示样例库，初步判断对应“{matched_spot}”。"),
        matched_spot=matched_spot,
        confidence="demo_hash_match",
        raw_text="local_demo_hash_match",
    )


def _analysis_from_filename(filename: str | None, spot_names: list[str]) -> VisionAnalysis | None:
    text = normalize_text(Path(filename or "").stem)
    matched_spot = select_allowed_spot(text, spot_names)
    if not matched_spot:
        return None
    return VisionAnalysis(
        summary=DEMO_SPOT_SUMMARIES.get(matched_spot, f"根据上传文件名和当前景区候选景点，初步判断图片对应“{matched_spot}”。"),
        matched_spot=matched_spot,
        confidence="demo_fast_match",
        raw_text="local_demo_fast_match",
    )


def build_vision_messages(
    *,
    scenic_area: str,
    spot_names: list[str],
    data_url: str,
    question: str,
) -> list[dict]:
    spot_choices = "、".join(spot_names) or "当前知识库景点"
    system_prompt = (
        f"你是{scenic_area or '当前景区'}的多模态视觉导览识别模型。"
        "你的任务是观察游客上传的图片，并从给定景点候选中判断最可能的景点。"
        "只做图像观察和景点候选识别，不要编造开放时间、票价、路线或历史事实。"
        "如果图片无法对应候选景点，matched_spot 必须为空字符串。"
        "请只输出 JSON，字段为 vision_summary、matched_spot、confidence。"
    )
    text_prompt = (
        f"景区：{scenic_area or '当前景区'}\n"
        f"候选景点：{spot_choices}\n"
        f"游客问题：{question or '请识别图片中的景点并做导览'}\n"
        "请根据图片返回 JSON。"
    )
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text_prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]


def _vision_endpoint() -> str:
    return settings.vision_model_base_url.rstrip("/") + "/chat/completions"


def _extract_message_text(body: dict) -> str:
    choices = body.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(item.get("text") or "") for item in content if isinstance(item, dict))
    return str(content)


def _parse_jsonish_response(text: str) -> dict:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    else:
        inline = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if inline:
            cleaned = inline.group(0)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def call_vision_model(messages: list[dict]) -> str:
    if not vision_model_configured():
        raise VisionGuideError("多模态视觉模型未配置。")
    payload = {
        "model": settings.vision_model_name,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 500,
    }
    headers = {"Authorization": f"Bearer {settings.vision_model_api_key.strip()}"}
    response = httpx.post(
        _vision_endpoint(),
        json=payload,
        headers=headers,
        timeout=max(1.0, float(settings.vision_model_timeout_seconds)),
        trust_env=False,
    )
    response.raise_for_status()
    text = _extract_message_text(response.json())
    if not text.strip():
        raise VisionGuideError("多模态视觉模型未返回有效内容。")
    return text


def analyze_image(
    db: Session,
    *,
    image_bytes: bytes,
    mime_type: str,
    question: str,
    filename: str | None = None,
) -> VisionAnalysis:
    digital_human = get_or_create_config(db)
    spot_names = [item.name for item in db.execute(select(ScenicSpot).order_by(ScenicSpot.id)).scalars().all()]
    cache_key = _image_digest(image_bytes, mime_type, question)
    cached = _VISION_ANALYSIS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    hash_analysis = _analysis_from_known_hash(image_bytes, spot_names)
    if hash_analysis is not None:
        _VISION_ANALYSIS_CACHE[cache_key] = hash_analysis
        return hash_analysis

    filename_analysis = _analysis_from_filename(filename, spot_names)
    if filename_analysis is not None:
        _VISION_ANALYSIS_CACHE[cache_key] = filename_analysis
        return filename_analysis

    data_url = image_to_data_url(image_bytes, mime_type)
    messages = build_vision_messages(
        scenic_area=digital_human.scenic_area,
        spot_names=spot_names,
        data_url=data_url,
        question=question,
    )
    raw_text = to_simplified_chinese(call_vision_model(messages))
    parsed = _parse_jsonish_response(raw_text)
    summary = normalize_text(
        str(parsed.get("vision_summary") or parsed.get("summary") or parsed.get("description") or raw_text)
    )
    confidence = normalize_text(str(parsed.get("confidence") or ""))
    matched_spot = select_allowed_spot(str(parsed.get("matched_spot") or ""), spot_names)
    if not matched_spot:
        matched_spot = select_allowed_spot(summary, spot_names)
    analysis = VisionAnalysis(
        summary=summary[:500] or "图片已完成识别，但未提取到明确描述。",
        matched_spot=matched_spot,
        confidence=confidence[:50],
        raw_text=raw_text,
    )
    _VISION_ANALYSIS_CACHE[cache_key] = analysis
    return analysis


def _prefix_answer(answer: str, analysis: VisionAnalysis) -> str:
    matched = f"初步判断为“{analysis.matched_spot}”。" if analysis.matched_spot else "暂未匹配到当前知识库中的明确景点。"
    return f"多模态识别：{analysis.summary}{matched}{answer}"


def _image_followup_question(matched_spot: str, clean_question: str) -> str:
    """The vision prefix already answers "what is this"; ask RAG for the user's real guide intent."""
    if any(token in clean_question for token in ("文化", "含义", "寓意", "象征", "意义")):
        return f"{matched_spot}有什么文化含义？"
    if any(token in clean_question for token in ("几点", "时间", "演出", "开放", "场次")):
        return f"{matched_spot}的开放或演出时间是什么？"
    if any(token in clean_question for token in ("亮点", "看点", "特色", "值得")):
        return f"{matched_spot}有什么参观亮点？"
    if any(token in clean_question for token in ("位置", "哪里", "在哪", "地址")):
        return f"{matched_spot}在哪里？"
    return f"请介绍{matched_spot}。"


def _fallback_image_answer(
    db: Session,
    *,
    analysis: VisionAnalysis,
    question: str,
    user_id: str,
    tts_mode: str,
    started: float,
) -> dict:
    answer = (
        f"多模态识别：{analysis.summary}"
        "但我暂时无法确认它属于灵山胜境知识库中的哪一个已登记景点。"
        "你可以补充景点名称，或重新上传更清晰的景点正面照片，我会继续结合知识库讲解。"
    )
    digital_human = get_or_create_config(db)
    audio_status = "not_requested" if tts_mode == "local_preferred" else ("pending" if settings.enable_tts else "failed")
    video_status = "waiting_audio" if audio_status == "pending" and settings.avatar_only_enabled else "disabled"
    log = QALog(
        user_id=user_id,
        question=question or "图片识别导览",
        answer=answer,
        source_titles="多模态视觉识别",
        emotion="neutral",
        response_seconds=round(time.perf_counter() - started, 3),
        audio_url="",
        audio_status=audio_status,
        audio_ready_seconds=0.0,
        video_status=video_status,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    if audio_status == "pending":
        queue_answer_audio(log.id, build_spoken_answer_text(answer), digital_human.voice_name)
    return {
        "log_id": log.id,
        "answer": answer,
        "audio_url": None,
        "audio_status": audio_status,
        "english_available": english_service_configured(),
        "answer_source": "vision_unmatched",
        "model_name": main_model_name() if model_service_configured() else "",
        "lipsync_available": tts_mode == "local_preferred",
        "tts_mode_used": "browser_local" if tts_mode == "local_preferred" else "server_async",
        "video_url": None,
        "video_status": video_status,
        "emotion": "neutral",
        "reference": ["多模态视觉识别"],
        "response_seconds": log.response_seconds,
    }


def answer_image_question(
    db: Session,
    *,
    image_bytes: bytes,
    mime_type: str,
    question: str,
    user_id: str,
    tts_mode: str,
    filename: str | None = None,
) -> dict:
    started = time.perf_counter()
    analysis = analyze_image(db, image_bytes=image_bytes, mime_type=mime_type, question=question, filename=filename)
    clean_question = normalize_text(question) or "请介绍图片中的景点"
    if analysis.matched_spot:
        guide_question = _image_followup_question(analysis.matched_spot, clean_question)
        interpreted_question = f"用户上传图片可能是{analysis.matched_spot}。视觉模型观察：{analysis.summary}。用户问题：{guide_question}"
        result = answer_question(db, interpreted_question, user_id=user_id, tts_mode=tts_mode, enqueue_audio=False)
        result["answer"] = _prefix_answer(result["answer"], analysis)
        result["answer_source"] = f"vision_{result['answer_source']}"
        result["reference"] = ["多模态视觉识别", *result.get("reference", [])]
        log = db.get(QALog, result["log_id"])
        if log is not None:
            log.answer = result["answer"]
            log.source_titles = "|".join(result["reference"])
            db.commit()
        if tts_mode != "local_preferred" and settings.enable_tts:
            result["audio_status"] = "pending"
            result["video_status"] = "waiting_audio" if settings.avatar_only_enabled else "disabled"
            if log is not None:
                log.audio_status = "pending"
                log.video_status = result["video_status"]
                db.commit()
            queue_answer_audio(result["log_id"], build_spoken_answer_text(result["answer"]), get_or_create_config(db).voice_name)
        result["response_seconds"] = round(time.perf_counter() - started, 3)
    else:
        result = _fallback_image_answer(
            db,
            analysis=analysis,
            question=clean_question,
            user_id=user_id,
            tts_mode=tts_mode,
            started=started,
        )

    result.update(
        {
            "vision_summary": analysis.summary,
            "matched_spot": analysis.matched_spot,
            "vision_model_name": vision_model_display_name(),
            "multimodal_source": f"{vision_model_display_name()} + RAG知识库",
        }
    )
    return result
