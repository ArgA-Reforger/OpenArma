"""内置工具：联网搜索。支持 Tavily（推荐）和 DuckDuckGo（免费 fallback）。"""

import logging
from typing import Any

from backend.app.conversation.engine.builtin_tools.registry import builtin_registry

log = logging.getLogger(__name__)


async def _search_tavily(query: str, max_results: int = 5) -> str:
    """通过 Tavily API 搜索（专为 LLM 设计，返回格式化文本）。"""
    try:
        from tavily import AsyncTavilyClient
    except ImportError:
        return 'Tavily SDK not installed. Run: pip install tavily-python'

    from backend.core.conf import settings

    api_key = getattr(settings, 'TAVILY_API_KEY', None)
    if not api_key:
        return 'Tavily API key not configured (TAVILY_API_KEY).'

    client = AsyncTavilyClient(api_key=api_key)
    response = await client.search(query, max_results=max_results, search_depth='basic')

    results = response.get('results', [])
    if not results:
        return f'No search results found for: {query}'

    parts: list[str] = []
    for r in results[:max_results]:
        title = r.get('title', '')
        url = r.get('url', '')
        content = r.get('content', '')
        parts.append(f'### {title}\n{content}\nSource: {url}')

    return '\n\n'.join(parts)


async def _search_duckduckgo(query: str, max_results: int = 5) -> str:
    """通过 DuckDuckGo 搜索（免费，无需 API Key）。"""
    try:
        from duckduckgo_search import AsyncDDGS
    except ImportError:
        return 'DuckDuckGo SDK not installed. Run: pip install duckduckgo-search'

    async with AsyncDDGS() as ddgs:
        results = []
        async for r in ddgs.atext(query, max_results=max_results):
            results.append(r)

    if not results:
        return f'No search results found for: {query}'

    parts: list[str] = []
    for r in results:
        title = r.get('title', '')
        href = r.get('href', '')
        body = r.get('body', '')
        parts.append(f'### {title}\n{body}\nSource: {href}')

    return '\n\n'.join(parts)


@builtin_registry.register(
    'web_search',
    display_name='Búsqueda web',
    description=(
        'Search the internet for current information. '
        'Use this when you need up-to-date information, facts, news, '
        'or any knowledge that might not be in your training data.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'The search query to look up on the internet.',
            },
            'max_results': {
                'type': 'integer',
                'description': 'Maximum number of results to return (default: 5).',
                'default': 5,
            },
        },
        'required': ['query'],
    },
)
async def web_search(query: str, max_results: int = 5, **_: Any) -> str:
    """联网搜索：优先使用 Tavily，fallback 到 DuckDuckGo。"""
    from backend.core.conf import settings

    provider = getattr(settings, 'WEB_SEARCH_PROVIDER', 'auto')

    if provider == 'tavily' or (provider == 'auto' and getattr(settings, 'TAVILY_API_KEY', None)):
        try:
            return await _search_tavily(query, max_results)
        except Exception:
            log.exception('Tavily search failed, falling back to DuckDuckGo')

    try:
        return await _search_duckduckgo(query, max_results)
    except Exception:
        log.exception('DuckDuckGo search also failed')
        return f'Web search failed for query: {query}'
