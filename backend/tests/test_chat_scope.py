import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import DigitalHumanConfig, ScenicSpot
from app.services.chat import answer_question


class ChatScopeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add(
            DigitalHumanConfig(
                scenic_area="灵山胜境",
                voice_name="zh-CN-XiaoxiaoNeural",
                outfit_theme="asset-avatar",
            )
        )
        self.db.add(
            ScenicSpot(
                spot_id="jiulong",
                name="九龙灌浴",
                location="灵山胜境核心区域",
                cultural_meaning="表现佛教文化中的祥瑞寓意。",
                description="九龙灌浴是灵山胜境的动态表演景点。",
                highlights="适合观看喷泉表演。",
                schedule="平日演出时间为10:00、11:30、13:30、15:00。",
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_external_weather_question_does_not_use_scenic_templates(self):
        result = answer_question(
            self.db,
            "今天徐州天气",
            user_id="scope-test",
            enqueue_audio=False,
            tts_mode="local_preferred",
        )

        self.assertEqual("out_of_scope", result["answer_source"])
        self.assertIn("没有启用联网天气查询", result["answer"])
        self.assertNotIn("九龙灌浴", result["answer"])
        self.assertTrue(result["reference"][0].startswith("超出当前景区知识库范围"))

    def test_external_scenic_question_is_rejected(self):
        result = answer_question(
            self.db,
            "故宫门票多少钱",
            user_id="scope-test",
            enqueue_audio=False,
            tts_mode="local_preferred",
        )

        self.assertEqual("out_of_scope", result["answer_source"])
        self.assertIn("外部城市或景区资料", result["answer"])

    def test_current_scenic_question_still_works(self):
        result = answer_question(
            self.db,
            "九龙灌浴几点开始表演",
            user_id="scope-test",
            enqueue_audio=False,
            tts_mode="local_preferred",
        )

        self.assertNotEqual("out_of_scope", result["answer_source"])
        self.assertIn("10:00", result["answer"])


if __name__ == "__main__":
    unittest.main()
