import uuid
from datetime import date
from functools import lru_cache

from qdrant_client import QdrantClient, models

from app.settings import get_settings

COLLECTION_NAME = "diary_chunks"
VECTOR_SIZE = 768
_POINT_ID_NAMESPACE = uuid.UUID("2f5b6b2a-9c3e-4b8e-9c0a-9a5f6d9c2b10")


@lru_cache
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=get_settings().qdrant_url)


def _point_id(diary_entry_id: uuid.UUID, chunk_index: int) -> str:
    return str(uuid.uuid5(_POINT_ID_NAMESPACE, f"{diary_entry_id}:{chunk_index}"))


def ensure_collection() -> None:
    client = get_qdrant_client()
    if client.collection_exists(COLLECTION_NAME):
        return
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="user_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )


def upsert_chunks(
    diary_entry_id: uuid.UUID,
    user_id: uuid.UUID,
    entry_date: date,
    chunks: list[str],
    vectors: list[list[float]],
) -> None:
    delete_diary_entry_points(diary_entry_id, user_id)
    if not chunks:
        return
    points = [
        models.PointStruct(
            id=_point_id(diary_entry_id, index),
            vector=vector,
            payload={
                "user_id": str(user_id),
                "diary_entry_id": str(diary_entry_id),
                "chunk_index": index,
                "chunk_text": chunk,
                "entry_date": entry_date.isoformat(),
            },
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    get_qdrant_client().upsert(collection_name=COLLECTION_NAME, points=points)


def _scoped_filter(diary_entry_id: uuid.UUID, user_id: uuid.UUID) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="diary_entry_id", match=models.MatchValue(value=str(diary_entry_id))
            ),
            models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
        ]
    )


def delete_diary_entry_points(diary_entry_id: uuid.UUID, user_id: uuid.UUID) -> None:
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        return
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(filter=_scoped_filter(diary_entry_id, user_id)),
    )


def _recency_bonus(entry_date: date, today: date, half_life_days: int) -> float:
    age_days = max((today - entry_date).days, 0)
    return 0.5 ** (age_days / half_life_days)


def _hybrid_score(
    cosine_score: float,
    entry_date: date,
    today: date,
    recency_weight: float,
    half_life_days: int,
) -> float:
    recency = _recency_bonus(entry_date, today, half_life_days)
    return (1 - recency_weight) * cosine_score + recency_weight * recency


def search(user_id: uuid.UUID, query_vector: list[float], top_k: int) -> list[models.ScoredPoint]:
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        return []
    settings = get_settings()
    candidate_pool_size = max(settings.retrieval_candidate_pool_size, top_k)
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=models.Filter(
            must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id)))]
        ),
        limit=candidate_pool_size,
    )
    today = date.today()
    ranked = sorted(
        response.points,
        key=lambda point: _hybrid_score(
            point.score,
            date.fromisoformat(point.payload["entry_date"]),
            today,
            settings.retrieval_recency_weight,
            settings.retrieval_recency_half_life_days,
        ),
        reverse=True,
    )
    return ranked[:top_k]
