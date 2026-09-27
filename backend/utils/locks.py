from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import anyio

from backend.core.path_conf import RELOAD_LOCK_FILE
from backend.database.redis import redis_client


@asynccontextmanager
async def acquire_distributed_reload_lock() -> AsyncGenerator[None, Any]:
    """Acquire the distributed hot-reload lock"""
    lock = redis_client.lock(
        'fba:reload_lock',
        timeout=300,  # lock hold timeout: 5 minutes
        blocking_timeout=60,  # lock acquire wait timeout: 60 seconds
    )
    await lock.acquire()

    # File lock (tells the file watcher to skip reload)
    lock_path = anyio.Path(RELOAD_LOCK_FILE)
    await lock_path.touch()

    try:
        yield
    finally:
        await lock_path.unlink(missing_ok=True)
        if await lock.owned():
            await lock.release()
