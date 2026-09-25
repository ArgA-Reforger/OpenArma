from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_login_log import login_log_dao
from backend.app.admin.schema.login_log import CreateLoginLogParam, DeleteLoginLogParam
from backend.common.context import ctx
from backend.common.log import log
from backend.common.pagination import paging_data
from backend.database.db import async_db_session


class LoginLogService:
    """Login log service class"""

    @staticmethod
    async def get_list(*, db: AsyncSession, username: str | None, status: int | None, ip: str | None) -> dict[str, Any]:
        """
        Get login log list

        :param db: database session
        :param username: username
        :param status: status
        :param ip: IP address
        :return:
        """
        log_select = await login_log_dao.get_select(username=username, status=status, ip=ip)
        return await paging_data(db, log_select)

    @staticmethod
    async def create(
        *,
        user_uuid: str,
        username: str,
        login_time: datetime,
        status: int,
        msg: str,
    ) -> None:
        """
        Create login log

        :param user_uuid: user UUID
        :param username: username
        :param login_time: login time
        :param status: status
        :param msg: message
        :return:
        """
        try:
            obj = CreateLoginLogParam(
                user_uuid=user_uuid,
                username=username,
                status=status,
                ip=ctx.ip,
                country=ctx.country,
                region=ctx.region,
                city=ctx.city,
                user_agent=ctx.user_agent,
                browser=ctx.browser,
                os=ctx.os,
                device=ctx.device,
                msg=msg,
                login_time=login_time,
            )
            # Create a separate database session for the background task
            async with async_db_session.begin() as db:
                await login_log_dao.create(db, obj)
        except Exception as e:
            log.error(f'Failed to create login log: {e}')

    @staticmethod
    async def delete(*, db: AsyncSession, obj: DeleteLoginLogParam) -> int:
        """
        Batch delete login logs

        :param db: database session
        :param obj: log ID list
        :return:
        """
        count = await login_log_dao.delete(db, obj.pks)
        return count

    @staticmethod
    async def delete_all(*, db: AsyncSession) -> None:
        """Clear all login logs"""
        await login_log_dao.delete_all(db)


login_log_service: LoginLogService = LoginLogService()
