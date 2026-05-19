import json
import math
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeChunk, KnowledgeDocument, KnowledgeEmbedding, ScenicSpot
from app.services.embedding import content_hash, embed_text, embed_texts, embedding_configured
from app.utils import looks_garbled, normalize_text, overlap_score


STRUCTURAL_NOISE_HINTS = ("字段规范", "字段说明", "数据集", "结构化数据", "景点ID", "具体位置", "景区名称、")


def build_chunk_text(chunk: KnowledgeChunk) -> str:
    return normalize_text(f"{chunk.title} {chunk.tags} {chunk.content}")


def _active_document_names(db: Session) -> set[str]:
    rows = db.execute(select(KnowledgeDocument.name).where(KnowledgeDocument.status == "active")).all()
    return {name for (name,) in rows}


def _current_spot_names(db: Session) -> list[str]:
    return [item.name for item in db.execute(select(ScenicSpot)).scalars().all()]


def _is_structural_noise(chunk: KnowledgeChunk) -> bool:
    text = f"{chunk.document_name} {chunk.title} {chunk.content} {chunk.tags}"
    if looks_garbled(chunk.title):
        return True
    return any(token in text for token in STRUCTURAL_NOISE_HINTS)


def _belongs_to_current_scenic(chunk: KnowledgeChunk, scenic_area: str, spot_names: list[str]) -> bool:
    text = f"{chunk.document_name} {chunk.title} {chunk.content} {chunk.tags}"
    if chunk.document_name == "sample_scenic_spots":
        return True
    if scenic_area and scenic_area in text:
        return True
    return any(name in text for name in spot_names)


def _valid_chunks(db: Session, document_name: str | None = None, scenic_area: str = "") -> list[KnowledgeChunk]:
    active_docs = _active_document_names(db)
    statement = select(KnowledgeChunk)
    if document_name:
        statement = statement.where(KnowledgeChunk.document_name == document_name)
    chunks = db.execute(statement).scalars().all()
    chunks = [
        chunk
        for chunk in chunks
        if (not active_docs or chunk.document_name in active_docs) and not _is_structural_noise(chunk)
    ]

    spot_names = _current_spot_names(db)
    if scenic_area or spot_names:
        chunks = [chunk for chunk in chunks if _belongs_to_current_scenic(chunk, scenic_area, spot_names)]
    return chunks


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _keyword_rank(question: str, chunks: list[KnowledgeChunk], limit: int) -> list[tuple[KnowledgeChunk, float]]:
    ranked = []
    for chunk in chunks:
        score = overlap_score(question, f"{chunk.title} {chunk.content} {chunk.tags}")
        if score > 0:
            ranked.append((chunk, score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:limit]


def _upsert_embedding(
    db: Session,
    chunk: KnowledgeChunk,
    hash_value: str,
    vector: list[float],
    last_error: str = "",
) -> None:
    row = db.execute(select(KnowledgeEmbedding).where(KnowledgeEmbedding.chunk_id == chunk.id)).scalar_one_or_none()
    vector_json = json.dumps(vector, ensure_ascii=False)
    if row is None:
        db.add(
            KnowledgeEmbedding(
                chunk_id=chunk.id,
                document_name=chunk.document_name,
                title=chunk.title,
                content_hash=hash_value,
                vector_json=vector_json,
                dimension=len(vector),
                model_name=settings.embedding_model,
                last_error=last_error,
            )
        )
        return

    row.document_name = chunk.document_name
    row.title = chunk.title
    row.content_hash = hash_value
    row.vector_json = vector_json
    row.dimension = len(vector)
    row.model_name = settings.embedding_model
    row.last_error = last_error
    row.updated_at = datetime.utcnow()


def _record_embedding_error(db: Session, chunk: KnowledgeChunk, hash_value: str, message: str) -> None:
    row = db.execute(select(KnowledgeEmbedding).where(KnowledgeEmbedding.chunk_id == chunk.id)).scalar_one_or_none()
    if row is None:
        db.add(
            KnowledgeEmbedding(
                chunk_id=chunk.id,
                document_name=chunk.document_name,
                title=chunk.title,
                content_hash=hash_value,
                vector_json="[]",
                dimension=0,
                model_name=settings.embedding_model,
                last_error=message[:1000],
            )
        )
        return

    row.document_name = chunk.document_name
    row.title = chunk.title
    row.content_hash = hash_value
    row.vector_json = "[]"
    row.dimension = 0
    row.model_name = settings.embedding_model
    row.last_error = message[:1000]
    row.updated_at = datetime.utcnow()


def rebuild_embeddings(db: Session, document_name: str | None = None) -> dict:
    chunks = _valid_chunks(db, document_name=document_name)
    total = len(chunks)
    if not settings.enable_rag:
        return {"indexed": 0, "skipped": 0, "failed": 0, "total": total, "message": "RAG 已关闭。"}
    if not embedding_configured():
        return {
            "indexed": 0,
            "skipped": 0,
            "failed": total,
            "total": total,
            "message": "未配置 EMBEDDING_API_KEY，已保留关键词检索降级能力。",
        }

    existing_rows = {
        row.chunk_id: row
        for row in db.execute(select(KnowledgeEmbedding).where(KnowledgeEmbedding.model_name == settings.embedding_model))
        .scalars()
        .all()
    }
    pending: list[tuple[KnowledgeChunk, str, str]] = []
    skipped = 0
    for chunk in chunks:
        text = build_chunk_text(chunk)
        hash_value = content_hash(text)
        existing = existing_rows.get(chunk.id)
        if existing and existing.content_hash == hash_value and existing.dimension > 0 and existing.vector_json != "[]":
            skipped += 1
            continue
        pending.append((chunk, text, hash_value))

    indexed = 0
    failed = 0
    for start in range(0, len(pending), 16):
        batch = pending[start : start + 16]
        texts = [item[1] for item in batch]
        try:
            vectors = embed_texts(texts, batch_size=16)
            if len(vectors) != len(batch):
                raise RuntimeError("embedding 返回数量与知识片段数量不一致")
            for (chunk, _text, hash_value), vector in zip(batch, vectors):
                _upsert_embedding(db, chunk, hash_value, vector)
                indexed += 1
            db.commit()
        except Exception as exc:
            failed += len(batch)
            message = str(exc)
            for chunk, _text, hash_value in batch:
                _record_embedding_error(db, chunk, hash_value, message)
            db.commit()

    return {
        "indexed": indexed,
        "skipped": skipped,
        "failed": failed,
        "total": total,
        "message": f"向量索引重建完成：新增/更新 {indexed} 条，跳过 {skipped} 条，失败 {failed} 条。",
    }


def rag_status(db: Session) -> dict:
    chunks = _valid_chunks(db)
    chunk_by_id = {chunk.id: chunk for chunk in chunks}
    rows = db.execute(select(KnowledgeEmbedding)).scalars().all()
    valid_rows = []
    error_rows = []
    for row in rows:
        chunk = chunk_by_id.get(row.chunk_id)
        if row.last_error:
            error_rows.append(row)
        if not chunk:
            continue
        if row.model_name != settings.embedding_model or row.dimension <= 0:
            continue
        if row.content_hash != content_hash(build_chunk_text(chunk)):
            continue
        valid_rows.append(row)

    valid_rows.sort(key=lambda item: item.updated_at or datetime.min, reverse=True)
    error_rows.sort(key=lambda item: item.updated_at or datetime.min, reverse=True)
    latest = valid_rows[0] if valid_rows else None
    last_error = error_rows[0].last_error if error_rows else ""
    if not embedding_configured():
        last_error = last_error or "未配置 EMBEDDING_API_KEY，当前会自动降级为关键词检索。"

    return {
        "enabled": settings.enable_rag,
        "configured": embedding_configured(),
        "model_name": settings.embedding_model,
        "indexed_chunks": len(valid_rows),
        "total_chunks": len(chunks),
        "dimension": latest.dimension if latest else None,
        "last_updated": latest.updated_at if latest else None,
        "last_error": last_error,
    }


def retrieve_rag_chunks(db: Session, question: str, scenic_area: str, top_k: int | None = None) -> list[KnowledgeChunk]:
    limit = max(1, top_k or settings.rag_top_k or 5)
    chunks = _valid_chunks(db, scenic_area=scenic_area)
    if not chunks:
        return []

    keyword_ranked = _keyword_rank(question, chunks, limit=max(limit * 2, 8))
    if not settings.enable_rag or not embedding_configured():
        return [chunk for chunk, _score in keyword_ranked[:limit]]

    try:
        query_vector = embed_text(question)
    except Exception:
        query_vector = None
    if not query_vector:
        return [chunk for chunk, _score in keyword_ranked[:limit]]

    chunk_by_id = {chunk.id: chunk for chunk in chunks}
    rows = db.execute(
        select(KnowledgeEmbedding).where(KnowledgeEmbedding.chunk_id.in_(list(chunk_by_id.keys())))
    ).scalars().all()
    scores: dict[int, float] = {}
    for row in rows:
        chunk = chunk_by_id.get(row.chunk_id)
        if chunk is None or row.model_name != settings.embedding_model or row.dimension <= 0:
            continue
        if row.content_hash != content_hash(build_chunk_text(chunk)):
            continue
        try:
            vector = json.loads(row.vector_json)
        except json.JSONDecodeError:
            continue
        similarity = _cosine_similarity(query_vector, [float(value) for value in vector])
        if similarity > 0:
            scores[chunk.id] = similarity

    for chunk, keyword_score in keyword_ranked:
        bonus = min(keyword_score, 2.0) * 0.05
        scores[chunk.id] = scores.get(chunk.id, 0.0) + bonus

    ranked_ids = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)
    return [chunk_by_id[chunk_id] for chunk_id in ranked_ids[:limit] if chunk_id in chunk_by_id]
