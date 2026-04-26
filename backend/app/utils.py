import re


def normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def char_ngrams(text: str, n: int = 2) -> set[str]:
    compact = re.sub(r"\s+", "", text)
    if len(compact) <= n:
        return {compact} if compact else set()
    return {compact[i : i + n] for i in range(len(compact) - n + 1)}


def overlap_score(query: str, content: str) -> float:
    query_set = char_ngrams(query)
    content_set = char_ngrams(content)
    if not query_set or not content_set:
        return 0.0
    inter = len(query_set & content_set)
    ratio = inter / max(len(query_set), 1)
    bonus = 0.0
    if query in content:
        bonus += 1.5
    return ratio + bonus


def looks_garbled(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return True
    question_marks = normalized.count("?")
    if question_marks >= max(3, len(normalized) // 2):
        return True
    useful_chars = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", normalized)
    return len(useful_chars) < max(1, len(normalized) // 5)


QUESTION_KEYWORDS = [
    "几点",
    "时间",
    "時間",
    "表演",
    "演出",
    "演出时间",
    "演出時間",
    "开放",
    "開放",
    "路线",
    "路線",
    "推荐",
    "推薦",
    "怎么",
    "哪里",
    "什么",
    "多高",
    "含义",
    "介绍",
    "适合",
    "历史",
    "文化",
]

SCENIC_KEYWORDS = [
    "灵山胜境",
    "九龙灌浴",
    "菩提大道",
    "灵山大佛",
    "灵山梵宫",
    "祥符禅寺",
    "五印坛城",
    "佛足坛",
    "五智门",
    "五明桥",
    "灵山大照壁",
]


def _segment_score(segment: str) -> int:
    score = 0
    score += sum(4 for token in SCENIC_KEYWORDS if token in segment)
    score += sum(3 for token in QUESTION_KEYWORDS if token in segment)
    if len(segment) <= 30:
        score += 2
    if "？" in segment or "?" in segment:
        score += 2
    return score


def _contains_any(text: str, tokens: list[str]) -> bool:
    return any(token in text for token in tokens)


def refine_voice_question(text: str) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return normalized

    normalized = normalized.replace("？", "?").replace("。", "。").replace("，", "，")
    segments = re.split(r"[。！？!?；;，,]", normalized)
    segments = [seg.strip() for seg in segments if seg.strip()]
    if not segments:
        return normalized

    ranked = sorted(segments, key=_segment_score, reverse=True)
    best = ranked[0]

    if len(best) <= 32 and _segment_score(best) >= 4:
        if not best.endswith(("?", "？")) and any(token in best for token in QUESTION_KEYWORDS):
            if "几点" in best or "时间" in best:
                return best + "？"
        return best

    scenic_hits = [token for token in SCENIC_KEYWORDS if token in normalized]
    if scenic_hits:
        scenic = scenic_hits[0]
        if _contains_any(normalized, ["几点", "时间", "時間", "演出时间", "演出時間"]):
            return f"{scenic}几点开始表演？"
        if _contains_any(normalized, ["推荐", "推薦", "路线", "路線"]):
            return f"{scenic}相关路线怎么推荐？"
        if _contains_any(normalized, ["介绍", "介紹", "什么", "特色", "亮点", "亮點"]):
            return f"{scenic}有什么特色？"

    return best[:40]
