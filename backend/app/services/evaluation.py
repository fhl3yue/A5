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
        "case_id": "fact_location_city",
        "question": "灵山胜境具体在哪个城市",
        "expected_keywords": ["江苏", "无锡", "马山"],
        "min_hits": 2,
    },
    {
        "case_id": "fact_scenic_level",
        "question": "灵山胜境是不是国家5A级旅游景区",
        "expected_keywords": ["国家", "5A"],
        "min_hits": 2,
    },
    {
        "case_id": "fact_forum_site",
        "question": "灵山胜境和世界佛教论坛有什么关系",
        "expected_keywords": ["世界佛教论坛", "永久会址"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_xiaolingshan_origin",
        "question": "小灵山这个名字有什么由来",
        "expected_keywords": ["玄奘", "小灵山", "灵鹫山"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_xiangfu_history",
        "question": "祥符禅寺有什么历史",
        "expected_keywords": ["北宋", "祥符禅寺", "千年"],
        "min_hits": 2,
    },
    {
        "case_id": "fact_zhaobi_calligraphy",
        "question": "灵山大照壁是谁题写的",
        "expected_keywords": ["赵朴初", "灵山胜境"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_zhaobi_size",
        "question": "灵山大照壁有多大",
        "expected_keywords": ["39.8", "7", "青石"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_wuming_bridge_meaning",
        "question": "五明桥象征什么",
        "expected_keywords": ["五明", "智慧"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_foot_altar_meaning",
        "question": "佛足坛是什么",
        "expected_keywords": ["佛足", "脚印", "释迦牟尼"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_wuzhi_gate_meaning",
        "question": "五智门有什么象征意义",
        "expected_keywords": ["五方五佛", "六度", "波罗蜜"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_bodhi_avenue_meaning",
        "question": "菩提大道的文化意义是什么",
        "expected_keywords": ["菩提", "悟道", "成佛"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_jiulong_time",
        "question": "九龙灌浴几点开始表演",
        "expected_keywords": ["九龙灌浴", "10:00", "11:30"],
        "min_hits": 2,
    },
    {
        "case_id": "fact_jiulong_highlight",
        "question": "九龙灌浴有什么看点",
        "expected_keywords": ["喷泉", "圣水", "表演"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_buddha_height",
        "question": "灵山大佛多高",
        "expected_keywords": ["88", "101.5", "青铜"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_buddha_meaning",
        "question": "灵山大佛有什么文化含义",
        "expected_keywords": ["灵山大佛", "慈悲", "智慧"],
        "min_hits": 2,
    },
    {
        "case_id": "fact_fangong_feature",
        "question": "灵山梵宫有什么特色",
        "expected_keywords": ["建筑艺术", "吉祥颂", "沉浸式"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_jixiang_song_time",
        "question": "灵山梵宫的吉祥颂几点演出",
        "expected_keywords": ["吉祥颂", "10:35", "16:00"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_xiangfu_highlight",
        "question": "祥符禅寺有哪些看点",
        "expected_keywords": ["祥符禅寺", "千年银杏", "古井"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_wuyin_tancheng_style",
        "question": "五印坛城是什么风格",
        "expected_keywords": ["藏传", "五方五佛", "金顶红墙"],
        "min_hits": 1,
    },
    {
        "case_id": "fact_blessing_experience",
        "question": "灵山胜境有哪些祈福体验",
        "expected_keywords": ["九龙灌浴", "天下第一掌", "抱佛脚"],
        "min_hits": 1,
    },
    {
        "case_id": "route_half_day",
        "question": "我只有半天时间，怎么游览",
        "expected_keywords": ["半天", "路线", "灵山大佛"],
        "min_hits": 2,
    },
    {
        "case_id": "route_full_day_buddhist",
        "question": "我想安排一天佛教文化深度游",
        "expected_keywords": ["全天", "佛教文化", "五印坛城"],
        "min_hits": 2,
    },
    {
        "case_id": "route_nature_relax",
        "question": "我喜欢自然风光，想轻松一点游览",
        "expected_keywords": ["自然风光", "菩提大道", "九龙灌浴"],
        "min_hits": 1,
    },
    {
        "case_id": "route_family_child",
        "question": "带孩子来灵山胜境，推荐怎么游览",
        "expected_keywords": ["亲子", "九龙灌浴", "灵山大佛"],
        "min_hits": 1,
    },
    {
        "case_id": "route_history_interest",
        "question": "我对历史文化感兴趣，推荐怎么游览",
        "expected_keywords": ["历史文化", "祥符禅寺", "灵山大佛"],
        "min_hits": 1,
    },
    {
        "case_id": "route_first_visit",
        "question": "第一次来灵山胜境，有什么推荐景点",
        "expected_keywords": ["九龙灌浴", "灵山大佛", "灵山梵宫"],
        "min_hits": 2,
    },
    {
        "case_id": "route_must_see",
        "question": "灵山胜境有哪些必看景点",
        "expected_keywords": ["九龙灌浴", "灵山大佛", "灵山梵宫"],
        "min_hits": 1,
    },
    {
        "case_id": "route_performance_plan",
        "question": "我想看演出，怎么安排路线",
        "expected_keywords": ["九龙灌浴", "灵山梵宫", "演出"],
        "min_hits": 1,
    },
    {
        "case_id": "route_elder_easy",
        "question": "老人想轻松一点怎么游览",
        "expected_keywords": ["半天", "路线", "九龙灌浴"],
        "min_hits": 1,
    },
    {
        "case_id": "route_photo_checkin",
        "question": "适合拍照打卡的地方推荐一下",
        "expected_keywords": ["灵山大佛", "九龙灌浴", "灵山梵宫"],
        "min_hits": 1,
    },
    {
        "case_id": "service_parking",
        "question": "有无停车地点",
        "expected_keywords": ["停车", "游客中心"],
        "min_hits": 1,
    },
    {
        "case_id": "service_ticket",
        "question": "灵山胜境门票多少钱",
        "expected_keywords": ["票务", "游客中心", "现场公告"],
        "min_hits": 1,
    },
    {
        "case_id": "service_traffic",
        "question": "从市区怎么去景区，交通方便吗",
        "expected_keywords": ["交通", "游客中心", "出行指引"],
        "min_hits": 1,
    },
    {
        "case_id": "service_dining",
        "question": "景区里面哪里可以吃饭",
        "expected_keywords": ["配套服务", "餐饮", "游客中心"],
        "min_hits": 1,
    },
    {
        "case_id": "service_toilet",
        "question": "附近有没有洗手间",
        "expected_keywords": ["配套服务", "洗手间", "游客中心"],
        "min_hits": 1,
    },
    {
        "case_id": "service_wheelchair",
        "question": "景区有轮椅或无障碍服务吗",
        "expected_keywords": ["配套服务", "轮椅", "游客中心"],
        "min_hits": 1,
    },
    {
        "case_id": "service_luggage",
        "question": "游客能不能寄存行李",
        "expected_keywords": ["配套服务", "寄存", "游客中心"],
        "min_hits": 1,
    },
    {
        "case_id": "boundary_weather",
        "question": "如果下雨，今天的演出还正常吗",
        "expected_keywords": ["公告为准", "现场", "演出"],
        "min_hits": 1,
    },
    {
        "case_id": "boundary_fortune",
        "question": "你能帮我预测今天运势吗",
        "expected_keywords": ["暂时没有查到", "游客中心"],
        "min_hits": 1,
    },
    {
        "case_id": "boundary_unrelated_spot",
        "question": "高家庄好玩吗，能给我推荐路线吗",
        "expected_keywords": ["灵山胜境", "当前景区", "路线"],
        "min_hits": 1,
    },
    {
        "case_id": "culture_overview",
        "question": "灵山胜境的佛教文化特色是什么",
        "expected_keywords": ["佛教", "文化"],
        "min_hits": 1,
    },
    {
        "case_id": "culture_blessing_safe",
        "question": "参观祈福时有什么需要注意的礼仪",
        "expected_keywords": ["文化礼仪", "现场标识", "不宣称"],
        "min_hits": 1,
    },
    {
        "case_id": "culture_han_tibetan",
        "question": "景区里能看到藏传佛教文化吗",
        "expected_keywords": ["藏传", "五印坛城"],
        "min_hits": 1,
    },
    {
        "case_id": "culture_fangong_art",
        "question": "灵山梵宫有哪些艺术元素",
        "expected_keywords": ["东阳木雕", "敦煌壁画", "琉璃艺术"],
        "min_hits": 1,
    },
    {
        "case_id": "culture_five_buddhas",
        "question": "五方五佛在景区哪些内容里有体现",
        "expected_keywords": ["五方五佛", "五智门", "五印坛城"],
        "min_hits": 1,
    },
    {
        "case_id": "culture_xuanzang",
        "question": "玄奘法师和灵山有什么关系",
        "expected_keywords": ["玄奘", "小灵山", "唐贞观"],
        "min_hits": 1,
    },
    {
        "case_id": "paraphrase_jiulong_schedule",
        "question": "九龙灌浴表演什么时候能看",
        "expected_keywords": ["九龙灌浴", "10:00"],
        "min_hits": 1,
    },
    {
        "case_id": "paraphrase_buddha_meaning",
        "question": "大佛有什么意义",
        "expected_keywords": ["灵山大佛", "慈悲", "智慧"],
        "min_hits": 1,
    },
    {
        "case_id": "paraphrase_easy_walk",
        "question": "我想轻松逛一下，不要太累",
        "expected_keywords": ["轻松", "半天", "路线"],
        "min_hits": 1,
    },
    {
        "case_id": "paraphrase_child_visit",
        "question": "带孩子看什么比较合适，推荐一下",
        "expected_keywords": ["亲子", "九龙灌浴", "灵山大佛"],
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
