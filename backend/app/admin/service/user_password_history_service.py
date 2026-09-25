import math

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_user_password_history import user_password_history_dao
from backend.app.admin.schema.user_password_history import CreateUserPasswordHistoryParam
from backend.common.exception import errors
from backend.core.conf import settings
from backend.database.redis import redis_client
from backend.utils.dynamic_config import load_user_security_config
from backend.utils.timezone import timezone


class UserPasswordHistoryService:
    """User password history service class"""

    @staticmethod
    async def check_status(user_id: int, user_status: int) -> None:
        """
        Check user status

        :param user_id: user ID
        :param user_status: user status
        :return:
        """
        if not user_status:
            raise errors.AuthorizationError(msg='This user has been locked, please contact an administrator')

        locked_until_str = await redis_client.get(f'{settings.USER_LOCK_REDIS_PREFIX}:{user_id}')

        if locked_until_str:
            locked_until = timezone.from_str(locked_until_str)
            now = timezone.now()
            if locked_until > now:
                remaining_minutes = math.ceil((locked_until - now).total_seconds() / 60)
                raise errors.AuthorizationError(msg=f'Account is locked, please try again in {remaining_minutes} minutes')

            await redis_client.delete(f'{settings.USER_LOCK_REDIS_PREFIX}:{user_id}')
            await redis_client.delete(f'{settings.LOGIN_FAILURE_PREFIX}:{user_id}')

    @staticmethod
    async def handle_login_failure(db: AsyncSession, user_id: int) -> None:
        """
        Handle login failure

        :param db: database session
        :param user_id: user ID
        :return:
        """
        await load_user_security_config(db)

        if settings.USER_LOCK_THRESHOLD == 0:
            return

        failure_count = await redis_client.get(f'{settings.LOGIN_FAILURE_PREFIX}:{user_id}')
        failure_count = int(failure_count) if failure_count else 0
        failure_count += 1
        await redis_client.setex(
            f'{settings.LOGIN_FAILURE_PREFIX}:{user_id}',
            settings.USER_LOCK_SECONDS,
            str(failure_count),
        )

        if failure_count >= settings.USER_LOCK_THRESHOLD:
            locked_until = timezone.now() + timedelta(seconds=settings.USER_LOCK_SECONDS)
            await redis_client.setex(
                f'{settings.USER_LOCK_REDIS_PREFIX}:{user_id}',
                settings.USER_LOCK_SECONDS,
                timezone.to_str(locked_until),
            )
            raise errors.AuthorizationError(msg='Too many failed login attempts, account has been locked')

    @staticmethod
    async def check_password_expiry_status(db: AsyncSession, password_changed_time: datetime) -> int | None:
        """
        Check password expiry status

        :param db: database session
        :param password_changed_time: password change time
        :return:
        """
        await load_user_security_config(db)

        if settings.USER_PASSWORD_EXPIRY_DAYS == 0:
            return None

        if not password_changed_time:
            raise errors.AuthorizationError(msg='Password has expired, please change it and log in again')

        expiry_time = password_changed_time + timedelta(days=settings.USER_PASSWORD_EXPIRY_DAYS)
        days_remaining = (expiry_time - timezone.now()).days

        if days_remaining < 0:
            raise errors.AuthorizationError(msg='Password has expired, please change it and log in again')

        if days_remaining <= settings.USER_PASSWORD_REMINDER_DAYS:
            return days_remaining

        return None

    @staticmethod
    async def handle_login_success(user_id: int) -> None:
        """
        Handle login success

        :param user_id: user ID
        :return:
        """
        await redis_client.delete(f'{settings.USER_LOCK_REDIS_PREFIX}:{user_id}')
        await redis_client.delete(f'{settings.LOGIN_FAILURE_PREFIX}:{user_id}')

    @staticmethod
    async def save_password_history(db: AsyncSession, obj: CreateUserPasswordHistoryParam) -> None:
        """
        Save password history record

        :param db: database session
        :param obj: password history record creation params
        :return:
        """
        await user_password_history_dao.create(db, obj)


password_security_service: UserPasswordHistoryService = UserPasswordHistoryService()
