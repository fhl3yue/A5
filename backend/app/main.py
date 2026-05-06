from pathlib import Path
import shutil
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc, func, select, update
from sqlalchemy.orm import Session

from app.config import ensure_runtime_dirs, settings
from app.database import Base, engine, get_db
from app.models import AdminUser, KnowledgeChunk, KnowledgeDocument, QALog
from app.schemas import (
    ChatData,
    ChatRequest,
    ChatResponse,
    DashboardResponse,
    DigitalHumanConfigData,
    DigitalHumanConfigResponse,
    FeedbackRequest,
    KnowledgeChunkCreateRequest,
    KnowledgeChunkItem,
    KnowledgeChunkUpdateRequest,
    KnowledgeDocumentDetailData,
    KnowledgeDocumentDetailResponse,
    KnowledgeDocumentItem,
    KnowledgeDocumentsResponse,
    KnowledgeDocumentUpdateRequest,
    LoginData,
    LoginRequest,
    LoginResponse,
    LogItem,
    LogsResponse,
    RouteData,
    RouteRequest,
    RouteResponse,
    SimpleResponse,
    VisitorReportResponse,
)
from app.services.analytics import build_dashboard, build_visitor_report
from app.services.chat import answer_question
from app.services.digital_human import get_or_create_config, serialize_config, update_config
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
frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


def document_to_item(db: Session, document: KnowledgeDocument) -> KnowledgeDocumentItem:
    chunk_count = db.execute(
        select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.document_name == document.name)
    ).scalar_one()
    return KnowledgeDocumentItem(
        id=document.id,
        name=document.name,
        source=document.source,
        status=document.status,
        content_type=document.content_type,
        chunk_count=chunk_count,
        created_at=document.created_at,
    )


def chunk_to_item(chunk: KnowledgeChunk) -> KnowledgeChunkItem:
    return KnowledgeChunkItem(
        id=chunk.id,
        title=chunk.title,
        content=chunk.content,
        tags=chunk.tags,
        created_at=chunk.created_at,
    )


def get_document_or_404(db: Session, document_id: int) -> KnowledgeDocument:
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="未找到对应知识文档。")
    return document


def get_chunk_or_404(db: Session, chunk_id: int) -> KnowledgeChunk:
    chunk = db.get(KnowledgeChunk, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="未找到对应知识片段。")
    return chunk


def document_detail_response(db: Session, document: KnowledgeDocument) -> KnowledgeDocumentDetailResponse:
    chunks = db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.document_name == document.name).order_by(KnowledgeChunk.id)
    ).scalars().all()
    return KnowledgeDocumentDetailResponse(
        data=KnowledgeDocumentDetailData(
            document=document_to_item(db, document),
            chunks=[chunk_to_item(chunk) for chunk in chunks],
        )
    )


def import_document_by_suffix(db: Session, path: Path, source: str = "upload") -> int:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return import_plain_text_document(db, path, source=source)
    if suffix == ".docx":
        return import_docx_document(db, path, source=source)
    if suffix == ".xlsx":
        return import_xlsx_rows(db, path, source=source)
    raise HTTPException(status_code=400, detail="当前仅支持 .txt/.md/.docx/.xlsx 文件。")


@app.get("/")
def root():
    if frontend_dir.exists():
        return RedirectResponse(url="/app/")
    return {
        "app": settings.app_name,
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/api/health")
def health():
    return {
        "app": settings.app_name,
        "status": "ok",
        "docs": "/docs",
        "frontend": "/app/" if frontend_dir.exists() else None,
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


@app.get("/api/digital-human/config", response_model=DigitalHumanConfigResponse)
def get_digital_human_config(db: Session = Depends(get_db)):
    config = get_or_create_config(db)
    return DigitalHumanConfigResponse(data=DigitalHumanConfigData(**serialize_config(config)))


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


@app.get("/api/admin/visitor-report", response_model=VisitorReportResponse)
def admin_visitor_report(db: Session = Depends(get_db)):
    return VisitorReportResponse(data=build_visitor_report(db))


@app.post("/api/admin/digital-human/config", response_model=DigitalHumanConfigResponse)
def update_digital_human_config(payload: DigitalHumanConfigData, db: Session = Depends(get_db)):
    config = update_config(db, payload.model_dump())
    return DigitalHumanConfigResponse(data=DigitalHumanConfigData(**serialize_config(config)))


@app.get("/api/admin/docs", response_model=KnowledgeDocumentsResponse)
def list_documents(db: Session = Depends(get_db)):
    documents = db.execute(select(KnowledgeDocument).order_by(desc(KnowledgeDocument.created_at))).scalars().all()
    return KnowledgeDocumentsResponse(data=[document_to_item(db, document) for document in documents])


@app.post("/api/admin/docs/upload", response_model=SimpleResponse)
def upload_doc(file: UploadFile = File(...), db: Session = Depends(get_db)):
    destination = settings.raw_data_dir / file.filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    import_document_by_suffix(db, destination, source="upload")
    return SimpleResponse()


@app.get("/api/admin/docs/{document_id}", response_model=KnowledgeDocumentDetailResponse)
def get_document_detail(document_id: int, db: Session = Depends(get_db)):
    document = get_document_or_404(db, document_id)
    return document_detail_response(db, document)


@app.patch("/api/admin/docs/{document_id}", response_model=KnowledgeDocumentDetailResponse)
def update_document_meta(document_id: int, payload: KnowledgeDocumentUpdateRequest, db: Session = Depends(get_db)):
    document = get_document_or_404(db, document_id)
    next_name = payload.name.strip()
    existing = db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.name == next_name, KnowledgeDocument.id != document_id)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="已存在同名知识文档。")

    old_name = document.name
    document.name = next_name
    document.source = payload.source.strip() or "admin"
    document.status = payload.status.strip() or "active"
    if old_name != next_name:
        db.execute(
            update(KnowledgeChunk).where(KnowledgeChunk.document_name == old_name).values(document_name=next_name)
        )
    db.commit()
    db.refresh(document)
    return document_detail_response(db, document)


@app.delete("/api/admin/docs/{document_id}", response_model=SimpleResponse)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = get_document_or_404(db, document_id)
    db.execute(
        update(KnowledgeChunk)
        .where(KnowledgeChunk.document_name == document.name)
        .values(document_name=f"deleted:{document.name}")
    )
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_name == f"deleted:{document.name}").delete()
    db.delete(document)
    db.commit()
    return SimpleResponse()


@app.post("/api/admin/docs/{document_id}/reimport", response_model=KnowledgeDocumentDetailResponse)
def reimport_document(document_id: int, db: Session = Depends(get_db)):
    document = get_document_or_404(db, document_id)
    source_path = settings.raw_data_dir / document.name
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="未找到原始上传文件，无法重新导入。")
    import_document_by_suffix(db, source_path, source="reimport")
    refreshed = db.execute(select(KnowledgeDocument).where(KnowledgeDocument.name == source_path.name)).scalar_one()
    return document_detail_response(db, refreshed)


@app.post("/api/admin/docs/{document_id}/chunks", response_model=KnowledgeDocumentDetailResponse)
def create_document_chunk(document_id: int, payload: KnowledgeChunkCreateRequest, db: Session = Depends(get_db)):
    document = get_document_or_404(db, document_id)
    db.add(
        KnowledgeChunk(
            document_name=document.name,
            title=payload.title.strip() or payload.content.strip()[:24],
            content=payload.content.strip(),
            tags=payload.tags.strip() or "manual",
        )
    )
    db.commit()
    return document_detail_response(db, document)


@app.patch("/api/admin/docs/chunks/{chunk_id}", response_model=KnowledgeDocumentDetailResponse)
def update_document_chunk(chunk_id: int, payload: KnowledgeChunkUpdateRequest, db: Session = Depends(get_db)):
    chunk = get_chunk_or_404(db, chunk_id)
    document = db.execute(select(KnowledgeDocument).where(KnowledgeDocument.name == chunk.document_name)).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="知识片段缺少所属文档。")
    chunk.title = payload.title.strip() or payload.content.strip()[:24]
    chunk.content = payload.content.strip()
    chunk.tags = payload.tags.strip()
    db.commit()
    db.refresh(document)
    return document_detail_response(db, document)


@app.delete("/api/admin/docs/chunks/{chunk_id}", response_model=KnowledgeDocumentDetailResponse)
def delete_document_chunk(chunk_id: int, db: Session = Depends(get_db)):
    chunk = get_chunk_or_404(db, chunk_id)
    document = db.execute(select(KnowledgeDocument).where(KnowledgeDocument.name == chunk.document_name)).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="知识片段缺少所属文档。")
    db.delete(chunk)
    db.commit()
    db.refresh(document)
    return document_detail_response(db, document)
