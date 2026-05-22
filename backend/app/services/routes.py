from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import QALog, RoutePreset
from app.utils import normalize_text, overlap_score


INTEREST_ALIASES = {
    "亲子休闲": ["亲子", "家庭", "孩子", "儿童", "轻松", "拍照", "打卡", "老人", "慢游"],
    "自然风光": ["自然", "风光", "休闲", "散步", "避开人流", "安静", "步行", "林荫", "放松"],
    "佛教文化": ["佛教", "祈福", "朝圣", "禅", "佛", "宗教", "文化深度", "梵宫"],
    "历史文化": ["历史", "文史", "文化", "建筑", "艺术", "典故", "传统"],
}

GENERIC_INTEREST_HINTS = ("推荐", "随便", "都可以", "不知道", "帮我", "适合我")


def normalize_duration(duration: str) -> str:
    text = normalize_text(duration).strip()
    if not text:
        return "半天"
    if any(token in text for token in ["全天", "一天", "1天", "整天", "深度"]):
        return "全天"
    if any(token in text for token in ["半天", "半日", "2小时", "两小时", "3小时", "三小时", "上午", "下午"]):
        return "半天"
    return text


def _score_interest(text: str) -> list[tuple[float, str]]:
    scored: list[tuple[float, str]] = []
    for canonical, aliases in INTEREST_ALIASES.items():
        score = 0.0
        if canonical in text:
            score += 3.0
        for alias in aliases:
            if alias in text:
                score += 1.0 + min(len(alias) / 10, 0.8)
        if score:
            scored.append((score, canonical))
    return scored


def infer_interest(interest: str) -> str:
    text = normalize_text(interest).strip()
    if not text:
        return "历史文化"
    scored = _score_interest(text)
    if scored:
        return max(scored, key=lambda item: item[0])[1]
    return text


def infer_user_profile(db: Session, user_id: str) -> tuple[str, list[str]]:
    if not user_id or user_id == "guest":
        return "", []
    logs = db.execute(
        select(QALog).where(QALog.user_id == user_id).order_by(desc(QALog.created_at)).limit(8)
    ).scalars().all()
    if not logs:
        return "", []

    text = " ".join(normalize_text(f"{item.question} {item.source_titles}") for item in logs)
    scored = _score_interest(text)
    if not scored:
        return "", []

    interest = max(scored, key=lambda item: item[0])[1]
    evidence = []
    for log in logs[:3]:
        question = normalize_text(log.question)
        if any(alias in question for alias in INTEREST_ALIASES.get(interest, [])):
            evidence.append(question[:24])
    return interest, evidence[:2]


def route_score(route: RoutePreset, raw_interest: str, inferred_interest: str, profile_interest: str, duration: str) -> float:
    searchable = f"{route.name} {route.interest} {route.duration} {route.spots} {route.reason}"
    score = overlap_score(raw_interest, searchable) + overlap_score(inferred_interest, searchable)
    if route.interest == inferred_interest:
        score += 2.0
    if profile_interest and route.interest == profile_interest:
        score += 1.2
    if route.duration == duration:
        score += 1.0
    for alias in INTEREST_ALIASES.get(route.interest, []):
        if alias in raw_interest:
            score += 0.45
    return score


def _select_route(db: Session, raw_interest: str, inferred_interest: str, profile_interest: str, duration: str) -> RoutePreset | None:
    target_interest = inferred_interest
    if profile_interest and (not raw_interest or any(token in raw_interest for token in GENERIC_INTEREST_HINTS)):
        target_interest = profile_interest

    route = db.execute(
        select(RoutePreset).where(RoutePreset.interest == target_interest, RoutePreset.duration == duration)
    ).scalar_one_or_none()
    if route is not None:
        return route

    route = db.execute(select(RoutePreset).where(RoutePreset.interest == target_interest)).scalar_one_or_none()
    if route is not None:
        return route

    routes = db.execute(select(RoutePreset)).scalars().all()
    return max(
        routes,
        key=lambda item: route_score(item, raw_interest, inferred_interest, profile_interest, duration),
        default=None,
    )


def recommend_route(db: Session, interest: str, duration: str, user_id: str = "guest") -> dict:
    raw_interest = normalize_text(interest).strip()
    inferred_interest = infer_interest(raw_interest)
    profile_interest, evidence = infer_user_profile(db, user_id)
    duration = normalize_duration(duration)
    route = _select_route(db, raw_interest, inferred_interest, profile_interest, duration)

    matched_interest = profile_interest if profile_interest and any(token in raw_interest for token in GENERIC_INTEREST_HINTS) else inferred_interest
    basis = [f"当前输入：{raw_interest or '未填写'}", f"游览时长：{duration}"]
    if profile_interest:
        basis.append(f"历史偏好：{profile_interest}")
    basis.extend(f"近期问题：{item}" for item in evidence)

    if route is None:
        return {
            "route_name": "默认推荐路线",
            "route_spots": ["灵山大佛", "九龙灌浴", "灵山梵宫"],
            "reason": "当前没有命中预设路线，先返回覆盖核心景点的基础路线。",
            "matched_interest": matched_interest,
            "personalization_basis": basis[:4],
        }

    reason = route.reason
    if profile_interest and profile_interest != inferred_interest:
        reason = f"结合你最近关注的“{profile_interest}”与本次输入“{raw_interest}”，{route.reason}"
    elif raw_interest != inferred_interest:
        reason = f"根据你输入的“{raw_interest}”，系统匹配到“{inferred_interest}”偏好。{route.reason}"

    return {
        "route_name": route.name,
        "route_spots": [item for item in route.spots.split("|") if item],
        "reason": reason,
        "matched_interest": matched_interest,
        "personalization_basis": basis[:4],
    }
