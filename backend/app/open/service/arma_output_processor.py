"""Arma Output Processor — 强制后处理管道。

确保 AI 输出包含可解析的 JSON orders，无论用户如何自定义 Agent。
有 JSON → 提取 orders → command_pool。
没有 JSON → 返回空 orders + 原文作为 briefing。
"""

import json
import logging
import re

log = logging.getLogger(__name__)


def extract_orders_from_response(response_text: str) -> dict:
    """Extract structured orders from AI response text.

    Tries multiple strategies:
    1. Direct JSON parse
    2. Fenced code block extraction
    3. Brace-matching extraction
    4. Fallback: no orders, text as briefing

    Returns dict with keys: orders, briefing, assessment, priority_targets
    """
    if not response_text or not response_text.strip():
        return _empty_result('No AI response')

    text = response_text.strip()

    parsed = _try_parse_json(text)
    if parsed and _has_valid_orders(parsed):
        return _normalize(parsed, text)

    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if fence_match:
        parsed = _try_parse_json(fence_match.group(1).strip())
        if parsed and _has_valid_orders(parsed):
            return _normalize(parsed, text)

    brace_match = re.search(r'\{.*\}', text, re.DOTALL)
    if brace_match:
        parsed = _try_parse_json(brace_match.group(0))
        if parsed and _has_valid_orders(parsed):
            return _normalize(parsed, text)

    log.warning('No structured orders found in AI response (len=%d), using text as briefing', len(text))
    return _empty_result(text[:500])


def _try_parse_json(text: str) -> dict | None:
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def _has_valid_orders(data: dict) -> bool:
    """Check if parsed JSON has a meaningful orders list."""
    orders = data.get('orders')
    if not isinstance(orders, list):
        return False
    return True


def _normalize(data: dict, full_text: str) -> dict:
    """Normalize parsed JSON into standard format."""
    orders = data.get('orders', [])
    validated_orders = []
    for o in orders:
        if not isinstance(o, dict):
            continue
        if 'type' not in o or 'group_id' not in o:
            continue
        wps = o.get('waypoints')
        if isinstance(wps, list):
            converted = []
            for wp in wps:
                if isinstance(wp, list):
                    converted.append({'pos': wp})
                elif isinstance(wp, dict) and 'pos' in wp:
                    converted.append(wp)
            o['waypoints'] = converted
        validated_orders.append(o)

    return {
        'orders': validated_orders,
        'briefing': data.get('briefing', ''),
        'assessment': data.get('assessment', ''),
        'priority_targets': data.get('priority_targets', []),
        'raw_response': full_text,
    }


def _empty_result(briefing_text: str = '') -> dict:
    return {
        'orders': [],
        'briefing': briefing_text,
        'assessment': '',
        'priority_targets': [],
    }
