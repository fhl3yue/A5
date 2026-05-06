from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RoutePreset
from app.utils import overlap_score


INTEREST_ALIASES = {
    "亲子休闲": ["亲子", "家庭", "孩子", "儿童", "轻松", "拍照", "打卡", "老人", "慢游"],
    "自然风光": ["自然", "风光", "休闲", "散步", "避开人流", "安静", "步行", "林荫", "放松"],
    "佛教文化": ["佛教", "祈福", "朝圣", "禅", "佛", "宗教", "文化深度", "寺"],
    "历史文化": ["历史", "文史", "文化", "建筑", "艺术", "典故", "传统"],
}


def normalize_duration(duration: str) -> str:
    text = duration.strip()
    if not text:
        return "半天"
    if any(token in text for token in ["全天", "一天", "1天", "整天", "深度"]):
        return "全天"
    if any(token in text for token in ["半天", "半日", "2小时", "两小时", "3小时", "三小时", "上午", "下午"]):
        return "半天"
    return text


def infer_interest(interest: str) -> str:
    text = interest.strip()
    if not text:
        return "历史文化"
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
    if scored:
        return max(scored, key=lambda item: item[0])[1]
    return text


def route_score(route: RoutePreset, raw_interest: str, inferred_interest: str, duration: str) -> float:
    searchable = f"{route.name} {route.interest} {route.duration} {route.spots} {route.reason}"
    score = overlap_score(raw_interest, searchable) + overlap_score(inferred_interest, searchable)
    if route.interest == inferred_interest:
        score += 2.0
    if route.duration == duration:
        score += 1.0
    for alias in INTEREST_ALIASES.get(route.interest, []):
        if alias in raw_interest:
            score += 0.45
    return score


def recommend_route(db: Session, interest: str, duration: str) -> dict:
    raw_interest = interest.strip()
    inferred_interest = infer_interest(raw_interest)
    duration = normalize_duration(duration)

    stmt = select(RoutePreset).where(RoutePreset.interest == inferred_interest, RoutePreset.duration == duration)
    route = db.execute(stmt).scalar_one_or_none()
    if route is None:
        stmt = select(RoutePreset).where(RoutePreset.interest == inferred_interest)
        route = db.execute(stmt).scalar_one_or_none()
    if route is None:
        routes = db.execute(select(RoutePreset)).scalars().all()
        route = max(routes, key=lambda item: route_score(item, raw_interest, inferred_interest, duration), default=None)
    if route is None:
        return {
            "route_name": "默认推荐路线",
            "route_spots": ["灵山大佛", "九龙灌浴", "灵山梵宫"],
            "reason": "当前没有命中预设路线，返回基础精华路线。",
        }

    return {
        "route_name": route.name,
        "route_spots": [item for item in route.spots.split("|") if item],
        "reason": route.reason
        if raw_interest == inferred_interest
        else f"根据你输入的“{raw_interest}”，系统匹配到“{inferred_interest}”偏好。{route.reason}",
    }
