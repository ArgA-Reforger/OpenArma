import functools

from collections.abc import Callable, Sequence
from typing import Any, ParamSpec, TypeVar

from msgspec import json

from backend.common.cache.local import local_cache_manager
from backend.common.cache.pubsub import cache_pubsub_manager
from backend.common.context import ctx
from backend.common.exception import errors
from backend.common.log import log
from backend.core.conf import settings
from backend.database.redis import redis_client
from backend.utils.serializers import select_columns_serialize, select_list_serialize

P = ParamSpec('P')
T = TypeVar('T')


def _build_cache_key(
    name: str,
    key: str | None,
    key_builder: Callable[..., str] | None,
    *args: Any,
    **kwargs: Any,
) -> str:
    """Build the cache key"""
    if key:
        if '.' in key:
            param, field = key.split('.', 1)
            value = kwargs.get(param)
            if value is None:
                raise errors.ServerError(msg=f'Failed to build cache key: parameter "{param}" is missing or empty')

            if isinstance(value, list):
                raise errors.ServerError(
                    msg='Failed to build cache key: extracting a field from a list is not supported, '
                    'use key_builder to handle list parameters'
                )

            if hasattr(value, field):
                value = getattr(value, field)
            elif isinstance(value, dict) and field in value:
                value = value[field]
            else:
                raise errors.ServerError(msg=f'Failed to build cache key: field "{field}" does not exist on the object')
        else:
            value = kwargs.get(key)
            if value is None:
                raise errors.ServerError(msg=f'Failed to build cache key: parameter "{key}" is missing or empty')

        return f'{name}:{value}'

    if key_builder:
        return f'{name}:{key_builder(*args, **kwargs)}'

    return name


def _serialize_result(result: Any) -> bytes:
    """
    Serialize the cache result

    :param result: result to serialize
    :return:
    """
    # SQLAlchemy query table
    if hasattr(result, '__table__'):
        return json.encode(select_columns_serialize(result))

    # SQLAlchemy query list
    if (
        isinstance(result, Sequence)
        and not isinstance(result, (str, bytes))
        and len(result) > 0
        and hasattr(result[0], '__table__')
    ):
        return json.encode(select_list_serialize(result))

    # Basic types
    return json.encode(result)


def _deserialize_result(value: bytes) -> Any:
    """
    Deserialize the cache result

    :param value: cache result
    :return:
    """
    try:
        return json.decode(value)
    except Exception:
        return value


def user_key_builder() -> str:
    """Generate a cache key based on the current user ID"""
    user_id = ctx.user_id
    if user_id is None:
        raise errors.ServerError(msg='Failed to build user cache key')
    return str(user_id)


def cached(  # noqa: C901
    name: str,
    *,
    key: str | None = None,
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Cache decorator

    :param name: cache name (usually the cache key prefix)
    :param key: use the value of the named method parameter as the cache key, mutually exclusive with key_builder
    :param key_builder: custom key generation function, mutually exclusive with key
    :return:
    """
    if key is not None and key_builder is not None:
        raise errors.ServerError(msg='Cache key and key_builder cannot be used at the same time')

    def decorator(func: Callable[P, T]) -> Callable[P, T]:  # noqa: C901
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache_key = _build_cache_key(name, key, key_builder, *args, **kwargs)

            # L1: local cache
            if settings.CACHE_LOCAL_ENABLED:
                local_value = local_cache_manager.get(cache_key)
                if local_value is not None:
                    return local_value

            # L2: Redis cache
            try:
                redis_value = await redis_client.get(cache_key)
                if redis_value is not None:
                    result = _deserialize_result(redis_value)
                    # Backfill L1
                    if settings.CACHE_LOCAL_ENABLED:
                        local_cache_manager.set(cache_key, result)
                    return result
            except Exception as e:
                log.warning(f'[Cache] GET error: {e}')

            # Cache miss
            result = await func(*args, **kwargs)

            if result is not None:
                try:
                    # Backfill L1
                    if settings.CACHE_LOCAL_ENABLED:
                        local_cache_manager.set(cache_key, result)

                    # Backfill L2
                    serialized_result = _serialize_result(result)
                    if settings.CACHE_REDIS_TTL:
                        await redis_client.setex(cache_key, settings.CACHE_REDIS_TTL, serialized_result)
                    else:
                        await redis_client.set(cache_key, serialized_result)
                except Exception as e:
                    log.warning(f'[Cache] SET error: {e}')

            return result

        return wrapper

    return decorator


def cache_invalidate(  # noqa: C901
    name: str,
    *,
    key: str | None = None,
    key_builder: Callable[..., str] | None = None,
    atomic: bool = True,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Cache invalidation decorator

    :param name: cache name (usually the cache key prefix)
    :param key: use the value of the named method parameter as the cache key, mutually exclusive with key_builder
    :param key_builder: custom key generation function, mutually exclusive with key
    :param atomic: whether to guarantee cache atomicity
    :return:
    """
    if key is not None and key_builder is not None:
        raise errors.ServerError(msg='Cache key and key_builder cannot be used at the same time')

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = await func(*args, **kwargs)

            # Attempt to invalidate the cache
            invalidate_success = False
            invalidate_error = None

            try:
                invalidate_key = _build_cache_key(name, key, key_builder, *args, **kwargs)

                # L1 cache invalidation
                if settings.CACHE_LOCAL_ENABLED:
                    if invalidate_key == name:
                        local_cache_manager.delete_prefix(invalidate_key)
                    else:
                        local_cache_manager.delete(invalidate_key)

                # Broadcast the invalidation message (notify other nodes to clear their local cache)
                if settings.CACHE_LOCAL_ENABLED:
                    if invalidate_key == name:
                        await cache_pubsub_manager.publish_invalidation(invalidate_key, is_delete_prefix=True)
                    else:
                        await cache_pubsub_manager.publish_invalidation(invalidate_key)

                # L2 cache invalidation
                if invalidate_key == name:
                    await redis_client.delete_prefix(invalidate_key)
                else:
                    await redis_client.delete(invalidate_key)

            except Exception as e:
                log.error(f'[Cache] INVALIDATE error: {e}')
                invalidate_error = e
            else:
                invalidate_success = True

            # Atomicity check
            if atomic and not invalidate_success:
                raise errors.ServerError(
                    msg='Cache invalidation failed, data may be inconsistent', data=invalidate_error
                )

            return result

        return wrapper

    return decorator
