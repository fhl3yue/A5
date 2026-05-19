from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    user_id: str = "guest"


class ChatData(BaseModel):
    log_id: int
    transcript: str | None = None
    interpreted_question: str | None = None
    answer: str
    audio_url: str | None = None
    video_url: str | None = None
    video_status: str = "disabled"
    emotion: str = "neutral"
    reference: list[str] = []
    response_seconds: float = 0.0


class ChatResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: ChatData


class RouteRequest(BaseModel):
    interest: str
    duration: str = "半天"


class RouteData(BaseModel):
    route_name: str
    route_spots: list[str]
    reason: str


class RouteResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: RouteData


class FeedbackRequest(BaseModel):
    log_id: int
    satisfaction: int = Field(ge=1, le=5)


class TranslateRequest(BaseModel):
    log_id: int | None = None
    text: str | None = Field(default=None, max_length=4000)
    target_language: str = Field(default="en", pattern="^(en)$")


class TranslateData(BaseModel):
    log_id: int | None = None
    target_language: str
    translation: str


class TranslateResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: TranslateData


class SimpleResponse(BaseModel):
    code: int = 0
    message: str = "success"


class KnowledgeDocumentItem(BaseModel):
    id: int
    name: str
    source: str
    status: str
    content_type: str
    chunk_count: int
    created_at: datetime


class KnowledgeChunkItem(BaseModel):
    id: int
    title: str
    content: str
    tags: str
    created_at: datetime


class KnowledgeDocumentDetailData(BaseModel):
    document: KnowledgeDocumentItem
    chunks: list[KnowledgeChunkItem]


class KnowledgeDocumentsResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: list[KnowledgeDocumentItem]


class KnowledgeDocumentDetailResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: KnowledgeDocumentDetailData


class KnowledgeDocumentUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source: str = Field(default="admin", max_length=255)
    status: str = Field(default="active", max_length=50)


class KnowledgeChunkCreateRequest(BaseModel):
    title: str = Field(default="", max_length=255)
    content: str = Field(min_length=1, max_length=3000)
    tags: str = Field(default="manual", max_length=255)


class KnowledgeChunkUpdateRequest(BaseModel):
    title: str = Field(default="", max_length=255)
    content: str = Field(min_length=1, max_length=3000)
    tags: str = Field(default="", max_length=255)


class DigitalHumanConfigData(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role_title: str = Field(min_length=1, max_length=100)
    scenic_area: str = Field(min_length=1, max_length=100)
    outfit_theme: str = Field(min_length=1, max_length=50)
    voice_name: str = Field(min_length=1, max_length=100)
    greeting: str = Field(min_length=1, max_length=300)
    avatar_asset_url: str = Field(default="/app/assets/avatar/avatar-guide-v1.png", max_length=500)
    video_provider_status: str = Field(default="外部视频 API", max_length=100)
    fallback_message: str = Field(default="数字人视频暂不可用，已切换为语音讲解。", min_length=1, max_length=300)
    service_boundary: str = Field(
        default="仅基于景区知识库进行导览讲解，不提供功德承诺、神迹保证或占卜预测。",
        min_length=1,
        max_length=500,
    )


class DigitalHumanConfigResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: DigitalHumanConfigData


class DigitalVideoStatusData(BaseModel):
    enabled: bool
    configured: bool
    avatar_id: str
    last_status: str
    last_message: str
    last_failure_reason: str
    average_response_seconds: float
    fallback_count: int
    total_requests: int


class DigitalVideoStatusResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: DigitalVideoStatusData


class RagRebuildRequest(BaseModel):
    document_name: str | None = None


class RagStatusData(BaseModel):
    enabled: bool
    configured: bool
    model_name: str
    indexed_chunks: int
    total_chunks: int
    dimension: int | None = None
    last_updated: datetime | None = None
    last_error: str = ""


class RagStatusResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: RagStatusData


class RagRebuildData(BaseModel):
    indexed: int
    skipped: int
    failed: int
    total: int
    message: str


class RagRebuildResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: RagRebuildData


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginData(BaseModel):
    username: str
    display_name: str
    token: str


class LoginResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: LoginData


class LogItem(BaseModel):
    id: int
    user_id: str
    question: str
    answer: str
    emotion: str
    satisfaction: int | None
    response_seconds: float
    source_titles: list[str]
    created_at: datetime


class LogsResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: list[LogItem]


class ChartItem(BaseModel):
    name: str
    value: int


class HotQuestionItem(BaseModel):
    name: str
    count: int


class ServiceTrendItem(BaseModel):
    date: str
    visitors: int = 0
    qa_count: int = 0


class SatisfactionTrendItem(BaseModel):
    date: str
    satisfaction_rate: float = 0.0
    rating_count: int = 0


class DashboardData(BaseModel):
    today_visitors: int
    today_qa_count: int
    satisfaction_rate: float
    hot_questions: list[HotQuestionItem]
    emotion_distribution: list[ChartItem]
    weekly_service_trend: list[ServiceTrendItem]
    satisfaction_trend: list[SatisfactionTrendItem]


class DashboardResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: DashboardData


class EmotionTrendItem(BaseModel):
    date: str
    positive: int = 0
    neutral: int = 0
    negative: int = 0


class VisitorReportData(BaseModel):
    summary: str
    focus_points: list[HotQuestionItem]
    emotion_trend: list[EmotionTrendItem]
    service_suggestions: list[str]


class VisitorReportResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: VisitorReportData
