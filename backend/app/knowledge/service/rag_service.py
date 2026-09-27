"""RAG retrieval service: retrieve relevant knowledge from Qdrant and inject into conversation context."""

import logging
from typing import Any

import litellm

from backend.common.qdrant_client import get_client, search_vectors

log = logging.getLogger(__name__)


def _collection_name(kb_id: int) -> str:
    return f'kb_{kb_id}'


async def retrieve_context(
    query: str,
    kb_ids: list[int],
    *,
    top_k: int = 5,
    score_threshold: float = 0.3,
    embedding_model: str = 'text-embedding-3-small',
    embedding_kwargs: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve text chunks most relevant to query from multiple knowledge bases.

    :param query: user query text
    :param kb_ids: list of knowledge base IDs to retrieve from
    :param top_k: maximum results per knowledge base
    :param score_threshold: minimum similarity threshold
    :param embedding_model: embedding model
    :param embedding_kwargs: extra keyword arguments for litellm.embedding
    :return: list of retrieval results sorted by similarity
    """
    if not kb_ids or not query.strip():
        return []

    kwargs = embedding_kwargs or {}
    try:
        response = litellm.embedding(model=embedding_model, input=[query], **kwargs)
        query_vector = response.data[0]['embedding']
    except Exception:
        log.exception('Failed to embed query for RAG')
        return []

    client = get_client()
    all_results: list[dict[str, Any]] = []

    for kb_id in kb_ids:
        collection = _collection_name(kb_id)
        if not client.collection_exists(collection):
            continue

        try:
            points = search_vectors(
                collection,
                query_vector,
                limit=top_k,
                score_threshold=score_threshold,
            )
            for point in points:
                all_results.append({
                    'text': point.payload.get('text', ''),
                    'title': point.payload.get('title', ''),
                    'score': point.score,
                    'kb_id': kb_id,
                    'doc_id': point.payload.get('doc_id'),
                    'chunk_index': point.payload.get('chunk_index'),
                })
        except Exception:
            log.exception(f'RAG search failed for collection {collection}')

    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:top_k]


def build_rag_context(results: list[dict[str, Any]], max_chars: int = 4000) -> str:
    """Format retrieval results into context text that can be injected into system prompt."""
    if not results:
        return ''

    parts = ['## Relevant Knowledge\n']
    total = 0
    for r in results:
        text = r['text']
        if total + len(text) > max_chars:
            break
        title = r.get('title', '')
        parts.append(f'### {title}\n{text}\n')
        total += len(text)

    return '\n'.join(parts)
