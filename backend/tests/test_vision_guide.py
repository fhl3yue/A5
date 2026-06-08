import unittest
from unittest.mock import Mock, patch

from app.config import settings
from app.services.ai_status import build_ai_status
from app.services.vision import (
    _extract_message_text,
    build_vision_messages,
    call_vision_model,
    select_allowed_spot,
    vision_model_configured,
    vision_model_display_name,
)


class VisionGuideTests(unittest.TestCase):
    def setUp(self):
        self._original_values = {
            "enable_vision_guide": settings.enable_vision_guide,
            "vision_model_api_key": settings.vision_model_api_key,
            "vision_model_base_url": settings.vision_model_base_url,
            "vision_model_name": settings.vision_model_name,
        }

    def tearDown(self):
        for name, value in self._original_values.items():
            setattr(settings, name, value)

    def test_vision_model_configured_requires_independent_key(self):
        settings.enable_vision_guide = True
        settings.vision_model_api_key = ""
        settings.vision_model_base_url = "https://api.edgefn.net/v1"
        settings.vision_model_name = "GLM-4.5V"

        self.assertFalse(vision_model_configured())

        settings.vision_model_api_key = "sk-test"

        self.assertTrue(vision_model_configured())
        self.assertEqual("GLM-4.5V", vision_model_display_name())

    def test_select_allowed_spot_only_returns_current_scenic_spot(self):
        spot_names = ["灵山大佛", "九龙灌浴", "灵山梵宫"]

        self.assertEqual("灵山大佛", select_allowed_spot("图片可能是灵山大佛", spot_names))
        self.assertEqual("", select_allowed_spot("图片可能是高家庄", spot_names))

    def test_build_vision_messages_include_image_url_and_spot_choices(self):
        messages = build_vision_messages(
            scenic_area="灵山胜境",
            spot_names=["灵山大佛", "九龙灌浴"],
            data_url="data:image/png;base64,AAAA",
            question="这是哪里？",
        )

        self.assertEqual("system", messages[0]["role"])
        self.assertIn("灵山胜境", messages[0]["content"])
        self.assertEqual("user", messages[1]["role"])
        self.assertEqual("text", messages[1]["content"][0]["type"])
        self.assertIn("灵山大佛、九龙灌浴", messages[1]["content"][0]["text"])
        self.assertEqual("image_url", messages[1]["content"][1]["type"])
        self.assertEqual("data:image/png;base64,AAAA", messages[1]["content"][1]["image_url"]["url"])

    def test_extract_message_text_does_not_leak_reasoning_content(self):
        body = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning_content": "内部推理内容不应展示给游客",
                    }
                }
            ]
        }

        self.assertEqual("", _extract_message_text(body))

    def test_call_vision_model_disables_environment_proxy(self):
        settings.enable_vision_guide = True
        settings.vision_model_api_key = "sk-test"
        settings.vision_model_base_url = "https://api.edgefn.net/v1"
        settings.vision_model_name = "GLM-4.5V"
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": "{}"}}]}
        response.raise_for_status.return_value = None

        with patch("app.services.vision.httpx.post", return_value=response) as post:
            self.assertEqual("{}", call_vision_model([{"role": "user", "content": "test"}]))

        self.assertFalse(post.call_args.kwargs["trust_env"])

    def test_ai_status_includes_vision_fields(self):
        settings.enable_vision_guide = True
        settings.vision_model_api_key = "sk-test"
        settings.vision_model_base_url = "https://api.edgefn.net/v1"
        settings.vision_model_name = "GLM-4.5V"

        status = build_ai_status()

        self.assertTrue(status["vision_enabled"])
        self.assertTrue(status["vision_configured"])
        self.assertEqual("GLM-4.5V", status["vision_model_name"])


if __name__ == "__main__":
    unittest.main()
