import unittest

from app.config import settings
from app.services import audio
from app.services.ai_status import build_ai_status


class AIStatusTtsTests(unittest.TestCase):
    def setUp(self):
        self._original_values = {
            "server_tts_provider": settings.server_tts_provider,
            "local_tts_enabled": settings.local_tts_enabled,
            "local_tts_provider": settings.local_tts_provider,
            "local_tts_base_url": settings.local_tts_base_url,
        }
        audio.reset_tts_runtime_status()

    def tearDown(self):
        for name, value in self._original_values.items():
            setattr(settings, name, value)
        audio.reset_tts_runtime_status()

    def test_ai_status_includes_local_tts_runtime_fields(self):
        settings.server_tts_provider = "auto"
        settings.local_tts_enabled = True
        settings.local_tts_provider = "moss_onnx"
        settings.local_tts_base_url = "http://127.0.0.1:18083"
        audio._set_tts_runtime_status(
            ready=True,
            provider="local_moss_onnx",
            elapsed_seconds=1.25,
        )

        status = build_ai_status()

        self.assertEqual("auto", status["server_tts_provider"])
        self.assertTrue(status["local_tts_enabled"])
        self.assertEqual("moss_onnx", status["local_tts_provider"])
        self.assertTrue(status["server_tts_ready"])
        self.assertEqual("local_moss_onnx", status["server_tts_last_provider"])
        self.assertEqual(1.25, status["server_tts_last_elapsed_seconds"])


if __name__ == "__main__":
    unittest.main()
