"""内置工具：知识库检索（RAG）。让 LLM 自主决定何时查询知识库。"""

import logging
from typing import Any

from backend.app.conversation.engine.builtin_tools.registry import builtin_registry

log = logging.getLogger(__name__)


@builtin_registry.register(
    'rag_retrieval',
    display_name='知识库检索',
    description=(
        'Search the project knowledge base for relevant information. '
        'Use this when you need to look up specific facts, documents, '
        'or domain knowledge that might be stored in the knowledge base. '
        'This searches through uploaded documents and returns relevant excerpts.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'The search query to find relevant knowledge.',
            },
        },
        'required': ['query'],
    },
)
async def rag_retrieval(query: str, _context: dict | None = None, **_: Any) -> str:
    """知识库检索：复用现有 RAG 服务，但由 LLM 主动触发。"""
    if not _context:
        return 'No project context available for knowledge retrieval.'

    kb_ids = _context.get('kb_ids', [])
    if not kb_ids:
        return 'No knowledge bases are bound to this project.'

    try:
        from backend.app.knowledge.service.rag_service import build_rag_context, retrieve_context

        results = await retrieve_context(query, kb_ids)
        if not results:
            return f'No relevant knowledge found for: {query}'

        return build_rag_context(results)
    except Exception:
        log.exception('RAG retrieval tool failed')
        return f'Knowledge retrieval failed for query: {query}'
