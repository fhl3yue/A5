from collections import Counter
from datetime import date

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
    }
