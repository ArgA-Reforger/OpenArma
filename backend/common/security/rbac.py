from fastapi import Depends, Request

from backend.common.context import ctx
from backend.common.enums import MethodType, StatusType
from backend.common.exception import errors
from backend.common.log import log
from backend.common.security.jwt import DependsJwtAuth
from backend.core.conf import settings
from backend.utils.dynamic_import import import_module_cached


async def rbac_verify(request: Request, _token: str = DependsJwtAuth) -> None:  # noqa: C901
    """
    RBAC permission verification (the authentication order matters, modify with care)

    :param request: FastAPI request object
    :param _token: JWT token
    :return:
    """
    path = request.url.path

    # API authentication whitelist
    if path in settings.TOKEN_REQUEST_PATH_EXCLUDE:
        return
    for pattern in settings.TOKEN_REQUEST_PATH_EXCLUDE_PATTERN:
        if pattern.match(path):
            return

    # Enforce JWT authorization state check
    if not request.auth.scopes:
        raise errors.TokenError

    # Superusers are exempt from verification
    if request.user.is_superuser:
        return

    # Check the user's roles
    user_roles = request.user.roles
    if not user_roles or all(status == 0 for status in user_roles):
        raise errors.AuthorizationError(msg='This user has no assigned roles, please contact the system administrator')

    # Check the menus assigned to the user's roles
    if not any(len(role.menus) > 0 for role in user_roles):
        raise errors.AuthorizationError(msg='This user has no assigned menus, please contact the system administrator')

    # Check admin operation permission
    method = request.method
    if (method != MethodType.GET or method != MethodType.OPTIONS) and not request.user.is_staff:
        raise errors.AuthorizationError(
            msg='This user is forbidden from performing admin operations, please contact the system administrator'
        )

    # RBAC authentication
    if settings.RBAC_ROLE_MENU_MODE:
        path_auth_perm = ctx.permission

        # No menu operation permission identifier, skip verification
        if not path_auth_perm:
            return

        # Menu authentication whitelist
        if path_auth_perm in settings.RBAC_ROLE_MENU_EXCLUDE:
            return

        # De-duplicate menus
        unique_menus = {}
        for role in user_roles:
            for menu in role.menus:
                unique_menus[menu.id] = menu

        # Verify against the assigned menu permissions
        allow_perms = []
        for menu in list(unique_menus.values()):
            if menu.perms and menu.status == StatusType.enable:
                allow_perms.extend(menu.perms.split(','))
        if path_auth_perm not in allow_perms:
            raise errors.AuthorizationError
    else:
        try:
            casbin_rbac = import_module_cached('backend.plugin.casbin_rbac.rbac')
            casbin_verify = casbin_rbac.casbin_verify
        except (ImportError, AttributeError) as e:
            log.error(f'Attempting RBAC permission verification via casbin, but this plugin does not exist: {e}')
            raise errors.ServerError(msg='Permission verification failed, please contact the system administrator')

        await casbin_verify(request)


# RBAC authorization dependency injection
DependsRBAC = Depends(rbac_verify)
