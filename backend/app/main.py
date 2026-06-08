from pathlib import Path
import shutil
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc, func, select, update
from sqlalchemy.orm import Session

from app.config import BASE_DIR, ensure_runtime_dirs, settings
from app.database import Base, engine, get_db
from app.models import AdminUser, KnowledgeChunk, KnowledgeDocument, KnowledgeEmbedding, QALog
from app.schemas import (
    AIStatusData,
    AIStatusResponse,
    AudioStatusData,
    AudioStatusResponse,
    ChatData,
    ChatRequest,
    ChatResponse,
    DashboardResponse,
    DigitalHumanConfigData,
    DigitalHumanConfigResponse,
    DigitalVideoStatusData,
    DigitalVideoStatusResponse,
    EvaluationData,
    EvaluationResponse,
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
    RagRebuildData,
    RagRebuildRequest,
    RagRebuildResponse,
    RagStatusData,
    RagStatusResponse,
    RouteData,
    RouteRequest,
    RouteResponse,
    SimpleResponse,
    TranslateData,
    TranslateRequest,
    TranslateResponse,
    VisitorReportResponse,
)
from app.services.analytics import build_dashboard, build_visitor_report
from app.services.ai_status import build_ai_status
from app.services.audio_tasks import get_audio_status, request_answer_audio
from app.services.chat import answer_question, build_translation_result
from app.services.digital_human import get_or_create_config, serialize_config, update_config
from app.services.digital_video import get_digital_video_status
from app.services.evaluation import load_latest_evaluation, run_evaluation
from app.services.knowledge import import_docx_document, import_plain_text_document, import_xlsx_rows
from app.services.rag import rag_status, rebuild_embeddings
from app.services.routes import recommend_route
from app.services.speech import transcribe_audio_file
from app.services.vision import VisionGuideError, answer_image_question, validate_image_upload
from app.utils import refine_voice_question, to_simplified_chinese


ensure_runtime_dirs()
Base.metadata.create_all(bind=engine)


def ensure_runtime_schema() -> None:
    if engine.dialect.name != "sqlite":
        return

    column_defaults = {
        "avatar_asset_url": "VARCHAR(500) DEFAULT '/app/assets/avatar/avatar-guide-v1.png'",
        "video_provider_status": "VARCHAR(100) DEFAULT '外部视频 API'",
        "fallback_message": "TEXT DEFAULT '数字人视频暂不可用，已切换为语音讲解。'",
        "service_boundary": "TEXT DEFAULT '仅基于景区知识库进行导览讲解，不提供功德承诺、神迹保证或占卜预测。'",
    }
    qa_log_defaults = {
        "audio_url": "VARCHAR(500) DEFAULT ''",
        "audio_status": "VARCHAR(20) DEFAULT 'pending'",
        "audio_ready_seconds": "FLOAT DEFAULT 0.0",
    }
    with engine.begin() as connection:
        rows = connection.exec_driver_sql("PRAGMA table_info(digital_human_configs)").fetchall()
        existing_columns = {row[1] for row in rows}
        for column_name, definition in column_defaults.items():
            if column_name not in existing_columns:
                connection.exec_driver_sql(f"ALTER TABLE digital_human_configs ADD COLUMN {column_name} {definition}")
        qa_rows = connection.exec_driver_sql("PRAGMA table_info(qa_logs)").fetchall()
        existing_qa_columns = {row[1] for row in qa_rows}
        for column_name, definition in qa_log_defaults.items():
            if column_name not in existing_qa_columns:
                connection.exec_driver_sql(f"ALTER TABLE qa_logs ADD COLUMN {column_name} {definition}")


ensure_runtime_schema()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/generated/audio", StaticFiles(directory=settings.audio_output_dir), name="generated-audio")
app.mount("/generated/avatar", StaticFiles(directory=settings.avatar_output_dir), name="generated-avatar")
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


ALLOWED_AVATAR_SUFFIXES = {".png", ".webp", ".avif", ".gif", ".jpg", ".jpeg"}


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
    result = answer_question(db, payload.question, payload.user_id, tts_mode=payload.tts_mode)
    return ChatResponse(
        data=ChatData(
            log_id=result["log_id"],
            transcript=payload.question,
            interpreted_question=payload.question,
            answer=result["answer"],
            audio_url=result["audio_url"],
            audio_status=result["audio_status"],
            english_available=result["english_available"],
            answer_source=result["answer_source"],
            model_name=result["model_name"],
            lipsync_available=result["lipsync_available"],
            tts_mode_used=result["tts_mode_used"],
            video_url=result["video_url"],
            video_status=result["video_status"],
            emotion=result["emotion"],
            reference=result["reference"],
            response_seconds=result["response_seconds"],
        )
    )


@app.post("/api/chat/voice", response_model=ChatResponse)
def chat_voice(
    transcript: str = Form(default=""),
    user_id: str = Form(default="guest"),
    tts_mode: str = Form(default="auto"),
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
    result = answer_question(db, interpreted_question, user_id, tts_mode=tts_mode)
    return ChatResponse(
        data=ChatData(
            log_id=result["log_id"],
            transcript=derived_transcript,
            interpreted_question=interpreted_question,
            answer=result["answer"],
            audio_url=result["audio_url"],
            audio_status=result["audio_status"],
            english_available=result["english_available"],
            answer_source=result["answer_source"],
            model_name=result["model_name"],
            lipsync_available=result["lipsync_available"],
            tts_mode_used=result["tts_mode_used"],
            video_url=result["video_url"],
            video_status=result["video_status"],
            emotion=result["emotion"],
            reference=result["reference"],
            response_seconds=result["response_seconds"],
        )
    )


@app.post("/api/chat/image", response_model=ChatResponse)
def chat_image(
    question: str = Form(default=""),
    user_id: str = Form(default="guest"),
    tts_mode: str = Form(default="auto"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if tts_mode not in {"auto", "local_preferred", "server_only"}:
        tts_mode = "auto"
    image_bytes = file.file.read()
    try:
        mime_type = validate_image_upload(file.filename, file.content_type, image_bytes)
    except VisionGuideError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = answer_image_question(
            db,
            image_bytes=image_bytes,
            mime_type=mime_type,
            question=question.strip(),
            user_id=user_id,
            tts_mode=tts_mode,
        )
    except VisionGuideError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.InvalidURL as exc:
        raise HTTPException(status_code=502, detail=f"多模态视觉模型连接配置异常：{exc}") from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 404:
            detail = "多模态视觉模型调用失败：当前中转未找到 GLM-4.5V 模型。"
        elif status_code == 400:
            detail = "多模态视觉模型调用失败：当前中转不接受本次图片请求参数。"
        else:
            detail = f"多模态视觉模型调用失败：{status_code}"
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"多模态视觉模型连接失败：{exc}") from exc

    interpreted_question = (
        f"图片识别：{result.get('matched_spot') or '未识别到明确景点'}。"
        f"{question.strip() or '请介绍图片中的景点'}"
    )
    return ChatResponse(
        data=ChatData(
            log_id=result["log_id"],
            transcript=question.strip() or "图片识别导览",
            interpreted_question=interpreted_question,
            answer=result["answer"],
            audio_url=result["audio_url"],
            audio_status=result["audio_status"],
            english_available=result["english_available"],
            answer_source=result["answer_source"],
            model_name=result["model_name"],
            lipsync_available=result["lipsync_available"],
            tts_mode_used=result["tts_mode_used"],
            video_url=result["video_url"],
            video_status=result["video_status"],
            emotion=result["emotion"],
            reference=result["reference"],
            response_seconds=result["response_seconds"],
            vision_summary=result["vision_summary"],
            matched_spot=result["matched_spot"],
            vision_model_name=result["vision_model_name"],
            multimodal_source=result["multimodal_source"],
        )
    )


@app.get("/api/chat/audio/{log_id}", response_model=AudioStatusResponse)
def chat_audio_status(log_id: int):
    status = get_audio_status(log_id)
    if status is None:
        raise HTTPException(status_code=404, detail="未找到对应问答记录。")
    return AudioStatusResponse(data=AudioStatusData(**status))


@app.post("/api/chat/audio/{log_id}/request", response_model=AudioStatusResponse)
def chat_audio_request(log_id: int, db: Session = Depends(get_db)):
    digital_human = get_or_create_config(db)
    status = request_answer_audio(db, log_id, digital_human.voice_name)
    if status is None:
        raise HTTPException(status_code=404, detail="鏈壘鍒板搴旈棶绛旇褰曘€?")
    return AudioStatusResponse(data=AudioStatusData(**status))


@app.post("/api/recommend/route", response_model=RouteResponse)
def route_recommend(payload: RouteRequest, db: Session = Depends(get_db)):
    route = recommend_route(db, payload.interest, payload.duration, payload.user_id)
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


@app.post("/api/chat/translate", response_model=TranslateResponse)
def chat_translate(payload: TranslateRequest, db: Session = Depends(get_db)):
    text = (payload.text or "").strip()
    if not text and payload.log_id is not None:
        log = db.get(QALog, payload.log_id)
        if log is None:
            raise HTTPException(status_code=404, detail="未找到对应问答记录。")
        text = log.answer.strip()
    if not text:
        raise HTTPException(status_code=400, detail="缺少需要翻译的文本。")

    translation_result = build_translation_result(text, payload.target_language)
    if not translation_result:
        raise HTTPException(status_code=503, detail="当前未配置英文回答服务。")

    return TranslateResponse(
        data=TranslateData(
            log_id=payload.log_id,
            target_language=payload.target_language,
            translation=translation_result["translation"],
            audio_url=translation_result["audio_url"],
        )
    )


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
            question=to_simplified_chinese(item.question),
            answer=to_simplified_chinese(item.answer),
            emotion=item.emotion,
            satisfaction=item.satisfaction,
            response_seconds=item.response_seconds,
            audio_status=(item.audio_status or "pending").strip() or "pending",
            audio_ready_seconds=float(item.audio_ready_seconds or 0.0),
            source_titles=[to_simplified_chinese(value) for value in item.source_titles.split("|") if value],
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


@app.get("/api/admin/ai/status", response_model=AIStatusResponse)
def admin_ai_status():
    return AIStatusResponse(data=AIStatusData(**build_ai_status()))


@app.get("/api/admin/evaluation/latest", response_model=EvaluationResponse)
def admin_evaluation_latest():
    return EvaluationResponse(data=EvaluationData(**load_latest_evaluation()))


@app.post("/api/admin/evaluation/run", response_model=EvaluationResponse)
def admin_evaluation_run(db: Session = Depends(get_db)):
    return EvaluationResponse(data=EvaluationData(**run_evaluation(db)))


@app.post("/api/admin/digital-human/config", response_model=DigitalHumanConfigResponse)
def update_digital_human_config(payload: DigitalHumanConfigData, db: Session = Depends(get_db)):
    config = update_config(db, payload.model_dump())
    return DigitalHumanConfigResponse(data=DigitalHumanConfigData(**serialize_config(config)))


@app.post("/api/admin/digital-human/avatar", response_model=DigitalHumanConfigResponse)
def upload_digital_human_avatar(file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_AVATAR_SUFFIXES:
        raise HTTPException(status_code=400, detail="数字人形象支持 PNG、WebP、AVIF、GIF、JPG/JPEG；透明背景优先使用 PNG、WebP、AVIF 或 GIF。")

    destination = settings.avatar_output_dir / f"digital-human-avatar-{uuid4().hex}{suffix}"
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    config = update_config(
        db,
        {
            "avatar_asset_url": f"/generated/avatar/{destination.name}",
            "outfit_theme": "asset-avatar",
        },
    )
    return DigitalHumanConfigResponse(data=DigitalHumanConfigData(**serialize_config(config)))


@app.get("/api/admin/digital-video/status", response_model=DigitalVideoStatusResponse)
def digital_video_status():
    return DigitalVideoStatusResponse(data=DigitalVideoStatusData(**get_digital_video_status()))


@app.get("/api/admin/rag/status", response_model=RagStatusResponse)
def admin_rag_status(db: Session = Depends(get_db)):
    return RagStatusResponse(data=RagStatusData(**rag_status(db)))


@app.post("/api/admin/rag/rebuild", response_model=RagRebuildResponse)
def admin_rag_rebuild(payload: RagRebuildRequest | None = None, db: Session = Depends(get_db)):
    document_name = payload.document_name.strip() if payload and payload.document_name else None
    return RagRebuildResponse(data=RagRebuildData(**rebuild_embeddings(db, document_name=document_name)))


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
        db.execute(
            update(KnowledgeEmbedding).where(KnowledgeEmbedding.document_name == old_name).values(document_name=next_name)
        )
    db.commit()
    db.refresh(document)
    return document_detail_response(db, document)


@app.delete("/api/admin/docs/{document_id}", response_model=SimpleResponse)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = get_document_or_404(db, document_id)
    db.query(KnowledgeEmbedding).filter(KnowledgeEmbedding.document_name == document.name).delete()
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
    db.query(KnowledgeEmbedding).filter(KnowledgeEmbedding.chunk_id == chunk.id).delete()
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
    db.query(KnowledgeEmbedding).filter(KnowledgeEmbedding.chunk_id == chunk.id).delete()
    db.delete(chunk)
    db.commit()
    db.refresh(document)
    return document_detail_response(db, document)
