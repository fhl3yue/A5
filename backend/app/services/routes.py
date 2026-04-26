from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RoutePreset


def recommend_route(db: Session, interest: str, duration: str) -> dict:
    interest = interest.strip()
    duration = duration.strip() or "半天"

    stmt = select(RoutePreset).where(RoutePreset.interest == interest, RoutePreset.duration == duration)
    route = db.execute(stmt).scalar_one_or_none()
    if route is None:
        stmt = select(RoutePreset).where(RoutePreset.interest == interest)
        route = db.execute(stmt).scalar_one_or_none()
    if route is None:
        route = db.execute(select(RoutePreset)).scalars().first()
    if route is None:
        return {
            "route_name": "默认推荐路线",
            "route_spots": ["灵山大佛", "九龙灌浴", "灵山梵宫"],
            "reason": "当前没有命中预设路线，返回基础精华路线。",
        }

    return {
        "route_name": route.name,
        "route_spots": [item for item in route.spots.split("|") if item],
        "reason": route.reason,
    }

