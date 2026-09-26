import json
import time

from asyncio import Queue
from typing import Any

from fastapi import Response
from starlette.datastructures import UploadFile
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.app.admin.schema.opera_log import CreateOperaLogParam
from backend.app.admin.service.opera_log_service import opera_log_service
from backend.common.context import ctx
from backend.common.enums import StatusType
from backend.common.log import log
from backend.common.observability.prometheus import (
    PROMETHEUS_APP_NAME,
    PROMETHEUS_EXCEPTION_COUNTER,
    PROMETHEUS_REQUEST_COST_TIME_HISTOGRAM,
    PROMETHEUS_REQUEST_IN_PROGRESS_GAUGE,
    PROMETHEUS_RESPONSE_COUNTER,
)
from backend.common.queue import batch_dequeue
from backend.common.response.response_code import StandardResponseCode
from backend.core.conf import settings
from backend.database.db import async_db_session
from backend.utils.trace_id import get_request_trace_id


class OperaLogMiddleware(BaseHTTPMiddleware):
    """Operation log middleware"""

    opera_log_queue: Queue = Queue(maxsize=settings.OPERA_LOG_QUEUE_MAXSIZE)

    async def dispatch(self, request: Request, call_next: Any) -> Response:  # noqa: C901
        """
        Process the request and record the operation log

        :param request: FastAPI request object
        :param call_next: next middleware or route handler function
        :return:
        """
        path = request.url.path
        method = request.method
        code = 200
        msg = 'Success'
        status = StatusType.enable
        elapsed = 0

        try:
            username = request.user.username
        except AttributeError:
            username = None

        should_log_opera = path.startswith(settings.FASTAPI_API_V1_PATH) and path not in settings.OPERA_LOG_PATH_EXCLUDE
        args = await self.get_request_args(request) if should_log_opera else None

        try:
            response = await call_next(request)
        except Exception as e:
            elapsed = round((time.perf_counter() - ctx.perf_time) * 1000, 3)
            log.error(f'Request exception: {e!s}')

            if should_log_opera:
                code = getattr(e, 'code', StandardResponseCode.HTTP_500)
                msg = getattr(e, 'msg', str(e))
                status = StatusType.disable

            if path.startswith(settings.FASTAPI_API_V1_PATH):
                PROMETHEUS_EXCEPTION_COUNTER.labels(
                    app_name=PROMETHEUS_APP_NAME,
                    method=method,
                    path=path,
                    exception_type=type(e).__name__,
                ).inc()

            raise
        else:
            elapsed = round((time.perf_counter() - ctx.perf_time) * 1000, 3)

            if should_log_opera:
                # Check exception information in the context
                for exception_key in [
                    '__request_http_exception__',
                    '__request_validation_exception__',
                    '__request_assertion_error__',
                    '__request_custom_exception__',
                ]:
                    exception = ctx.get(exception_key)
                    if exception:
                        code = exception.get('code')
                        msg = exception.get('msg')
                        status = StatusType.disable
                        log.error(f'Request exception: {msg}')
                        break

            if path.startswith(settings.FASTAPI_API_V1_PATH):
                PROMETHEUS_REQUEST_COST_TIME_HISTOGRAM.labels(
                    app_name=PROMETHEUS_APP_NAME, method=method, path=path
                ).observe(amount=elapsed, exemplar={'TraceID': get_request_trace_id()})
        finally:
            # summary can only be obtained after the request
            route = request.scope.get('route')
            summary = route.summary or '' if route else ''

            log.debug(f'Endpoint summary: [{summary}]')
            log.debug(f'Request address: [{ctx.ip}]')
            log.debug(f'Request parameters: {args}')

            if request.method != 'OPTIONS':
                log.debug('<-- Request ended')

            if path.startswith(settings.FASTAPI_API_V1_PATH):
                log.info(f'{ctx.ip: <15} | {method: <8} | {code!s: <6} | {path} | {elapsed:.3f}ms')

            if should_log_opera and request.method != 'OPTIONS':
                opera_log_in = CreateOperaLogParam(
                    trace_id=get_request_trace_id(),
                    username=username,
                    method=method,
                    title=summary,
                    path=path,
                    ip=ctx.ip,
                    country=ctx.country,
                    region=ctx.region,
                    city=ctx.city,
                    user_agent=ctx.user_agent,
                    os=ctx.os,
                    browser=ctx.browser,
                    device=ctx.device,
                    args=args,
                    status=status,
                    code=str(code),
                    msg=msg,
                    cost_time=elapsed,
                    opera_time=ctx.start_time,
                )
                await self.opera_log_queue.put(opera_log_in)

            if path.startswith(settings.FASTAPI_API_V1_PATH):
                PROMETHEUS_RESPONSE_COUNTER.labels(
                    app_name=PROMETHEUS_APP_NAME, method=method, path=path, status_code=code
                ).inc()
                PROMETHEUS_REQUEST_IN_PROGRESS_GAUGE.labels(
                    app_name=PROMETHEUS_APP_NAME, method=method, path=path
                ).dec()

        return response

    async def get_request_args(self, request: Request) -> dict[str, Any] | None:  # noqa: C901
        """
        Get the request parameters

        :param request: FastAPI request object
        :return:
        """
        args = {}

        # Query parameters
        query_params = dict(request.query_params)
        if query_params:
            args['query_params'] = self.desensitization(query_params)

        # Path parameters
        path_params = request.path_params
        if path_params:
            args['path_params'] = self.desensitization(path_params)

        # Tip: .body() must be obtained before .form()
        # https://github.com/encode/starlette/discussions/1933
        content_type = request.headers.get('Content-Type', '').split(';')

        # Request body
        body_data = await request.body()
        if body_data:
            # Note: non-json data uses "data" as the key by default
            if 'application/json' not in content_type:
                args['data'] = body_data.decode('utf-8', 'ignore') if isinstance(body_data, bytes) else str(body_data)
            else:
                json_data = await request.json()
                if isinstance(json_data, dict):
                    args['json'] = self.desensitization(json_data)
                else:
                    args['data'] = str(json_data)

        # Form parameters
        form_data = await request.form()
        if len(form_data) > 0:
            serialized_form = {}
            for k, v in form_data.items():
                if isinstance(v, UploadFile):
                    serialized_form[k] = {
                        'filename': v.filename,
                        'content_type': v.content_type,
                        'size': v.size,
                    }
                else:
                    serialized_form[k] = v
            if 'multipart/form-data' not in content_type:
                args['x-www-form-urlencoded'] = self.desensitization(serialized_form)
            else:
                args['form-data'] = self.desensitization(serialized_form)

        if args:
            args = self.truncate(args)

        return args or None

    @staticmethod
    def truncate(args: dict[str, Any]) -> dict[str, Any]:
        """
        Truncation handling

        :param args: request parameter dict that needs truncating
        :return:
        """
        max_size = 10240  # Maximum data size (bytes)

        try:
            args_str = json.dumps(args, ensure_ascii=False)
            args_size = len(args_str.encode('utf-8'))

            if args_size > max_size:
                truncated_str = args_str[:max_size]
                return {
                    '_truncated': True,
                    '_original_size': args_size,
                    '_max_size': max_size,
                    '_message': f'Data too large and was truncated: original size {args_size} bytes, '
                    f'limit {max_size} bytes',
                    'data_preview': truncated_str,
                }
        except Exception as e:
            log.error(f'Failed to truncate request parameters: {e}')

        return args

    @staticmethod
    def desensitization(args: dict[str, Any]) -> dict[str, Any]:
        """
        Desensitization handling

        :param args: parameter dict that needs desensitizing
        :return:
        """
        for key in args:
            if key in settings.OPERA_LOG_REDACT_KEYS:
                args[key] = '[REDACTED]'
        return args

    @classmethod
    async def consumer(cls) -> None:
        """Operation log consumer"""
        while True:
            logs = await batch_dequeue(
                cls.opera_log_queue,
                max_items=settings.OPERA_LOG_QUEUE_BATCH_CONSUME_SIZE,
                timeout=settings.OPERA_LOG_QUEUE_TIMEOUT,
            )
            if logs:
                try:
                    if settings.DATABASE_ECHO:
                        log.info('Automatically running the [bulk create operation log] task...')
                    async with async_db_session.begin() as db:
                        await opera_log_service.bulk_create(db=db, objs=logs)
                except Exception as e:
                    log.error(f'Failed to persist operation logs, lost {len(logs)} log entries: {e}')
                finally:
                    for _ in range(len(logs)):
                        cls.opera_log_queue.task_done()
