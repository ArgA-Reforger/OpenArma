"""Tile generation progress tracking via Redis.

Rendering runs in a thread (asyncio.to_thread) so we need a sync Redis
client for writes. The async redis_client is used for reads from the
FastAPI endpoint.
"""

from __future__ import annotations

import json

import redis

from backend.core.conf import settings

PROGRESS_KEY_PREFIX = 'tile_gen'
PROGRESS_TTL = 600


def _sync_redis() -> redis.Redis:
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DATABASE,
        socket_timeout=5,
        decode_responses=True,
    )


def progress_key(map_id: int, layer: str) -> str:
    return f'{PROGRESS_KEY_PREFIX}:{map_id}:{layer}'


def set_progress(map_id: int, layer: str, done: int, total: int, status: str = 'running') -> None:
    """Write progress from a sync rendering thread."""
    r = _sync_redis()
    try:
        r.setex(
            progress_key(map_id, layer),
            PROGRESS_TTL,
            json.dumps({'done': done, 'total': total, 'status': status, 'layer': layer}),
        )
    finally:
        r.close()


def clear_progress(map_id: int, layer: str) -> None:
    r = _sync_redis()
    try:
        r.delete(progress_key(map_id, layer))
    finally:
        r.close()


async def get_all_progress(map_id: int) -> dict[str, dict]:
    """Read all progress keys for a map (async, for FastAPI endpoint)."""
    from backend.database.redis import redis_client

    prefix = f'{PROGRESS_KEY_PREFIX}:{map_id}:'
    result: dict[str, dict] = {}
    async for key in redis_client.scan_iter(match=f'{prefix}*', count=50):
        raw = await redis_client.get(key)
        if raw:
            data = json.loads(raw)
            result[data.get('layer', key.split(':')[-1])] = data
    return result
