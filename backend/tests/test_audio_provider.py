import base64
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from app.config import settings
from app.services import audio
from app.services.audio_tasks import build_spoken_answer_text


FAKE_WAV_BYTES = b"RIFF\x24\x00\x00\x00WAVEfmt "


class _FakeMossHandler(BaseHTTPRequestHandler):
    request_path = ""
    request_body = b""

    def log_message(self, _format, *args):
        return

    def do_GET(self):
        if self.path == "/health":
            payload = json.dumps({"status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        type(self).request_path = self.path
        length = int(self.headers.get("Content-Length", "0"))
        type(self).request_body = self.rfile.read(length)
        payload = json.dumps(
            {
                "audio_base64": base64.b64encode(FAKE_WAV_BYTES).decode("ascii"),
                "sample_rate": 48000,
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class AudioProviderTests(unittest.TestCase):
    def setUp(self):
        self._original_values = {
            "audio_output_dir": settings.audio_output_dir,
            "enable_tts": settings.enable_tts,
        }
        for name in (
            "server_tts_provider",
            "edge_tts_cache_enabled",
            "edge_tts_cache_max_items",
            "edge_tts_cache_version",
            "local_tts_enabled",
            "local_tts_provider",
            "local_tts_base_url",
            "local_tts_timeout_seconds",
            "local_tts_demo_id",
            "tts_voice",
            "tts_max_chars",
        ):
            self._original_values[name] = getattr(settings, name, None)
        self.temp_dir = tempfile.TemporaryDirectory()
        settings.audio_output_dir = Path(self.temp_dir.name)
        settings.audio_output_dir.mkdir(parents=True, exist_ok=True)
        settings.enable_tts = True
        audio.reset_tts_runtime_status()

    def tearDown(self):
        for name, value in self._original_values.items():
            if value is None and hasattr(settings, name):
                delattr(settings, name)
            else:
                setattr(settings, name, value)
        audio.reset_tts_runtime_status()
        self.temp_dir.cleanup()

    def _run_fake_moss_server(self):
        server = HTTPServer(("127.0.0.1", 0), _FakeMossHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def test_generate_tts_audio_uses_local_moss_provider_when_available(self):
        server = self._run_fake_moss_server()
        try:
            settings.server_tts_provider = "auto"
            settings.local_tts_enabled = True
            settings.local_tts_provider = "moss_onnx"
            settings.local_tts_base_url = f"http://127.0.0.1:{server.server_port}"
            settings.local_tts_timeout_seconds = 2.0
            settings.local_tts_demo_id = "demo-1"
            settings.edge_tts_cache_enabled = False

            audio_url = audio.generate_tts_audio("欢迎来到灵山胜境。", enabled=True)

            self.assertIsNotNone(audio_url)
            self.assertTrue(audio_url.endswith(".wav"))
            self.assertEqual("/api/generate", _FakeMossHandler.request_path)
            self.assertIn(b"demo-1", _FakeMossHandler.request_body)
            output_path = settings.audio_output_dir / Path(audio_url).name
            self.assertEqual(FAKE_WAV_BYTES, output_path.read_bytes())
            status = audio.get_tts_runtime_status()
            self.assertTrue(status["server_tts_ready"])
            self.assertEqual("local_moss_onnx", status["last_provider"])
            self.assertEqual("", status["last_error"])
        finally:
            server.shutdown()
            server.server_close()

    def test_generate_tts_audio_falls_back_to_edge_when_local_provider_fails(self):
        async def fake_edge_synthesize(_text, output_path, _voice_name=None):
            output_path.write_bytes(b"ID3edge")

        original_edge = audio._synthesize_to_file
        audio._synthesize_to_file = fake_edge_synthesize
        try:
            settings.server_tts_provider = "auto"
            settings.local_tts_enabled = True
            settings.local_tts_provider = "moss_onnx"
            settings.local_tts_base_url = "http://127.0.0.1:9"
            settings.local_tts_timeout_seconds = 0.2
            settings.local_tts_demo_id = "demo-1"
            settings.edge_tts_cache_enabled = False

            audio_url = audio.generate_tts_audio("本地失败时应该回退。", enabled=True)

            self.assertIsNotNone(audio_url)
            self.assertTrue(audio_url.endswith(".mp3"))
            output_path = settings.audio_output_dir / Path(audio_url).name
            self.assertEqual(b"ID3edge", output_path.read_bytes())
            status = audio.get_tts_runtime_status()
            self.assertTrue(status["server_tts_ready"])
            self.assertEqual("edge_tts", status["last_provider"])
            self.assertEqual("", status["last_error"])
        finally:
            audio._synthesize_to_file = original_edge

    def test_edge_tts_cache_reuses_same_text_voice_and_version(self):
        calls = []

        async def fake_edge_synthesize(_text, output_path, voice_name=None):
            calls.append(voice_name)
            output_path.write_bytes(b"ID3cached")

        original_edge = audio._synthesize_to_file
        audio._synthesize_to_file = fake_edge_synthesize
        try:
            settings.server_tts_provider = "edge"
            settings.local_tts_enabled = False
            settings.edge_tts_cache_enabled = True
            settings.edge_tts_cache_max_items = 300
            settings.edge_tts_cache_version = "test-v1"
            settings.tts_voice = "zh-CN-XiaoxiaoNeural"

            first_url = audio.generate_tts_audio("同一个问题应该命中缓存。", enabled=True)
            first_status = audio.get_tts_runtime_status()
            second_url = audio.generate_tts_audio("同一个问题应该命中缓存。", enabled=True)
            second_status = audio.get_tts_runtime_status()

            self.assertEqual(first_url, second_url)
            self.assertEqual(1, len(calls))
            self.assertIn("/generated/audio/cache/edge_", first_url)
            self.assertEqual("edge_tts", first_status["last_provider"])
            self.assertFalse(first_status["edge_tts_cache_last_hit"])
            self.assertEqual("edge_tts_cache", second_status["last_provider"])
            self.assertTrue(second_status["edge_tts_cache_last_hit"])
            self.assertEqual(1, second_status["edge_tts_cache_items"])
            output_path = settings.audio_output_dir / "cache" / Path(first_url).name
            self.assertEqual(b"ID3cached", output_path.read_bytes())
        finally:
            audio._synthesize_to_file = original_edge

    def test_edge_tts_cache_separates_different_voices(self):
        calls = []

        async def fake_edge_synthesize(_text, output_path, voice_name=None):
            calls.append(voice_name)
            output_path.write_bytes(f"ID3{voice_name}".encode("utf-8"))

        original_edge = audio._synthesize_to_file
        audio._synthesize_to_file = fake_edge_synthesize
        try:
            settings.server_tts_provider = "edge"
            settings.local_tts_enabled = False
            settings.edge_tts_cache_enabled = True
            settings.edge_tts_cache_max_items = 300
            settings.edge_tts_cache_version = "test-v1"

            first_url = audio.generate_tts_audio("同一句话换音色不能复用旧音频。", "voice-a", enabled=True)
            second_url = audio.generate_tts_audio("同一句话换音色不能复用旧音频。", "voice-b", enabled=True)

            self.assertNotEqual(first_url, second_url)
            self.assertEqual(["voice-a", "voice-b"], calls)
            status = audio.get_tts_runtime_status()
            self.assertEqual(2, status["edge_tts_cache_items"])
        finally:
            audio._synthesize_to_file = original_edge

    def test_build_spoken_answer_text_shortens_long_answer_and_removes_metadata(self):
        long_answer = (
            "灵山胜境位于无锡太湖之滨，核心景点包括灵山大佛、九龙灌浴、灵山梵宫等。"
            "如果你只有半天时间，建议先看九龙灌浴，再参观灵山大佛，最后根据体力选择梵宫。"
            "这条路线能兼顾标志性景观、佛教文化和演出体验，步行压力也比较可控。"
            "\n参考来源：灵山胜境知识库"
        )

        spoken_text = build_spoken_answer_text(long_answer)

        self.assertLessEqual(len(spoken_text), 121)
        self.assertIn("灵山胜境", spoken_text)
        self.assertNotIn("参考来源", spoken_text)
        self.assertTrue(spoken_text.endswith("。"))


if __name__ == "__main__":
    unittest.main()
