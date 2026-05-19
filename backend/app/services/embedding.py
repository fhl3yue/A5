import hashlib
import time

import httpx

from app.config import settings
from app.utils import normalize_text


def embedding_configured() -> bool:
    return bool(
        settings.embedding_api_key.strip()
        and settings.embedding_base_url.strip()
        and settings.embedding_model.strip()
    )


def content_hash(text: str) -> str:
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _embedding_endpoint() -> str:
    return settings.embedding_base_url.rstrip("/") + "/embeddings"


def _request_embeddings(inputs: list[str]) -> list[list[float]]:
    payload = {
        "model": settings.embedding_model,
        "input": inputs,
    }
    headers = {"Authorization": f"Bearer {settings.embedding_api_key.strip()}"}

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = httpx.post(_embedding_endpoint(), json=payload, headers=headers, timeout=45.0)
            response.raise_for_status()
            body = response.json()
            vectors = [item["embedding"] for item in body.get("data", [])]
            if len(vectors) != len(inputs):
                raise ValueError("embedding response count mismatch")
            return [[float(value) for value in vector] for vector in vectors]
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"embedding request failed: {last_error}")


def embed_texts(texts: list[str], batch_size: int = 16) -> list[list[float]]:
    if not embedding_configured() or not texts:
        return []

    cleaned = [normalize_text(text) for text in texts]
    vectors: list[list[float]] = []
    for start in range(0, len(cleaned), batch_size):
        batch = cleaned[start : start + batch_size]
        vectors.extend(_request_embeddings(batch))
    return vectors


def embed_text(text: str) -> list[float] | None:
    vectors = embed_texts([text], batch_size=1)
    return vectors[0] if vectors else None
