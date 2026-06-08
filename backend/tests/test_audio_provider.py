import base64
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from app.config import settings
from app.services import audio


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
            "local_tts_enabled",
            "local_tts_provider",
            "local_tts_base_url",
            "local_tts_timeout_seconds",
            "local_tts_demo_id",
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


if __name__ == "__main__":
    unittest.main()
