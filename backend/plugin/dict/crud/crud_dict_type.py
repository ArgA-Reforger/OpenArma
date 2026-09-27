from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.dict.crud.crud_dict_data import dict_data_dao
from backend.plugin.dict.model import DictType
from backend.plugin.dict.schema.dict_type import CreateDictTypeParam, UpdateDictTypeParam


class CRUDDictType(CRUDPlus[DictType]):
    """Dict type database operations"""

    async def get(self, db: AsyncSession, pk: int) -> DictType | None:
        """
        Get dict type detail

        :param db: Database session
        :param pk: Dict type ID
        :return:
        """
        return await self.select_model(db, pk)

    async def get_all(self, db: AsyncSession) -> Sequence[DictType]:
        """
        Get all dict types

        :param db: Database session
        :return:
        """
        return await self.select_models(db)

    async def get_select(self, name: str | None, code: str | None) -> Select:
        """
        Get the query expression for the dict type list

        :param name: Dict type name
        :param code: Dict type code
        :return:
        """
        filters = {}

        if name is not None:
            filters['name__like'] = f'%{name}%'
        if code is not None:
            filters['code__like'] = f'%{code}%'

        return await self.select_order('id', 'desc', **filters)

    async def get_by_code(self, db: AsyncSession, code: str) -> DictType | None:
        """
        Get dict type by code

        :param db: Database session
        :param code: Dict code
        :return:
        """
        return await self.select_model_by_column(db, code=code)

    async def create(self, db: AsyncSession, obj: CreateDictTypeParam) -> None:
        """
        Create dict type

        :param db: Database session
        :param obj: Create dict type parameters
        :return:
        """
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateDictTypeParam) -> int:
        """
        Update dict type

        :param db: Database session
        :param pk: Dict type ID
        :param obj: Update dict type parameters
        :return:
        """
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """
        Batch delete dict types

        :param db: Database session
        :param pks: List of dict type IDs
        :return:
        """
        await dict_data_dao.delete_by_type_id(db, pks)
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


dict_type_dao: CRUDDictType = CRUDDictType(DictType)
