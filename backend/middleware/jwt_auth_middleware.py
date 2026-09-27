from typing import Any

from fastapi import Request, Response
from fastapi.security.utils import get_authorization_scheme_param
from starlette.authentication import AuthCredentials, AuthenticationBackend
from starlette.authentication import AuthenticationError as StarletteAuthenticationError
from starlette.requests import HTTPConnection

from backend.app.admin.schema.user import GetUserInfoWithRelationDetail
from backend.common.context import ctx
from backend.common.exception.errors import TokenError
from backend.common.log import log
from backend.common.security.jwt import jwt_authentication
from backend.core.conf import settings
from backend.utils.serializers import MsgSpecJSONResponse


class AuthenticationError(StarletteAuthenticationError):
    """Override the internal authentication error class"""

    def __init__(
        self,
        *,
        code: int | None = None,
        msg: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the authentication error

        :param code: error code
        :param msg: error message
        :param headers: response headers
        :return:
        """
        self.code = code
        self.msg = msg
        self.headers = headers


class JwtAuthMiddleware(AuthenticationBackend):
    """JWT authentication middleware"""

    @staticmethod
    def auth_exception_handler(conn: HTTPConnection, exc: AuthenticationError) -> Response:
        """
        Override the internal authentication error handling

        :param conn: HTTP connection object
        :param exc: authentication error object
        :return:
        """
        return MsgSpecJSONResponse(content={'code': exc.code, 'msg': exc.msg, 'data': None}, status_code=exc.code)

    @staticmethod
    def extract_token(request: Request) -> str | None:
        """
        Extract the Bearer Token from the request

        :param request: FastAPI request object
        :return:
        """
        authorization = request.headers.get('Authorization')
        if not authorization:
            return None

        path = request.url.path
        if path in settings.TOKEN_REQUEST_PATH_EXCLUDE:
            return None
        for pattern in settings.TOKEN_REQUEST_PATH_EXCLUDE_PATTERN:
            if pattern.match(path):
                return None

        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() != 'bearer':
            return None

        return token

    async def authenticate(self, request: Request) -> tuple[AuthCredentials, GetUserInfoWithRelationDetail] | None:
        """
        Authenticate the request

        :param request: FastAPI request object
        :return:
        """
        token = self.extract_token(request)
        if token is None:
            return None

        try:
            user = await jwt_authentication(token)
        except TokenError as exc:
            raise AuthenticationError(code=exc.code, msg=exc.detail, headers=exc.headers)
        except Exception as e:
            log.exception(f'JWT authorization exception: {e}')
            raise AuthenticationError(code=getattr(e, 'code', 500), msg=getattr(e, 'msg', 'Internal Server Error'))

        # Set the user ID in the context
        ctx.user_id = user.id

        # Note: this return uses a non-standard mode, so some standard features are lost once authentication succeeds
        # For the standard return mode, see: https://www.starlette.io/authentication/
        return AuthCredentials(['authenticated']), user
