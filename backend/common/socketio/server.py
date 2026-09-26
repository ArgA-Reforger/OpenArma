import urllib.parse

import socketio

from backend.common.log import log
from backend.common.security.jwt import jwt_authentication
from backend.core.conf import settings
from backend.database.redis import redis_client

# Create the Socket.IO server instance
sio = socketio.AsyncServer(
    client_manager=socketio.AsyncRedisManager(
        f'redis://:{urllib.parse.quote(settings.REDIS_PASSWORD)}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DATABASE}',
    ),
    async_mode='asgi',
    cors_allowed_origins=settings.CORS_ALLOWED_ORIGINS,
    cors_credentials=True,
    namespaces=['/ws'],
)


@sio.event
async def connect(sid, environ, auth) -> bool:
    """Socket connect event"""
    if not auth:
        log.error('WebSocket connection failed: no authorization')
        return False

    session_uuid = auth.get('session_uuid')
    token = auth.get('token')
    if not token or not session_uuid:
        log.error('WebSocket connection failed: authorization failed, please check')
        return False

    # Direct connection without authorization
    if token == settings.WS_NO_AUTH_MARKER:
        await redis_client.sadd(settings.TOKEN_ONLINE_REDIS_PREFIX, session_uuid)
        return True

    try:
        await jwt_authentication(token)
    except Exception as e:
        log.info(f'WebSocket connection failed: {e!s}')
        return False

    await redis_client.sadd(settings.TOKEN_ONLINE_REDIS_PREFIX, session_uuid)
    return True


@sio.event
async def disconnect(sid) -> None:
    """Socket disconnect event"""
    await redis_client.spop(settings.TOKEN_ONLINE_REDIS_PREFIX)
