import os

from asyncio import create_task
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import socketio

from fastapi import Depends, FastAPI
from fastapi_pagination import add_pagination
from prometheus_client import make_asgi_app
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.staticfiles import StaticFiles
from starlette_context.middleware import ContextMiddleware
from starlette_context.plugins import RequestIdPlugin

from backend import __version__
from backend.common.cache.pubsub import cache_pubsub_manager
from backend.common.exception.exception_handler import register_exception
from backend.common.log import set_custom_logfile, setup_logging
from backend.common.observability.otel import init_otel
from backend.common.response.response_code import StandardResponseCode
from backend.core.conf import settings
from backend.core.path_conf import STATIC_DIR, UPLOAD_DIR
from backend.database.db import async_db_session, create_tables
from backend.database.redis import redis_client
from backend.middleware.access_middleware import AccessMiddleware
from backend.middleware.i18n_middleware import I18nMiddleware
from backend.middleware.jwt_auth_middleware import JwtAuthMiddleware
from backend.middleware.opera_log_middleware import OperaLogMiddleware
from backend.middleware.state_middleware import StateMiddleware
from backend.plugin.core import build_final_router
from backend.utils.demo_mode import demo_site
from backend.utils.openapi import ensure_unique_route_names, simplify_operation_ids
from backend.utils.serializers import MsgSpecJSONResponse
from backend.utils.snowflake import snowflake
from backend.utils.trace_id import OtelTraceIdPlugin


@asynccontextmanager
async def register_init(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup initialization

    :param app: FastAPI application instance
    :return:
    """
    # Create the database tables
    await create_tables()

    # Initialize redis
    await redis_client.init()

    # Initialize the snowflake node
    await snowflake.init()

    # Create the operation log task
    create_task(OperaLogMiddleware.consumer())

    # Start the cache Pub/Sub listener
    cache_pubsub_manager.start_listener()

    # Automatically run the seed data (only for first-time deployment, triggered when the sys_user table is empty)
    try:
        await _auto_seed_if_empty()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning('Automatic seed data run failed: %s', e)

    yield

    # Stop the cache Pub/Sub listener
    await cache_pubsub_manager.stop_listener()

    # Release the snowflake node
    await snowflake.shutdown()

    # Close the redis connection
    await redis_client.aclose()


async def _auto_seed_if_empty() -> None:
    """Automatically run the seed data on first-time deployment (treated as first-time when sys_user is empty)"""
    import logging

    from sqlalchemy import text

    from backend.app.builtin_tool.service.seed import seed_builtin_tools

    _log = logging.getLogger(__name__)

    async with async_db_session() as db:
        # Built-in tool seed (idempotent, runs on every startup)
        await seed_builtin_tools(db)
        await db.commit()

    async with async_db_session() as db:
        result = await db.execute(text('SELECT COUNT(*) FROM sys_user'))
        count = result.scalar()
        if count and count > 0:
            return

    _log.info('Detected empty sys_user, running first-time deployment seed data...')

    from backend.common.enums import DataBaseType
    from backend.core.path_conf import POSTGRESQL_SCRIPT_DIR
    from backend.plugin.core import get_plugin_sql, get_plugins
    from backend.utils.sql_parser import parse_sql_script

    db_script_dir = POSTGRESQL_SCRIPT_DIR
    if DataBaseType.mysql == settings.DATABASE_TYPE:
        from backend.core.path_conf import MYSQL_SCRIPT_DIR
        db_script_dir = MYSQL_SCRIPT_DIR

    import anyio

    main_sql = db_script_dir / f'init_{"snowflake_" if settings.DATABASE_PK_MODE == "snowflake" else ""}test_data.sql'
    sql_files: list[str] = []
    if await anyio.Path(main_sql).exists():
        sql_files.append(str(main_sql))

    skip = {'init_test_data.sql', 'init_snowflake_test_data.sql'}
    async for child in anyio.Path(db_script_dir).iterdir():
        if child.name.endswith('.sql') and child.name.startswith('init_') and child.name not in skip:
            path_str = str(child)
            if path_str not in sql_files:
                sql_files.append(path_str)

    for plugin in get_plugins():
        plugin_sql = await get_plugin_sql(plugin, settings.DATABASE_TYPE, settings.DATABASE_PK_MODE)
        if plugin_sql:
            sql_files.append(str(plugin_sql))

    async with async_db_session.begin() as db:
        for sql_file in sql_files:
            _log.info('Running seed script: %s', sql_file)
            stmts = await parse_sql_script(sql_file)
            for stmt in stmts:
                await db.execute(text(stmt))

    _log.info('Seed data run completed (%d scripts)', len(sql_files))


def register_app() -> FastAPI:
    """Register the FastAPI application"""

    app = FastAPI(
        title=settings.FASTAPI_TITLE,
        version=__version__,
        description=settings.FASTAPI_DESCRIPTION,
        docs_url=settings.FASTAPI_DOCS_URL,
        redoc_url=settings.FASTAPI_REDOC_URL,
        openapi_url=settings.FASTAPI_OPENAPI_URL,
        default_response_class=MsgSpecJSONResponse,
        lifespan=register_init,
    )

    # Register components
    register_logger()
    register_socket_app(app)
    register_static_file(app)
    register_middleware(app)
    register_router(app)
    register_page(app)
    register_exception(app)

    if settings.GRAFANA_METRICS_ENABLE:
        register_metrics(app)

    return app


def register_logger() -> None:
    """Register logging"""
    setup_logging()
    set_custom_logfile()


def register_static_file(app: FastAPI) -> None:
    """
    Register the static resource service

    :param app: FastAPI application instance
    :return:
    """
    # Uploaded static resources
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    app.mount('/static/upload', StaticFiles(directory=UPLOAD_DIR), name='upload')

    # Built-in static resources
    if settings.FASTAPI_STATIC_FILES:
        app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


def register_middleware(app: FastAPI) -> None:
    """
    Register middleware (execution order runs bottom to top)

    :param app: FastAPI application instance
    :return:
    """
    # Opera log
    app.add_middleware(OperaLogMiddleware)

    # State
    app.add_middleware(StateMiddleware)

    # JWT auth
    app.add_middleware(
        AuthenticationMiddleware,
        backend=JwtAuthMiddleware(),
        on_error=JwtAuthMiddleware.auth_exception_handler,
    )

    # I18n
    app.add_middleware(I18nMiddleware)

    # Access log
    app.add_middleware(AccessMiddleware)

    # ContextVar
    plugins = [OtelTraceIdPlugin()] if settings.GRAFANA_METRICS_ENABLE else [RequestIdPlugin(validate=True)]
    app.add_middleware(
        ContextMiddleware,
        plugins=plugins,
        default_error_response=MsgSpecJSONResponse(
            content={'code': StandardResponseCode.HTTP_400, 'msg': 'BAD_REQUEST', 'data': None},
            status_code=StandardResponseCode.HTTP_400,
        ),
    )

    # CORS
    # https://github.com/fastapi-practices/fastapi_best_architecture/pull/789/changes
    # https://github.com/open-telemetry/opentelemetry-python-contrib/issues/4031
    if settings.MIDDLEWARE_CORS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
            expose_headers=settings.CORS_EXPOSE_HEADERS,
        )

    app.add_middleware(GZipMiddleware, minimum_size=1000)


def register_router(app: FastAPI) -> None:
    """
    Register routes

    :param app: FastAPI application instance
    :return:
    """
    dependencies = [Depends(demo_site)] if settings.DEMO_MODE else None

    # API
    router = build_final_router()
    app.include_router(router, dependencies=dependencies)

    # Extra
    ensure_unique_route_names(app)
    simplify_operation_ids(app)


def register_page(app: FastAPI) -> None:
    """
    Register the paginated query feature

    :param app: FastAPI application instance
    :return:
    """
    add_pagination(app)


def register_socket_app(app: FastAPI) -> None:
    """
    Register the Socket.IO application

    :param app: FastAPI application instance
    :return:
    """
    from backend.common.socketio.server import sio

    socket_app = socketio.ASGIApp(
        socketio_server=sio,
        other_asgi_app=app,
        # Never remove this setting: https://github.com/pyropy/fastapi-socketio/issues/51
        socketio_path='/ws/socket.io',
    )
    app.mount('/ws', socket_app)


def register_metrics(app: FastAPI) -> None:
    """
    Register metrics

    :param app: FastAPI application instance
    :return:
    """
    metrics_app = make_asgi_app()
    app.mount('/metrics', metrics_app)

    init_otel(app)
