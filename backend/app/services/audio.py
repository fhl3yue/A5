import asyncio
from pathlib import Path
from uuid import uuid4

import edge_tts

from app.config import settings


async def _synthesize_to_file(text: str, output_path: Path, voice_name: str | None = None) -> None:
    communicate = edge_tts.Communicate(text=text[:1200], voice=voice_name or settings.tts_voice)
    await communicate.save(str(output_path))


def generate_tts_audio(text: str, voice_name: str | None = None) -> str | None:
    if not settings.enable_tts:
        return None

    output_name = f"answer_{uuid4().hex}.mp3"
    output_path = settings.audio_output_dir / output_name
    try:
        asyncio.run(_synthesize_to_file(text, output_path, voice_name))
        return f"/generated/audio/{output_name}"
    except Exception:
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        return None
