import json
import uuid

from datetime import timedelta
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic_core import from_json
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.model import User
from backend.app.admin.schema.user import GetUserInfoWithRelationDetail
from backend.common.dataclasses import AccessToken, NewToken, RefreshToken, TokenPayload
from backend.common.exception import errors
from backend.core.conf import settings
from backend.database.db import async_db_session
from backend.database.redis import redis_client
from backend.utils.timezone import timezone

# JWT dependency injection
DependsJwtAuth = Depends(HTTPBearer())


def jwt_encode(payload: dict[str, Any]) -> str:
    """
    Generate a JWT token

    :param payload: payload
    :return:
    """
    return jwt.encode(payload, settings.TOKEN_SECRET_KEY, settings.TOKEN_ALGORITHM)


def jwt_decode(token: str) -> TokenPayload:
    """
    Decode a JWT token

    :param token: JWT token
    :return:
    """
    try:
        payload = jwt.decode(
            token,
            settings.TOKEN_SECRET_KEY,
            algorithms=[settings.TOKEN_ALGORITHM],
            options={'verify_exp': True},
        )
        session_uuid = payload.get('session_uuid')
        user_id = payload.get('sub')
        expire = payload.get('exp')
        if not session_uuid or not user_id or not expire:
            raise errors.TokenError(msg='Invalid token')
    except ExpiredSignatureError:
        raise errors.TokenError(msg='Token has expired')
    except (JWTError, Exception):
        raise errors.TokenError(msg='Invalid token')
    return TokenPayload(
        id=int(user_id),
        session_uuid=session_uuid,
        expire_time=timezone.from_datetime(timezone.to_utc(expire)),
    )


async def create_access_token(user_id: int, *, multi_login: bool, **kwargs) -> AccessToken:
    """
    Generate an encrypted token

    :param user_id: user ID
    :param multi_login: whether multi-device login is allowed
    :param kwargs: extra token information
    :return:
    """
    expire = timezone.now() + timedelta(seconds=settings.TOKEN_EXPIRE_SECONDS)
    session_uuid = str(uuid.uuid4())
    access_token = jwt_encode({
        'session_uuid': session_uuid,
        'exp': timezone.to_utc(expire).timestamp(),
        'sub': str(user_id),
    })

    if not multi_login:
        await redis_client.delete_prefix(f'{settings.TOKEN_REDIS_PREFIX}:{user_id}')

    await redis_client.setex(
        f'{settings.TOKEN_REDIS_PREFIX}:{user_id}:{session_uuid}',
        settings.TOKEN_EXPIRE_SECONDS,
        access_token,
    )

    # Extra token information is stored separately
    if kwargs:
        await redis_client.setex(
            f'{settings.TOKEN_EXTRA_INFO_REDIS_PREFIX}:{user_id}:{session_uuid}',
            settings.TOKEN_EXPIRE_SECONDS,
            json.dumps(kwargs, ensure_ascii=False),
        )

    return AccessToken(access_token=access_token, access_token_expire_time=expire, session_uuid=session_uuid)


async def create_refresh_token(session_uuid: str, user_id: int, *, multi_login: bool) -> RefreshToken:
    """
    Generate an encrypted refresh token, used only for creating a new token

    :param session_uuid: session UUID
    :param user_id: user ID
    :param multi_login: whether multi-device login is allowed
    :return:
    """
    expire = timezone.now() + timedelta(seconds=settings.TOKEN_REFRESH_EXPIRE_SECONDS)
    refresh_token = jwt_encode({
        'session_uuid': session_uuid,
        'exp': timezone.to_utc(expire).timestamp(),
        'sub': str(user_id),
    })

    if not multi_login:
        await redis_client.delete_prefix(f'{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user_id}')

    await redis_client.setex(
        f'{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user_id}:{session_uuid}',
        settings.TOKEN_REFRESH_EXPIRE_SECONDS,
        refresh_token,
    )
    return RefreshToken(refresh_token=refresh_token, refresh_token_expire_time=expire)


async def create_new_token(
    refresh_token: str,
    session_uuid: str,
    user_id: int,
    *,
    multi_login: bool,
    **kwargs,
) -> NewToken:
    """
    Generate a new token

    :param refresh_token: refresh token
    :param session_uuid: session UUID
    :param user_id: user ID
    :param multi_login: whether multi-device login is allowed
    :param kwargs: extra token information
    :return:
    """
    redis_refresh_token = await redis_client.get(f'{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user_id}:{session_uuid}')
    if not redis_refresh_token or redis_refresh_token != refresh_token:
        raise errors.TokenError(msg='Refresh token has expired, please log in again')

    await redis_client.delete(f'{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user_id}:{session_uuid}')
    await redis_client.delete(f'{settings.TOKEN_REDIS_PREFIX}:{user_id}:{session_uuid}')

    new_access_token = await create_access_token(user_id, multi_login=multi_login, **kwargs)
    new_refresh_token = await create_refresh_token(new_access_token.session_uuid, user_id, multi_login=multi_login)
    return NewToken(
        new_access_token=new_access_token.access_token,
        new_access_token_expire_time=new_access_token.access_token_expire_time,
        new_refresh_token=new_refresh_token.refresh_token,
        new_refresh_token_expire_time=new_refresh_token.refresh_token_expire_time,
        session_uuid=new_access_token.session_uuid,
    )


async def revoke_token(user_id: int, session_uuid: str) -> None:
    """
    Revoke a token

    :param user_id: user ID
    :param session_uuid: session ID
    :return:
    """
    await redis_client.delete(f'{settings.TOKEN_REDIS_PREFIX}:{user_id}:{session_uuid}')
    await redis_client.delete(f'{settings.TOKEN_EXTRA_INFO_REDIS_PREFIX}:{user_id}:{session_uuid}')


def get_token(request: Request) -> str:
    """
    Get the token from the request headers

    :param request: FastAPI request object
    :return:
    """
    authorization = request.headers.get('Authorization')
    scheme, token = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != 'bearer':
        raise errors.TokenError(msg='Invalid token')
    return token


async def get_current_user(db: AsyncSession, pk: int) -> User:
    """
    Get the current user

    :param db: database session
    :param pk: user ID
    :return:
    """
    from backend.app.admin.crud.crud_user import user_dao

    user = await user_dao.get_join(db, user_id=pk)
    if not user:
        raise errors.TokenError(msg='Invalid token')
    if not user.status:
        raise errors.AuthorizationError(msg='This user has been locked, please contact the system administrator')
    if user.dept_id:
        if not user.dept.status:
            raise errors.AuthorizationError(
                msg="This user's department has been locked, please contact the system administrator"
            )
        if user.dept.del_flag:
            raise errors.AuthorizationError(
                msg="This user's department has been deleted, please contact the system administrator"
            )
    if user.roles:
        role_status = [role.status for role in user.roles]
        if all(status == 0 for status in role_status):
            raise errors.AuthorizationError(
                msg="This user's role has been locked, please contact the system administrator"
            )
    return user


async def get_jwt_user(user_id: int) -> GetUserInfoWithRelationDetail:
    """
    Get the JWT user

    :param user_id:
    :return:
    """
    cache_user = await redis_client.get(f'{settings.JWT_USER_REDIS_PREFIX}:{user_id}')
    if not cache_user:
        async with async_db_session() as db:
            current_user = await get_current_user(db, user_id)
            user = GetUserInfoWithRelationDetail.model_validate(current_user)
            await redis_client.setex(
                f'{settings.JWT_USER_REDIS_PREFIX}:{user_id}',
                settings.TOKEN_EXPIRE_SECONDS,
                user.model_dump_json(),
            )
    else:
        # TODO: at an appropriate time, replace with model_validate_json
        # https://docs.pydantic.dev/latest/concepts/json/#partial-json-parsing
        user = GetUserInfoWithRelationDetail.model_validate(from_json(cache_user, allow_partial=True))
    return user


def superuser_verify(request: Request, _token: str = DependsJwtAuth) -> bool:
    """
    Verify the current user's superuser permission

    :param request: FastAPI request object
    :param _token: JWT token
    :return:
    """
    superuser = request.user.is_superuser
    if not superuser or not request.user.is_staff:
        raise errors.AuthorizationError
    return superuser


async def jwt_authentication(token: str) -> GetUserInfoWithRelationDetail:
    """
    JWT authentication

    :param token: JWT token
    :return:
    """
    token_payload = jwt_decode(token)
    user_id = token_payload.id
    redis_token = await redis_client.get(f'{settings.TOKEN_REDIS_PREFIX}:{user_id}:{token_payload.session_uuid}')
    if not redis_token:
        raise errors.TokenError(msg='Token has expired')

    if token != redis_token:
        raise errors.TokenError(msg='Token is no longer valid')

    return await get_jwt_user(user_id)


# Superuser authentication dependency injection
DependsSuperUser = Depends(superuser_verify)
