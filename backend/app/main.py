from pathlib import Path
import shutil
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import ensure_runtime_dirs, settings
from app.database import Base, engine, get_db
from app.models import AdminUser, QALog
from app.schemas import (
    ChatData,
    ChatRequest,
    ChatResponse,
    DashboardResponse,
    FeedbackRequest,
    LoginData,
    LoginRequest,
    LoginResponse,
    LogItem,
    LogsResponse,
    RouteData,
    RouteRequest,
    RouteResponse,
    SimpleResponse,
)
from app.services.analytics import build_dashboard
from app.services.chat import answer_question
from app.services.knowledge import import_docx_document, import_plain_text_document, import_xlsx_rows
from app.services.routes import recommend_route
from app.services.speech import transcribe_audio_file
from app.utils import refine_voice_question


ensure_runtime_dirs()
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/generated/audio", StaticFiles(directory=settings.audio_output_dir), name="generated-audio")


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "status": "ok",
        "docs": "/docs",
    }


@app.post("/api/chat/text", response_model=ChatResponse)
def chat_text(payload: ChatRequest, db: Session = Depends(get_db)):
    result = answer_question(db, payload.question, payload.user_id)
    return ChatResponse(
        data=ChatData(
            log_id=result["log_id"],
            transcript=payload.question,
            interpreted_question=payload.question,
            answer=result["answer"],
            audio_url=result["audio_url"],
            emotion=result["emotion"],
            reference=result["reference"],
            response_seconds=result["response_seconds"],
        )
    )


@app.post("/api/chat/voice", response_model=ChatResponse)
def chat_voice(
    transcript: str = Form(default=""),
    user_id: str = Form(default="guest"),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    if not transcript and file is None:
        raise HTTPException(status_code=400, detail="请提供 transcript 或音频文件。")

    derived_transcript = transcript.strip()
    temp_path: Path | None = None
    if not derived_transcript and file is not None:
        suffix = Path(file.filename or "voice_input.wav").suffix or ".wav"
        temp_path = settings.upload_temp_dir / f"voice_{uuid4().hex}{suffix}"
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        try:
            derived_transcript = transcribe_audio_file(temp_path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"语音识别失败：{exc}") from exc
        finally:
            temp_path.unlink(missing_ok=True)

    if not derived_transcript:
        raise HTTPException(status_code=400, detail="未能识别出有效语音内容，请重试或直接传 transcript。")

    interpreted_question = refine_voice_question(derived_transcript)
    result = answer_question(db, interpreted_question, user_id)
    return ChatResponse(
        data=ChatData(
            log_id=result["log_id"],
            transcript=derived_transcript,
            interpreted_question=interpreted_question,
            answer=result["answer"],
            audio_url=result["audio_url"],
            emotion=result["emotion"],
            reference=result["reference"],
            response_seconds=result["response_seconds"],
        )
    )


@app.post("/api/recommend/route", response_model=RouteResponse)
def route_recommend(payload: RouteRequest, db: Session = Depends(get_db)):
    route = recommend_route(db, payload.interest, payload.duration)
    return RouteResponse(data=RouteData(**route))


@app.post("/api/feedback", response_model=SimpleResponse)
def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    log = db.get(QALog, payload.log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="未找到对应问答记录。")
    log.satisfaction = payload.satisfaction
    db.commit()
    return SimpleResponse()


@app.post("/api/admin/login", response_model=LoginResponse)
def admin_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(AdminUser).where(AdminUser.username == payload.username)).scalar_one_or_none()
    if user is None or user.password != payload.password:
        raise HTTPException(status_code=401, detail="账号或密码错误。")
    return LoginResponse(data=LoginData(username=user.username, display_name=user.display_name, token=f"demo-token-{user.username}"))


@app.get("/api/admin/logs", response_model=LogsResponse)
def admin_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.execute(select(QALog).order_by(desc(QALog.created_at)).limit(limit)).scalars().all()
    data = [
        LogItem(
            id=item.id,
            user_id=item.user_id,
            question=item.question,
            answer=item.answer,
            emotion=item.emotion,
            satisfaction=item.satisfaction,
            response_seconds=item.response_seconds,
            source_titles=[value for value in item.source_titles.split("|") if value],
            created_at=item.created_at,
        )
        for item in logs
    ]
    return LogsResponse(data=data)


@app.get("/api/admin/dashboard", response_model=DashboardResponse)
def admin_dashboard(db: Session = Depends(get_db)):
    return DashboardResponse(data=build_dashboard(db))


@app.post("/api/admin/docs/upload", response_model=SimpleResponse)
def upload_doc(file: UploadFile = File(...), db: Session = Depends(get_db)):
    destination = settings.raw_data_dir / file.filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    suffix = Path(file.filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        import_plain_text_document(db, destination, source="upload")
    elif suffix == ".docx":
        import_docx_document(db, destination, source="upload")
    elif suffix == ".xlsx":
        import_xlsx_rows(db, destination, source="upload")
    else:
        raise HTTPException(status_code=400, detail="当前仅支持 .txt/.md/.docx/.xlsx 文件。")
    return SimpleResponse()
