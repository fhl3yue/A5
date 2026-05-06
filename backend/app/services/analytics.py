from collections import Counter
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import QALog
from app.utils import looks_garbled


def is_dashboard_hot_question(text: str) -> bool:
    normalized = text.strip()
    if looks_garbled(normalized):
        return False
    if len(normalized) > 40:
        return False
    if "？" in normalized or "?" in normalized:
        return True
    hint_words = ("几点", "时间", "表演", "演出", "推荐", "路线", "什么", "怎么", "哪里", "多高", "含义", "特色")
    return any(token in normalized for token in hint_words)


def build_dashboard(db: Session) -> dict:
    today = date.today()
    logs = db.execute(select(QALog).where(func.date(QALog.created_at) == today.isoformat())).scalars().all()
    all_logs = db.execute(select(QALog)).scalars().all()

    today_visitors = len({item.user_id for item in logs})
    today_qa_count = len(logs)

    ratings = [item.satisfaction for item in all_logs if item.satisfaction is not None]
    satisfaction_rate = float(round(sum(1 for item in ratings if item >= 4) / len(ratings), 2)) if ratings else 0.0

    hot_counter = Counter(item.question for item in all_logs if is_dashboard_hot_question(item.question))
    hot_questions = [{"name": q, "count": c} for q, c in hot_counter.most_common(10)]

    emotion_counter = Counter(item.emotion for item in all_logs)
    emotion_distribution = [
        {"name": name, "value": value}
        for name, value in emotion_counter.items()
    ] or [
        {"name": "positive", "value": 0},
        {"name": "neutral", "value": 0},
        {"name": "negative", "value": 0},
    ]

    return {
        "today_visitors": today_visitors,
        "today_qa_count": today_qa_count,
        "satisfaction_rate": satisfaction_rate,
        "hot_questions": hot_questions,
        "emotion_distribution": emotion_distribution,
        "weekly_service_trend": build_service_trend(all_logs),
        "satisfaction_trend": build_satisfaction_trend(all_logs),
    }


def build_visitor_report(db: Session) -> dict:
    all_logs = db.execute(select(QALog).order_by(QALog.created_at)).scalars().all()
    if not all_logs:
        return {
            "summary": "当前暂无游客互动记录，建议先完成文本问答、语音问答和满意度反馈测试。",
            "focus_points": [],
            "emotion_trend": build_empty_trend(),
            "service_suggestions": ["先积累不少于 10 条真实或模拟问答记录，再生成更可靠的运营建议。"],
        }

    focus_counter = Counter(item.question for item in all_logs if is_dashboard_hot_question(item.question))
    focus_points = [{"name": name, "count": count} for name, count in focus_counter.most_common(6)]

    ratings = [item.satisfaction for item in all_logs if item.satisfaction is not None]
    satisfaction_rate = round(sum(1 for item in ratings if item >= 4) / len(ratings), 2) if ratings else 0.0
    emotion_counter = Counter(item.emotion for item in all_logs)
    avg_response_seconds = sum(item.response_seconds for item in all_logs) / len(all_logs)

    summary = (
        f"已分析 {len(all_logs)} 条游客互动记录，满意度为 {int(satisfaction_rate * 100)}%。"
        f"当前主要情绪为 {emotion_counter.most_common(1)[0][0]}，平均响应耗时 {avg_response_seconds:.2f} 秒。"
    )

    suggestions = build_service_suggestions(focus_counter, emotion_counter, satisfaction_rate, avg_response_seconds, ratings)
    return {
        "summary": summary,
        "focus_points": focus_points,
        "emotion_trend": build_emotion_trend(all_logs),
        "service_suggestions": suggestions,
    }


def build_empty_trend() -> list[dict]:
    today = date.today()
    return [
        {
            "date": (today - timedelta(days=offset)).isoformat(),
            "positive": 0,
            "neutral": 0,
            "negative": 0,
        }
        for offset in range(6, -1, -1)
    ]


def build_service_trend(logs: list[QALog]) -> list[dict]:
    today = date.today()
    buckets = {
        (today - timedelta(days=offset)).isoformat(): {"visitors": set(), "qa_count": 0}
        for offset in range(6, -1, -1)
    }
    for item in logs:
        day = item.created_at.date().isoformat()
        if day not in buckets:
            continue
        buckets[day]["visitors"].add(item.user_id)
        buckets[day]["qa_count"] += 1

    return [
        {
            "date": day,
            "visitors": len(values["visitors"]),
            "qa_count": values["qa_count"],
        }
        for day, values in buckets.items()
    ]


def build_satisfaction_trend(logs: list[QALog]) -> list[dict]:
    today = date.today()
    buckets = {
        (today - timedelta(days=offset)).isoformat(): []
        for offset in range(6, -1, -1)
    }
    for item in logs:
        day = item.created_at.date().isoformat()
        if day in buckets and item.satisfaction is not None:
            buckets[day].append(item.satisfaction)

    return [
        {
            "date": day,
            "satisfaction_rate": round(sum(1 for rating in ratings if rating >= 4) / len(ratings), 2) if ratings else 0.0,
            "rating_count": len(ratings),
        }
        for day, ratings in buckets.items()
    ]


def build_emotion_trend(logs: list[QALog]) -> list[dict]:
    today = date.today()
    buckets = {
        (today - timedelta(days=offset)).isoformat(): {"positive": 0, "neutral": 0, "negative": 0}
        for offset in range(6, -1, -1)
    }
    for item in logs:
        day = item.created_at.date().isoformat()
        if day not in buckets:
            continue
        emotion = item.emotion if item.emotion in {"positive", "neutral", "negative"} else "neutral"
        buckets[day][emotion] += 1

    return [
        {
            "date": day,
            **values,
        }
        for day, values in buckets.items()
    ]


def build_service_suggestions(
    focus_counter: Counter,
    emotion_counter: Counter,
    satisfaction_rate: float,
    avg_response_seconds: float,
    ratings: list[int],
) -> list[str]:
    suggestions: list[str] = []
    focus_text = " ".join(focus_counter.keys())

    if "几点" in focus_text or "时间" in focus_text or "演出" in focus_text:
        suggestions.append("游客高频关注演出时间，建议在游客端首页固定展示九龙灌浴、吉祥颂等核心演出时刻。")
    if "路线" in focus_text or "怎么" in focus_text or "推荐" in focus_text:
        suggestions.append("路线规划需求较明显，建议按半天、全天、亲子、文化深度等场景维护更多路线模板。")
    if ratings and satisfaction_rate < 0.75:
        suggestions.append("满意度低于 75%，建议人工复核低评分问答，补充缺失知识点或优化回答表达。")
    if emotion_counter.get("negative", 0) > emotion_counter.get("positive", 0):
        suggestions.append("负向情绪偏高，建议优先检查无法回答、答非所问和语音识别失败场景。")
    if avg_response_seconds > 1.5:
        suggestions.append("平均响应耗时偏高，建议优化知识检索逻辑或缓存高频问题答案。")

    if not suggestions:
        suggestions.append("当前服务状态较稳定，建议继续扩充景点讲解、交通动线、演出时间和常见问题资料。")
    return suggestions[:5]
