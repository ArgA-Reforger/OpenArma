from collections.abc import Awaitable, Callable
from math import ceil

from fastapi import Request, Response
from fastapi_pagination.utils import is_async_callable
from pyrate_limiter import AbstractBucket, Limiter, Rate
from pyrate_limiter.buckets import RedisBucket
from starlette.concurrency import run_in_threadpool

from backend.common.exception import errors
from backend.common.response.response_code import StandardResponseCode
from backend.core.conf import settings
from backend.database.redis import redis_client
from backend.utils.request_parse import get_request_ip

IdentifierCallable = Callable[[Request], str] | Callable[[Request], Awaitable[str]]
CallbackCallable = Callable[[Request, Response, int], None] | Callable[[Request, Response, int], Awaitable[None]]


def default_identifier(request: Request) -> str:
    """
    Default identifier

    :param request: FastAPI request object
    :return:
    """
    ip = get_request_ip(request)
    return f'{ip}:{request.scope["path"]}'


def default_callback(request: Request, response: Response, retry_after: int) -> None:
    """
    Default callback

    :param request: FastAPI request object
    :param response: FastAPI response object
    :param retry_after: seconds until the next retry
    :return:
    """
    raise errors.HTTPError(
        code=StandardResponseCode.HTTP_429,
        msg='Too many requests, please try again later',
        headers={'Retry-After': str(retry_after)},
    )


class RateLimiter:
    """Rate limiter"""

    def __init__(
        self,
        *rates: Rate,
        identifier: IdentifierCallable = default_identifier,
        bucket: AbstractBucket | None = None,
        limiter: Limiter | None = None,
        callback: CallbackCallable = default_callback,
    ) -> None:
        """
        Initialize the rate limiter

        :param rates: pyrate_limiter Rate object(s), a single one or multiple can be passed
        :param identifier: custom identifier function
        :param bucket: pyrate_limiter AbstractBucket instance
        :param limiter: pyrate_limiter Limiter instance
        :param callback: custom rate-limit callback function
        :return:
        """
        if not rates and bucket is None:
            raise errors.ServerError(msg='At least one Rate or bucket instance must be provided')
        self.rates = list(rates)
        self.identifier = identifier
        self.bucket = bucket
        self.limiter = limiter
        self.callback = callback

    async def __call__(self, request: Request, response: Response) -> None:
        if self.limiter is None:
            if self.bucket is None:
                self.bucket = await RedisBucket.init(  # type: ignore
                    rates=self.rates,
                    redis=redis_client,
                    bucket_key=f'{settings.REQUEST_LIMITER_REDIS_PREFIX}',
                )
            self.limiter = Limiter(self.bucket)

        if is_async_callable(self.identifier):
            identifier = await self.identifier(request)
        else:
            identifier = await run_in_threadpool(self.identifier, request)

        acquired = await self.limiter.try_acquire_async(identifier, blocking=False)
        if not acquired:
            retry_after = ceil(self.bucket.failing_rate.interval / 1000)
            if is_async_callable(self.callback):
                await self.callback(request, response, retry_after)
            else:
                await run_in_threadpool(self.callback, request, response, retry_after)
