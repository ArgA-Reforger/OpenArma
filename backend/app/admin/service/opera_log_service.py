from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_opera_log import opera_log_dao
from backend.app.admin.schema.opera_log import CreateOperaLogParam, DeleteOperaLogParam
from backend.common.pagination import paging_data


class OperaLogService:
    """Operation log service class"""

    @staticmethod
    async def get_list(*, db: AsyncSession, username: str | None, status: int | None, ip: str | None) -> dict[str, Any]:
        """
        Get operation log list

        :param db: database session
        :param username: username
        :param status: status
        :param ip: IP address
        :return:
        """
        log_select = await opera_log_dao.get_select(username=username, status=status, ip=ip)
        return await paging_data(db, log_select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateOperaLogParam) -> None:
        """
        Create operation log

        :param db: database session
        :param obj: operation log creation params
        :return:
        """
        await opera_log_dao.create(db, obj)

    @staticmethod
    async def bulk_create(*, db: AsyncSession, objs: list[CreateOperaLogParam]) -> None:
        """
        Bulk create operation logs

        :param db: database session
        :param objs: list of operation log creation params
        :return:
        """
        await opera_log_dao.bulk_create(db, objs)

    @staticmethod
    async def delete(*, db: AsyncSession, obj: DeleteOperaLogParam) -> int:
        """
        Batch delete operation logs

        :param db: database session
        :param obj: log ID list
        :return:
        """
        count = await opera_log_dao.delete(db, obj.pks)
        return count

    @staticmethod
    async def delete_all(*, db: AsyncSession) -> None:
        """
        Clear all operation logs

        :param db: database session
        :return:
        """
        await opera_log_dao.delete_all(db)


opera_log_service: OperaLogService = OperaLogService()
