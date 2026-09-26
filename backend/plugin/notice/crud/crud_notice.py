from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.notice.model import Notice
from backend.plugin.notice.schema.notice import CreateNoticeParam, UpdateNoticeParam


class CRUDNotice(CRUDPlus[Notice]):
    """Notice database operations"""

    async def get(self, db: AsyncSession, pk: int) -> Notice | None:
        """
        Get notice

        :param db: Database session
        :param pk: Notice ID
        :return:
        """
        return await self.select_model(db, pk)

    async def get_select(self, title: str, type: int | None, status: int | None) -> Select:
        """
        Get the query expression for the notice list

        :param title: Notice title
        :param type: Notice type
        :param status: Notice status
        :return:
        """
        filters = {}

        if title is not None:
            filters['title__like'] = f'%{title}%'
        if type is not None:
            filters['type'] = type
        if status is not None:
            filters['status'] = status

        return await self.select_order('created_time', 'desc', **filters)

    async def get_all(self, db: AsyncSession) -> Sequence[Notice]:
        """
        Get all notices

        :param db: Database session
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj: CreateNoticeParam) -> None:
        """
        Create notice

        :param db: Database session
        :param obj: Create notice parameters
        :return:
        """
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateNoticeParam) -> int:
        """
        Update notice

        :param db: Database session
        :param pk: Notice ID
        :param obj: Update notice parameters
        :return:
        """
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """
        Batch delete notices

        :param db: Database session
        :param pks: List of notice IDs
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


notice_dao: CRUDNotice = CRUDNotice(Notice)
