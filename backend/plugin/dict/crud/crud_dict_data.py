from collections.abc import Sequence

from sqlalchemy import Select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.dict.model import DictData
from backend.plugin.dict.schema.dict_data import CreateDictDataParam, UpdateDictDataParam


class CRUDDictData(CRUDPlus[DictData]):
    """Dict data database operations"""

    async def get(self, db: AsyncSession, pk: int) -> DictData | None:
        """
        Get dict data detail

        :param db: Database session
        :param pk: Dict data ID
        :return:
        """
        return await self.select_model(db, pk)

    async def get_by_type_code(self, db: AsyncSession, type_code: str) -> Sequence[DictData]:
        """
        Get dict data by dict type code

        :param db: Database session
        :param type_code: Dict type code
        :return:
        """
        return await self.select_models_order(
            db,
            sort_columns='sort',
            sort_orders='desc',
            type_code=type_code,
        )

    async def get_all(self, db: AsyncSession) -> Sequence[DictData]:
        """
        Get all dict data

        :param db: Database session
        :return:
        """
        return await self.select_models(db)

    async def get_select(
        self,
        type_code: str | None,
        label: str | None,
        value: str | None,
        status: int | None,
        type_id: int | None,
    ) -> Select:
        """
        Get the query expression for the dict data list

        :param type_code: Dict type code
        :param label: Dict data label
        :param value: Dict data value
        :param status: Dict status
        :param type_id: Dict type ID
        :return:
        """
        filters = {}

        if type_code is not None:
            filters['type_code'] = type_code
        if label is not None:
            filters['label__like'] = f'%{label}%'
        if value is not None:
            filters['value__like'] = f'%{value}%'
        if status is not None:
            filters['status'] = status
        if type_id is not None:
            filters['type_id'] = type_id

        return await self.select_order('sort', 'asc', **filters)

    async def get_by_label_and_type_code(self, db: AsyncSession, label: str, type_code: str) -> DictData | None:
        """
        Get dict data by label

        :param db: Database session
        :param label: Dict label
        :param type_code: Dict type code
        :return:
        """
        return await self.select_model_by_column(db, and_(self.model.label == label, self.model.type_code == type_code))

    async def create(self, db: AsyncSession, obj: CreateDictDataParam, type_code: str) -> None:
        """
        Create dict data

        :param db: Database session
        :param obj: Create dict data parameters
        :param type_code: Dict type code
        :return:
        """
        dict_obj = obj.model_dump()
        dict_obj.update({'type_code': type_code})
        new_data = self.model(**dict_obj)
        db.add(new_data)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateDictDataParam, type_code: str) -> int:
        """
        Update dict data

        :param db: Database session
        :param pk: Dict data ID
        :param obj: Update dict data parameters
        :param type_code: Dict type code
        :return:
        """
        dict_obj = obj.model_dump()
        dict_obj.update({'type_code': type_code})
        return await self.update_model(db, pk, dict_obj)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """
        Batch delete dict data

        :param db: Database session
        :param pks: List of dict data IDs
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)

    async def delete_by_type_id(self, db: AsyncSession, type_ids: list[int]) -> int:
        """
        Delete dict data by type ID

        :param db: Database session
        :param type_ids: List of dict type IDs
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, type_id__in=type_ids)


dict_data_dao: CRUDDictData = CRUDDictData(DictData)
