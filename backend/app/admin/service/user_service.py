from collections.abc import Sequence
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_dept import dept_dao
from backend.app.admin.crud.crud_role import role_dao
from backend.app.admin.crud.crud_user import user_dao
from backend.app.admin.model import Role, User
from backend.app.admin.schema.user import (
    AddUserParam,
    ResetPasswordParam,
    UpdateUserParam,
)
from backend.app.admin.schema.user_password_history import CreateUserPasswordHistoryParam
from backend.app.admin.service.user_password_history_service import password_security_service
from backend.app.admin.utils.password_security import password_verify, validate_new_password
from backend.common.context import ctx
from backend.common.enums import UserPermissionType
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.common.response.response_code import CustomErrorCode
from backend.common.security.jwt import get_token, jwt_decode
from backend.core.conf import settings
from backend.database.redis import redis_client
from backend.utils.serializers import select_join_serialize


class UserService:
    """User service class"""

    @staticmethod
    async def get_userinfo(*, db: AsyncSession, pk: int | None = None, username: str | None = None) -> User:
        """
        Get user info

        :param db: database session
        :param pk: user ID
        :param username: username
        :return:
        """
        user = await user_dao.get_join(db, user_id=pk, username=username)
        if not user:
            raise errors.NotFoundError(msg='User does not exist')
        return user

    @staticmethod
    async def get_roles(*, db: AsyncSession, pk: int) -> Sequence[Role]:
        """
        Get all roles of a user

        :param db: database session
        :param pk: user ID
        :return:
        """
        user = await user_dao.get_join(db, user_id=pk)
        if not user:
            raise errors.NotFoundError(msg='User does not exist')
        return user.roles

    @staticmethod
    async def get_list(*, db: AsyncSession, dept: int, username: str, phone: str, status: int) -> dict[str, Any]:
        """
        Get user list

        :param db: database session
        :param dept: department ID
        :param username: username
        :param phone: phone number
        :param status: status
        :return:
        """
        user_select = await user_dao.get_select(dept=dept, username=username, phone=phone, status=status)
        data = await paging_data(db, user_select)
        if data['items']:
            serialized_items = select_join_serialize(data['items'], relationships=['User-m2o-Dept', 'User-m2m-Role'])
            # Ensure the result is a list, even with a single element
            data['items'] = [serialized_items] if not isinstance(serialized_items, list) else serialized_items
        return data

    @staticmethod
    async def create(*, db: AsyncSession, obj: AddUserParam) -> None:
        """
        Create user

        :param db: database session
        :param obj: user creation params
        :return:
        """
        if await user_dao.get_by_username(db, obj.username):
            raise errors.ConflictError(msg='Username already registered')
        if not obj.password:
            raise errors.RequestError(msg='Password cannot be empty')
        if not await dept_dao.get(db, obj.dept_id):
            raise errors.NotFoundError(msg='Department does not exist')
        for role_id in obj.roles:
            if not await role_dao.get(db, role_id):
                raise errors.NotFoundError(msg='Role does not exist')
        obj.nickname = obj.nickname or obj.username
        await user_dao.add(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateUserParam) -> int:
        """
        Update user info

        :param db: database session
        :param pk: user ID
        :param obj: user update params
        :return:
        """
        user = await user_dao.get_join(db, user_id=pk)
        if not user:
            raise errors.NotFoundError(msg='User does not exist')
        if obj.username != user.username and await user_dao.get_by_username(db, obj.username):
            raise errors.ConflictError(msg='Username already registered')
        if obj.dept_id and obj.dept_id != user.dept_id and not await dept_dao.get(db, dept_id=obj.dept_id):
            raise errors.NotFoundError(msg='Department does not exist')
        for role_id in obj.roles:
            if not await role_dao.get(db, role_id):
                raise errors.NotFoundError(msg='Role does not exist')
        count = await user_dao.update(db, user.id, obj)
        await redis_client.delete(f'{settings.JWT_USER_REDIS_PREFIX}:{user.id}')
        return count

    @staticmethod
    async def update_permission(*, db: AsyncSession, request: Request, pk: int, type: UserPermissionType) -> int:  # noqa: C901
        """
        Update user permission

        :param db: database session
        :param request: FastAPI request object
        :param pk: user ID
        :param type: permission type
        :return:
        """
        match type:
            case UserPermissionType.superuser:
                user = await user_dao.get(db, pk)
                if not user:
                    raise errors.NotFoundError(msg='User does not exist')
                if pk == request.user.id:
                    raise errors.ForbiddenError(msg='You cannot modify your own permissions')
                count = await user_dao.set_super(db, pk, is_super=not user.is_superuser)
            case UserPermissionType.staff:
                user = await user_dao.get(db, pk)
                if not user:
                    raise errors.NotFoundError(msg='User does not exist')
                if pk == request.user.id:
                    raise errors.ForbiddenError(msg='You cannot modify your own permissions')
                count = await user_dao.set_staff(db, pk, is_staff=not user.is_staff)
            case UserPermissionType.status:
                user = await user_dao.get(db, pk)
                if not user:
                    raise errors.NotFoundError(msg='User does not exist')
                if pk == request.user.id:
                    raise errors.ForbiddenError(msg='You cannot modify your own permissions')
                count = await user_dao.set_status(db, pk, 0 if user.status == 1 else 1)
            case UserPermissionType.multi_login:
                user = await user_dao.get(db, pk)
                if not user:
                    raise errors.NotFoundError(msg='User does not exist')
                multi_login = user.is_multi_login if pk != user.id else request.user.is_multi_login
                new_multi_login = not multi_login
                count = await user_dao.set_multi_login(db, pk, multi_login=new_multi_login)
                token = get_token(request)
                token_payload = jwt_decode(token)
                if pk == user.id:
                    # When an admin modifies their own account, invalidate every token but the current one
                    if not new_multi_login:
                        key_prefix = f'{settings.TOKEN_REDIS_PREFIX}:{user.id}'
                        await redis_client.delete_prefix(
                            key_prefix,
                            exclude=f'{key_prefix}:{token_payload.session_uuid}',
                        )
                else:
                    # When an admin modifies another user's account, invalidate all of that user's tokens
                    if not new_multi_login:
                        key_prefix = f'{settings.TOKEN_REDIS_PREFIX}:{user.id}'
                        await redis_client.delete_prefix(key_prefix)
            case _:
                raise errors.RequestError(msg='Permission type does not exist')

        await redis_client.delete(f'{settings.JWT_USER_REDIS_PREFIX}:{user.id}')
        return count

    @staticmethod
    async def reset_password(*, db: AsyncSession, pk: int, password: str) -> int:
        """
        Reset user password

        :param db: database session
        :param pk: user ID
        :param password: new password
        :return:
        """
        user = await user_dao.get(db, pk)
        if not user:
            raise errors.NotFoundError(msg='User does not exist')

        await validate_new_password(db, user.id, password)
        count = await user_dao.reset_password(db, user.id, password)

        history_obj = CreateUserPasswordHistoryParam(user_id=user.id, password=user.password)
        await password_security_service.save_password_history(db, history_obj)
        await user_dao.update_password_changed_time(db, user.id)

        key_prefix = [
            f'{settings.TOKEN_REDIS_PREFIX}:{user.id}',
            f'{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user.id}',
            f'{settings.JWT_USER_REDIS_PREFIX}:{user.id}',
        ]
        for prefix in key_prefix:
            await redis_client.delete_prefix(prefix)
        return count

    @staticmethod
    async def update_nickname(*, db: AsyncSession, user_id: int, nickname: str) -> int:
        """
        Update the current user's nickname

        :param db: database session
        :param user_id: user ID
        :param nickname: nickname
        :return:
        """
        count = await user_dao.update_nickname(db, user_id, nickname)
        await redis_client.delete(f'{settings.JWT_USER_REDIS_PREFIX}:{user_id}')
        return count

    @staticmethod
    async def update_avatar(*, db: AsyncSession, user_id: int, avatar: str) -> int:
        """
        Update the current user's avatar

        :param db: database session
        :param user_id: user ID
        :param avatar: avatar URL
        :return:
        """
        count = await user_dao.update_avatar(db, user_id, avatar)
        await redis_client.delete(f'{settings.JWT_USER_REDIS_PREFIX}:{user_id}')
        return count

    @staticmethod
    async def update_email(*, db: AsyncSession, user_id: int, captcha: str, email: str) -> int:
        """
        Update the current user's email

        :param db: database session
        :param user_id: user ID
        :param captcha: email verification code
        :param email: email address
        :return:
        """
        captcha_code = await redis_client.get(f'{settings.EMAIL_CAPTCHA_REDIS_PREFIX}:{ctx.ip}')
        if not captcha_code:
            raise errors.RequestError(msg='Verification code has expired, please request a new one')
        if captcha != captcha_code:
            raise errors.CustomError(error=CustomErrorCode.CAPTCHA_ERROR)
        await redis_client.delete(f'{settings.EMAIL_CAPTCHA_REDIS_PREFIX}:{ctx.ip}')
        count = await user_dao.update_email(db, user_id, email)
        await redis_client.delete(f'{settings.JWT_USER_REDIS_PREFIX}:{user_id}')
        return count

    @staticmethod
    async def update_password(*, db: AsyncSession, user_id: int, obj: ResetPasswordParam) -> int:
        """
        Update the current user's password

        :param db: database session
        :param user_id: user ID
        :param obj: password reset params
        :return:
        """
        user = await user_dao.get(db, user_id)

        if user.password and not password_verify(obj.old_password, user.password):
            raise errors.RequestError(msg='Incorrect current password')

        if obj.new_password != obj.confirm_password:
            raise errors.RequestError(msg='The two password entries do not match')

        await validate_new_password(db, user_id, obj.new_password)
        count = await user_dao.reset_password(db, user_id, obj.new_password)

        history_obj = CreateUserPasswordHistoryParam(user_id=user.id, password=user.password)
        await password_security_service.save_password_history(db, history_obj)
        await user_dao.update_password_changed_time(db, user.id)

        key_prefix = [
            f'{settings.TOKEN_REDIS_PREFIX}:{user_id}',
            f'{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user_id}',
            f'{settings.JWT_USER_REDIS_PREFIX}:{user_id}',
        ]
        for prefix in key_prefix:
            await redis_client.delete_prefix(prefix)
        return count

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        """
        Delete user

        :param db: database session
        :param pk: user ID
        :return:
        """
        user = await user_dao.get(db, pk)
        if not user:
            raise errors.NotFoundError(msg='User does not exist')
        count = await user_dao.delete(db, user.id)
        key_prefix = [
            f'{settings.TOKEN_REDIS_PREFIX}:{user.id}',
            f'{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user.id}',
            f'{settings.JWT_USER_REDIS_PREFIX}:{user.id}',
        ]
        for key in key_prefix:
            await redis_client.delete_prefix(key)
        return count


user_service: UserService = UserService()
