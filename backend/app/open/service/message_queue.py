"""Arma 消息池：Redis 队列 + 分布式锁。

态势报告和人类消息入队 → AI 处理时出队合并 → 确保不丢失堆积期间的变化。
"""

import json
import logging
import time

from backend.database.redis import redis_client

log = logging.getLogger(__name__)

QUEUE_PREFIX = 'arma:queue:'
LOCK_PREFIX = 'arma:lock:'
LOCK_TTL = 120
QUEUE_TTL = 3600


def _queue_key(conversation_id: str) -> str:
    return f'{QUEUE_PREFIX}{conversation_id}'


def _lock_key(conversation_id: str) -> str:
    return f'{LOCK_PREFIX}{conversation_id}'


async def enqueue_situation(
    conversation_id: str,
    request_id: int,
    situation_data: dict,
    priority: str = 'normal',
) -> int:
    """Push a situation report into the queue. Returns queue length."""
    payload = json.dumps({
        'request_id': request_id,
        'situation_data': situation_data,
        'priority': priority,
        'enqueued_at': time.time(),
    }, ensure_ascii=False)

    key = _queue_key(conversation_id)

    if priority == 'critical':
        await redis_client.lpush(key, payload)
    else:
        await redis_client.rpush(key, payload)

    await redis_client.expire(key, QUEUE_TTL)
    length = await redis_client.llen(key)
    log.info('Enqueued situation #%s for conv=%s, priority=%s, queue_len=%s',
             request_id, conversation_id, priority, length)
    return length


async def dequeue_all(conversation_id: str) -> list[dict]:
    """Pop all queued items. Returns list of payloads (oldest first, critical at head)."""
    key = _queue_key(conversation_id)
    items = []

    while True:
        raw = await redis_client.lpop(key)
        if raw is None:
            break
        try:
            items.append(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            log.warning('Skipped malformed queue item for conv=%s', conversation_id)

    return items


async def merge_situations(items: list[dict]) -> dict | None:
    """Merge multiple queued situation reports into a single comprehensive one.

    Strategy: use the latest situation_data as the base (freshest positions),
    but accumulate all human_messages from all reports.
    """
    if not items:
        return None

    latest = items[-1]
    merged = latest['situation_data'].copy()

    all_human_msgs: list[dict] = []
    seen_texts: set[str] = set()
    for item in items:
        for hm in item['situation_data'].get('human_messages', []):
            text = hm.get('text', '')
            if text and text not in seen_texts:
                all_human_msgs.append(hm)
                seen_texts.add(text)
    merged['human_messages'] = all_human_msgs

    highest_priority = 'normal'
    for item in items:
        if item.get('priority') == 'critical':
            highest_priority = 'critical'
            break

    return {
        'request_id': latest['request_id'],
        'situation_data': merged,
        'priority': highest_priority,
        'merged_count': len(items),
    }


async def acquire_lock(conversation_id: str) -> bool:
    """Try to acquire processing lock. Returns True if acquired."""
    key = _lock_key(conversation_id)
    acquired = await redis_client.set(key, '1', ex=LOCK_TTL, nx=True)
    return bool(acquired)


async def release_lock(conversation_id: str) -> None:
    """Release the processing lock."""
    key = _lock_key(conversation_id)
    await redis_client.delete(key)


async def is_locked(conversation_id: str) -> bool:
    """Check if a processing lock exists."""
    key = _lock_key(conversation_id)
    return bool(await redis_client.exists(key))


async def get_queue_length(conversation_id: str) -> int:
    key = _queue_key(conversation_id)
    return await redis_client.llen(key)
