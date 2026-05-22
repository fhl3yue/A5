import json
import math
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.services.chat import answer_question, main_model_name
from app.utils import normalize_text


ACCURACY_THRESHOLD = 0.9
LATENCY_THRESHOLD_SECONDS = 5.0
LATEST_EVALUATION_FILE = settings.generated_data_dir / "evaluation_latest.json"


EVALUATION_CASES = [
    {
        "case_id": "rag_jiulong_time",
        "question": "九龙灌浴几点开始表演",
        "expected_keywords": ["九龙灌浴", "10:00"],
        "min_hits": 2,
    },
    {
        "case_id": "rag_buddha_meaning",
        "question": "灵山大佛有什么文化含义",
        "expected_keywords": ["灵山大佛", "文化"],
        "min_hits": 2,
    },
    {
        "case_id": "route_half_day",
        "question": "我只有半天时间，怎么游览",
        "expected_keywords": ["半天", "路线", "灵山大佛"],
        "min_hits": 2,
    },
    {
        "case_id": "interest_history",
        "question": "我对历史文化感兴趣，推荐怎么游览",
        "expected_keywords": ["历史", "文化"],
        "min_hits": 1,
    },
    {
        "case_id": "interest_nature",
        "question": "我喜欢自然风光，想轻松一点游览",
        "expected_keywords": ["自然", "风光", "轻松"],
        "min_hits": 1,
    },
    {
        "case_id": "knowledge_gap_parking",
        "question": "有无停车地点",
        "expected_keywords": ["停车", "游客中心"],
        "min_hits": 1,
    },
]


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _case_result(case: dict, result: dict) -> dict:
    answer = normalize_text(result.get("answer", ""))
    reference = [normalize_text(item) for item in result.get("reference", [])]
    combined = f"{answer} {' '.join(reference)}"
    expected = case["expected_keywords"]
    hits = [keyword for keyword in expected if keyword in combined]
    passed = len(hits) >= int(case.get("min_hits", len(expected)))
    return {
        "case_id": case["case_id"],
        "question": case["question"],
        "passed": passed,
        "latency_seconds": float(result.get("response_seconds") or 0.0),
        "answer_source": result.get("answer_source", ""),
        "reference": result.get("reference", []),
        "expected_keywords": expected,
        "hit_keywords": hits,
        "answer_preview": answer[:120],
    }


def run_evaluation(db: Session) -> dict:
    results = []
    for case in EVALUATION_CASES:
        result = answer_question(db, case["question"], user_id="eval-runner", enqueue_audio=False)
        results.append(_case_result(case, result))

    latencies = [item["latency_seconds"] for item in results]
    passed_cases = sum(1 for item in results if item["passed"])
    total_cases = len(results)
    accuracy_rate = round(passed_cases / total_cases, 4) if total_cases else 0.0
    average_latency = round(sum(latencies) / len(latencies), 3) if latencies else 0.0
    p95_latency = round(_percentile(latencies, 0.95), 3)
    passed = accuracy_rate >= ACCURACY_THRESHOLD and p95_latency <= LATENCY_THRESHOLD_SECONDS

    data = {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "accuracy_rate": accuracy_rate,
        "average_latency_seconds": average_latency,
        "latency_p95_seconds": p95_latency,
        "passed": passed,
        "threshold_accuracy": ACCURACY_THRESHOLD,
        "threshold_latency_seconds": LATENCY_THRESHOLD_SECONDS,
        "model_name": main_model_name(),
        "generated_at": datetime.utcnow().isoformat(),
        "case_results": results,
    }
    save_latest_evaluation(data)
    return data


def save_latest_evaluation(data: dict) -> None:
    LATEST_EVALUATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    LATEST_EVALUATION_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_latest_evaluation() -> dict:
    if not Path(LATEST_EVALUATION_FILE).exists():
        return {
            "total_cases": 0,
            "passed_cases": 0,
            "accuracy_rate": 0.0,
            "average_latency_seconds": 0.0,
            "latency_p95_seconds": 0.0,
            "passed": False,
            "threshold_accuracy": ACCURACY_THRESHOLD,
            "threshold_latency_seconds": LATENCY_THRESHOLD_SECONDS,
            "model_name": main_model_name(),
            "generated_at": None,
            "case_results": [],
        }
    return json.loads(LATEST_EVALUATION_FILE.read_text(encoding="utf-8"))
