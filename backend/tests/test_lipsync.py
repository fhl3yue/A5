import tempfile
import unittest
from pathlib import Path

from app.config import settings
from app.services import lipsync


class LipSyncProviderTests(unittest.TestCase):
    def setUp(self):
        self._original_values = {
            "audio_output_dir": settings.audio_output_dir,
            "lipsync_output_dir": settings.lipsync_output_dir,
            "enable_rhubarb_lipsync": settings.enable_rhubarb_lipsync,
            "rhubarb_bin_path": settings.rhubarb_bin_path,
            "lipsync_cache_enabled": settings.lipsync_cache_enabled,
            "lipsync_timeout_seconds": settings.lipsync_timeout_seconds,
        }
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        settings.audio_output_dir = self.root / "audio"
        settings.lipsync_output_dir = self.root / "lipsync"
        settings.audio_output_dir.mkdir(parents=True, exist_ok=True)
        settings.lipsync_output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        for name, value in self._original_values.items():
            setattr(settings, name, value)
        self.temp_dir.cleanup()

    def test_generate_lipsync_returns_disabled_when_rhubarb_is_off(self):
        audio_path = settings.audio_output_dir / "answer.mp3"
        audio_path.write_bytes(b"ID3fake")
        settings.enable_rhubarb_lipsync = False

        result = lipsync.generate_lipsync_for_audio("/generated/audio/answer.mp3")

        self.assertIsNone(result["lipsync_url"])
        self.assertEqual("disabled", result["lipsync_provider"])
        self.assertEqual(0, result["mouth_cue_count"])

    def test_generate_lipsync_writes_and_reuses_rhubarb_cache(self):
        audio_path = settings.audio_output_dir / "answer.mp3"
        audio_path.write_bytes(b"ID3fake")
        fake_rhubarb = self.root / "rhubarb.exe"
        fake_rhubarb.write_text("fake", encoding="utf-8")
        settings.enable_rhubarb_lipsync = True
        settings.rhubarb_bin_path = str(fake_rhubarb)
        settings.lipsync_cache_enabled = True

        calls = []
        original_run = lipsync.subprocess.run

        def fake_run(command, **_kwargs):
            calls.append(command)
            output_path = Path(command[command.index("-o") + 1])
            output_path.write_text(
                '{"mouthCues":[{"start":0,"end":0.12,"value":"A"},{"start":0.12,"end":0.25,"value":"E"}]}',
                encoding="utf-8",
            )

        lipsync.subprocess.run = fake_run
        try:
            first = lipsync.generate_lipsync_for_audio("/generated/audio/answer.mp3")
            second = lipsync.generate_lipsync_for_audio("/generated/audio/answer.mp3")
        finally:
            lipsync.subprocess.run = original_run

        self.assertEqual(1, len(calls))
        self.assertEqual(first["lipsync_url"], second["lipsync_url"])
        self.assertEqual("rhubarb", first["lipsync_provider"])
        self.assertEqual("rhubarb_cache", second["lipsync_provider"])
        self.assertEqual(2, first["mouth_cue_count"])
        self.assertEqual(2, second["mouth_cue_count"])


if __name__ == "__main__":
    unittest.main()
