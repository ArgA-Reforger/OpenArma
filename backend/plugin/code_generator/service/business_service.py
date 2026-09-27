from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.plugin.code_generator.crud.crud_business import gen_business_dao
from backend.plugin.code_generator.model import GenBusiness
from backend.plugin.code_generator.schema.business import CreateGenBusinessParam, UpdateGenBusinessParam


class GenBusinessService:
    """Code generator business service"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> GenBusiness:
        """
        Get the business with the given ID

        :param db: Database session
        :param pk: Business ID
        :return:
        """

        business = await gen_business_dao.get(db, pk)
        if not business:
            raise errors.NotFoundError(msg='Code generator business does not exist')
        return business

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[GenBusiness]:
        """
        Get all businesses

        :param db: Database session
        :return:
        """

        return await gen_business_dao.get_all(db)

    @staticmethod
    async def get_list(*, db: AsyncSession, table_name: str) -> dict[str, Any]:
        """
        Get the code generator business list

        :param db: Database session
        :param table_name: Business table name
        :return:
        """
        business_select = await gen_business_dao.get_select(table_name=table_name)
        return await paging_data(db, business_select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateGenBusinessParam) -> None:
        """
        Create business

        :param db: Database session
        :param obj: Create business parameters
        :return:
        """

        business = await gen_business_dao.get_by_name(db, obj.table_name)
        if business:
            raise errors.ConflictError(msg='Code generator business already exists')
        await gen_business_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateGenBusinessParam) -> int:
        """
        Update business

        :param db: Database session
        :param pk: Business ID
        :param obj: Update business parameters
        :return:
        """

        return await gen_business_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        """
        Delete business

        :param db: Database session
        :param pk: Business ID
        :return:
        """

        return await gen_business_dao.delete(db, pk)


gen_business_service: GenBusinessService = GenBusinessService()
