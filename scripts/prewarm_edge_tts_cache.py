from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import ensure_runtime_dirs, settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import QALog  # noqa: E402
from app.services.audio import generate_tts_audio, get_tts_runtime_status  # noqa: E402
from app.services.audio_tasks import build_spoken_answer_text  # noqa: E402
from app.services.chat import answer_question  # noqa: E402
from app.services.digital_human import get_or_create_config  # noqa: E402
from app.services.evaluation import EVALUATION_CASES  # noqa: E402


DEMO_QUESTIONS = [
    "九龙灌浴几点开始表演？",
    "灵山大佛有什么文化含义？",
    "我只有半天时间怎么游览？",
    "灵山胜境具体位置在哪？",
    "景区有没有停车地点？",
    "带孩子来灵山胜境推荐怎么玩？",
    "第一次来灵山胜境，有什么推荐景点？",
    "灵山胜境有哪些必看景点？",
    "我想看演出，怎么安排路线？",
    "老人想轻松一点怎么游览？",
    "适合拍照打卡的地方推荐一下。",
    "灵山梵宫有什么特色？",
    "参观祈福时有什么需要注意的礼仪？",
]

DEMO_SPOKEN_TEXTS = [
    "欢迎来到灵山胜境，我可以为你讲解景点、推荐路线，也可以识别你上传的景区照片。",
    "当前知识库暂未查到可靠资料，我可以先记录这个问题，建议你也可以咨询景区现场服务台。",
    "语音已准备好，你可以点击播放，也可以继续输入新的问题。",
]


def _unique_questions(include_evaluation: bool, include_demo: bool) -> list[str]:
    questions: list[str] = []
    if include_evaluation:
        questions.extend(str(item["question"]) for item in EVALUATION_CASES)
    if include_demo:
        questions.extend(DEMO_QUESTIONS)

    seen: set[str] = set()
    unique: list[str] = []
    for question in questions:
        normalized = question.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def prewarm_edge_cache(include_evaluation: bool, include_demo: bool, limit: int | None = None) -> dict:
    ensure_runtime_dirs()
    questions = _unique_questions(include_evaluation, include_demo)
    direct_spoken_texts = DEMO_SPOKEN_TEXTS if include_demo else []
    if limit is not None and limit > 0:
        questions = questions[:limit]
        direct_spoken_texts = direct_spoken_texts[: max(0, limit - len(questions))]
    if not questions and not direct_spoken_texts:
        status = get_tts_runtime_status()
        return {
            "processed": 0,
            "generated": 0,
            "cache_hits": 0,
            "failed": 0,
            "cache_items": status.get("edge_tts_cache_items", 0),
            "elapsed_seconds": 0.0,
        }

    original_values = {
        "enable_tts": settings.enable_tts,
        "server_tts_provider": settings.server_tts_provider,
        "local_tts_enabled": settings.local_tts_enabled,
        "edge_tts_cache_enabled": settings.edge_tts_cache_enabled,
    }

    settings.enable_tts = True
    settings.server_tts_provider = "edge"
    settings.local_tts_enabled = False
    settings.edge_tts_cache_enabled = True

    started = time.perf_counter()
    generated = 0
    cache_hits = 0
    failed = 0
    processed = 0

    db = SessionLocal()
    try:
        voice_name = get_or_create_config(db).voice_name
        for question in questions:
            answer_result = answer_question(db, question, user_id="edge-cache-prewarm", enqueue_audio=False)
            spoken_text = build_spoken_answer_text(answer_result["answer"])
            audio_url = generate_tts_audio(spoken_text, voice_name, enabled=True) if spoken_text else None
            status = get_tts_runtime_status()
            processed += 1
            if not audio_url:
                failed += 1
            elif status.get("last_provider") == "edge_tts_cache":
                cache_hits += 1
            else:
                generated += 1
            log = db.get(QALog, answer_result["log_id"])
            if log is not None:
                db.delete(log)
                db.commit()
            print(
                f"[{processed:02d}/{len(questions):02d}] "
                f"{status.get('last_provider') or 'failed'} "
                f"{status.get('last_elapsed_seconds', 0):.3f}s "
                f"{question}"
            )
        for spoken_text in direct_spoken_texts:
            audio_url = generate_tts_audio(build_spoken_answer_text(spoken_text), voice_name, enabled=True)
            status = get_tts_runtime_status()
            processed += 1
            if not audio_url:
                failed += 1
            elif status.get("last_provider") == "edge_tts_cache":
                cache_hits += 1
            else:
                generated += 1
            print(
                f"[{processed:02d}/{len(questions) + len(direct_spoken_texts):02d}] "
                f"{status.get('last_provider') or 'failed'} "
                f"{status.get('last_elapsed_seconds', 0):.3f}s "
                f"{spoken_text}"
            )
    finally:
        db.close()
        for name, value in original_values.items():
            setattr(settings, name, value)

    final_status = get_tts_runtime_status()
    return {
        "processed": processed,
        "generated": generated,
        "cache_hits": cache_hits,
        "failed": failed,
        "cache_items": final_status.get("edge_tts_cache_items", 0),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prewarm deterministic Edge TTS audio cache.")
    parser.add_argument("--skip-evaluation", action="store_true", help="Skip the built-in 50 evaluation questions.")
    parser.add_argument("--skip-demo", action="store_true", help="Skip the extra demo questions.")
    parser.add_argument("--limit", type=int, default=0, help="Limit question count for quick smoke tests.")
    args = parser.parse_args()

    summary = prewarm_edge_cache(
        include_evaluation=not args.skip_evaluation,
        include_demo=not args.skip_demo,
        limit=args.limit or None,
    )
    print("\nEdge TTS cache prewarm summary:")
    for key, value in summary.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
