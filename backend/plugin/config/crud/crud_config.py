from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.config.model import Config
from backend.plugin.config.schema.config import CreateConfigParam, UpdateConfigParam


class CRUDConfig(CRUDPlus[Config]):
    """System parameter config database operations"""

    async def get(self, db: AsyncSession, pk: int) -> Config | None:
        """
        Get parameter config detail

        :param db: Database session
        :param pk: Parameter config ID
        :return:
        """
        return await self.select_model_by_column(db, id=pk)

    async def get_all(self, db: AsyncSession, type: str) -> Sequence[Config | None]:
        """
        Get parameter config by type

        :param db: Database session
        :param type: Parameter config type
        :return:
        """
        return await self.select_models(db, type=type)

    async def get_by_key(self, db: AsyncSession, key: str) -> Config | None:
        """
        Get parameter config by key

        :param db: Database session
        :param key: Parameter config key
        :return:
        """
        return await self.select_model_by_column(db, key=key)

    async def get_select(self, name: str | None, type: str | None) -> Select:
        """
        Get the query expression for the parameter config list

        :param name: Parameter config name
        :param type: Parameter config type
        :return:
        """
        filters = {}

        if name is not None:
            filters['name__like'] = f'%{name}%'
        if type is not None:
            filters['type__like'] = f'%{type}%'

        return await self.select_order('created_time', 'desc', **filters)

    async def create(self, db: AsyncSession, obj: CreateConfigParam) -> None:
        """
        Create parameter config

        :param db: Database session
        :param obj: Create parameter config parameters
        :return:
        """
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateConfigParam) -> int:
        """
        Update parameter config

        :param db: Database session
        :param pk: Parameter config ID
        :param obj: Update parameter config parameters
        :return:
        """
        return await self.update_model(db, pk, obj)

    async def bulk_update(self, db: AsyncSession, objs: list[UpdateConfigParam]) -> int:
        """
        Batch update parameter configs

        :param db: Database session
        :param objs: Batch update parameter config parameters
        :return:
        """
        return await self.bulk_update_models(db, objs)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """
        Batch delete parameter configs

        :param db: Database session
        :param pks: List of parameter config IDs
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


config_dao: CRUDConfig = CRUDConfig(Config)
