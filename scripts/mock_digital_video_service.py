import os
import time

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel


class DigitalVideoRequest(BaseModel):
    request_id: str
    avatar_id: str
    text: str
    audio_url: str | None = None
    max_wait_seconds: int = 8


app = FastAPI(title="Mock Digital Video Service")


@app.post("/api/digital-video/generate")
def generate_video(payload: DigitalVideoRequest, authorization: str | None = Header(default=None)):
    expected_token = os.environ.get("MOCK_DIGITAL_VIDEO_API_KEY", "")
    if expected_token and authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=401, detail="invalid token")

    delay = float(os.environ.get("MOCK_DIGITAL_VIDEO_DELAY_SECONDS", "0"))
    if delay > 0:
        time.sleep(delay)

    status = os.environ.get("MOCK_DIGITAL_VIDEO_STATUS", "ready").strip().lower()
    if status == "error":
        raise HTTPException(status_code=500, detail="mock error")
    if status == "timeout":
        time.sleep(max(payload.max_wait_seconds + 2, 2))

    if status == "ready":
        return {
            "status": "ready",
            "video_url": f"https://video.example.com/{payload.request_id}.mp4",
            "message": "mock ready",
        }
    return {
        "status": status or "processing",
        "video_url": None,
        "message": "mock non-ready status",
    }
