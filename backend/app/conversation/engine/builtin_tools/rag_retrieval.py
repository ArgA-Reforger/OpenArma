"""Builtin tool: knowledge base retrieval (RAG). Lets the LLM decide on its own when to query the knowledge base."""

import logging
from typing import Any

from backend.app.conversation.engine.builtin_tools.registry import builtin_registry

log = logging.getLogger(__name__)


@builtin_registry.register(
    'rag_retrieval',
    display_name='Búsqueda en base de conocimiento',
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
    """Knowledge base retrieval: reuses the existing RAG service, but is triggered proactively by the LLM."""
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
