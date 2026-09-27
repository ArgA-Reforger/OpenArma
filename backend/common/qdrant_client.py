"""Qdrant client wrapper, providing vector collection management and retrieval operations."""

from qdrant_client import QdrantClient, models

from backend.core.conf import settings

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY or None,
        )
    return _client


def ensure_collection(collection_name: str, vector_size: int = 1536) -> None:
    """Ensure the Qdrant collection exists, creating it if it does not."""
    client = get_client()
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )


def delete_collection(collection_name: str) -> None:
    client = get_client()
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)


def upsert_vectors(
    collection_name: str,
    ids: list[str],
    vectors: list[list[float]],
    payloads: list[dict],
) -> None:
    """Batch write vectors to Qdrant."""
    client = get_client()
    points = [
        models.PointStruct(id=id_, vector=vec, payload=payload)
        for id_, vec, payload in zip(ids, vectors, payloads)
    ]
    client.upsert(collection_name=collection_name, points=points)


def search_vectors(
    collection_name: str,
    query_vector: list[float],
    limit: int = 5,
    score_threshold: float | None = None,
    filter_conditions: models.Filter | None = None,
) -> list[models.ScoredPoint]:
    """Semantic search: return the most similar vectors."""
    client = get_client()
    return client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit,
        score_threshold=score_threshold,
        query_filter=filter_conditions,
    ).points


def delete_vectors_by_filter(collection_name: str, filter_conditions: models.Filter) -> None:
    client = get_client()
    client.delete(collection_name=collection_name, points_selector=filter_conditions)
