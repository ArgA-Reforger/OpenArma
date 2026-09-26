import asyncio

from asyncio import Queue

from backend.common.log import log


async def batch_dequeue(queue: Queue, max_items: int, timeout: float) -> list:
    """
    Get multiple items from an async queue

    :param queue: the `asyncio.Queue` to get items from
    :param max_items: maximum number of items to get from the queue
    :param timeout: total wait timeout (seconds)
    :return:
    """
    items = []

    async def collector() -> None:
        while len(items) < max_items:
            item = await queue.get()
            items.append(item)

    try:
        await asyncio.wait_for(collector(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    except Exception as e:
        log.error(f'Batch queue retrieval failed: {e}')

    return items
