"""RAG 检索服务：从 Qdrant 检索相关知识，注入对话上下文。"""

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
    从多个知识库中检索与 query 最相关的文本块。

    :param query: 用户查询文本
    :param kb_ids: 要检索的知识库 ID 列表
    :param top_k: 每个知识库返回的最大结果数
    :param score_threshold: 最低相似度阈值
    :param embedding_model: Embedding 模型
    :param embedding_kwargs: 传给 litellm.embedding 的额外参数
    :return: 按相似度排序的检索结果列表
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
    """将检索结果格式化为可注入 system prompt 的上下文文本。"""
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
