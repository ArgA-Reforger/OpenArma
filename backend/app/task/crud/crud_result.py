from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.task.model import TaskResult


class CRUDTaskResult(CRUDPlus[TaskResult]):
    """Task result database operations class"""

    async def get(self, db: AsyncSession, pk: int) -> TaskResult | None:
        """
        Get task result details

        :param db: database session
        :param pk: task ID
        :return:
        """
        return await self.select_model(db, pk)

    async def get_select(self, name: str | None, task_id: str | None) -> Select:
        """
        Get the query expression for the task result list

        :param name: task name
        :param task_id: task ID
        :return:
        """
        filters = {}

        if name is not None:
            filters['name__like'] = f'%{name}%'
        if task_id is not None:
            filters['task_id'] = task_id

        return await self.select_order('id', 'desc', **filters)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """
        Batch delete task results

        :param db: database session
        :param pks: list of task result IDs
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


task_result_dao: CRUDTaskResult = CRUDTaskResult(TaskResult)
