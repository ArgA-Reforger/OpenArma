import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from backend.common.context import ctx
from backend.common.log import log
from backend.common.observability.prometheus import (
    PROMETHEUS_APP_NAME,
    PROMETHEUS_REQUEST_COUNTER,
    PROMETHEUS_REQUEST_IN_PROGRESS_GAUGE,
)
from backend.core.conf import settings
from backend.utils.timezone import timezone


class AccessMiddleware(BaseHTTPMiddleware):
    """Access log middleware"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process the request and record the access log

        :param request: FastAPI request object
        :param call_next: next middleware or route handler function
        :return:
        """
        path = request.url.path
        method = request.method

        if method != 'OPTIONS':
            log.debug(
                f'--> Request started[{path if not request.url.query else request.url.path + "/" + request.url.query}]'
            )

        perf_time = time.perf_counter()
        ctx.perf_time = perf_time

        start_time = timezone.now()
        ctx.start_time = start_time

        if path.startswith(settings.FASTAPI_API_V1_PATH):
            PROMETHEUS_REQUEST_IN_PROGRESS_GAUGE.labels(app_name=PROMETHEUS_APP_NAME, method=method, path=path).inc()
            PROMETHEUS_REQUEST_COUNTER.labels(app_name=PROMETHEUS_APP_NAME, method=method, path=path).inc()

        response = await call_next(request)

        return response
