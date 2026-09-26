from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.cache.decorator import cache_invalidate, cached
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.core.conf import settings
from backend.plugin.config.crud.crud_config import config_dao
from backend.plugin.config.model import Config
from backend.plugin.config.schema.config import (
    CreateConfigParam,
    UpdateConfigParam,
    UpdateConfigsParam,
)


class ConfigService:
    """Parameter config service"""

    @staticmethod
    @cached(settings.CACHE_CONFIG_REDIS_PREFIX, key='pk')
    async def get(*, db: AsyncSession, pk: int) -> Config:
        """
        Get parameter config detail

        :param db: Database session
        :param pk: Parameter config ID
        :return:
        """
        config = await config_dao.get(db, pk)
        if not config:
            raise errors.NotFoundError(msg='Parameter config does not exist')
        return config

    @staticmethod
    @cached(settings.CACHE_CONFIG_REDIS_PREFIX, key='type')
    async def get_all(*, db: AsyncSession, type: str | None) -> Sequence[Config | None]:
        """
        Get all parameter configs

        :param db: Database session
        :param type: Parameter config type
        :return:
        """
        return await config_dao.get_all(db, type)

    @staticmethod
    async def get_list(*, db: AsyncSession, name: str | None, type: str | None) -> dict[str, Any]:
        """
        Get parameter config list

        :param db: Database session
        :param name: Parameter config name
        :param type: Parameter config type
        :return:
        """
        config_select = await config_dao.get_select(name=name, type=type)
        return await paging_data(db, config_select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateConfigParam) -> None:
        """
        Create parameter config

        :param db: Database session
        :param obj: Create parameter config parameters
        :return:
        """
        config = await config_dao.get_by_key(db, obj.key)
        if config:
            raise errors.ConflictError(msg=f'Parameter config {obj.key} already exists')
        await config_dao.create(db, obj)

    @staticmethod
    @cache_invalidate(settings.CACHE_CONFIG_REDIS_PREFIX)
    async def update(*, db: AsyncSession, pk: int, obj: UpdateConfigParam) -> int:
        """
        Update parameter config

        :param db: Database session
        :param pk: Parameter config ID
        :param obj: Update parameter config parameters
        :return:
        """
        config = await config_dao.get(db, pk)
        if not config:
            raise errors.NotFoundError(msg='Parameter config does not exist')
        if config.key != obj.key:
            config = await config_dao.get_by_key(db, obj.key)
            if config:
                raise errors.ConflictError(msg=f'Parameter config {obj.key} already exists')
        count = await config_dao.update(db, pk, obj)
        return count

    @staticmethod
    @cache_invalidate(settings.CACHE_CONFIG_REDIS_PREFIX)
    async def bulk_update(*, db: AsyncSession, objs: list[UpdateConfigsParam]) -> int:
        """
        Batch update parameter configs

        :param db: Database session
        :param objs: Batch update parameter config parameters
        :return:
        """
        for _batch in range(0, len(objs), 1000):
            for obj in objs:
                config = await config_dao.get(db, obj.id)
                if not config:
                    raise errors.NotFoundError(msg='Parameter config does not exist')
                if config.key != obj.key:
                    config = await config_dao.get_by_key(db, obj.key)
                    if config:
                        raise errors.ConflictError(msg=f'Parameter config {obj.key} already exists')
        count = await config_dao.bulk_update(db, objs)
        return count

    @staticmethod
    @cache_invalidate(settings.CACHE_CONFIG_REDIS_PREFIX)
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        """
        Batch delete parameter configs

        :param db: Database session
        :param pks: List of parameter config IDs
        :return:
        """
        count = await config_dao.delete(db, pks)
        return count


config_service: ConfigService = ConfigService()
