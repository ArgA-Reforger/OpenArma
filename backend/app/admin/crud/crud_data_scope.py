from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, delete, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus, JoinConfig

from backend.app.admin.model import DataRule, DataScope, data_scope_rule
from backend.app.admin.schema.data_scope import (
    CreateDataScopeParam,
    CreateDataScopeRuleParam,
    UpdateDataScopeParam,
    UpdateDataScopeRuleParam,
)
from backend.utils.serializers import select_join_serialize


class CRUDDataScope(CRUDPlus[DataScope]):
    """Data scope database operations"""

    async def get(self, db: AsyncSession, pk: int) -> DataScope | None:
        """
        Get data scope detail

        :param db: database session
        :param pk: scope ID
        :return:
        """
        return await self.select_model(db, pk)

    async def get_by_name(self, db: AsyncSession, name: str) -> DataScope | None:
        """
        Get a data scope by name

        :param db: database session
        :param name: scope name
        :return:
        """
        return await self.select_model_by_column(db, name=name)

    async def get_join(self, db: AsyncSession, pk: int) -> Any:
        """
        Get data scope relational data

        :param db: database session
        :param pk: scope ID
        :return:
        """
        result = await self.select_models(
            db,
            id=pk,
            join_conditions=[
                JoinConfig(model=data_scope_rule, join_on=data_scope_rule.c.data_scope_id == self.model.id),
                JoinConfig(model=DataRule, join_on=DataRule.id == data_scope_rule.c.data_rule_id, fill_result=True),
            ],
        )

        return select_join_serialize(result, relationships=['DataScope-m2m-DataRule:rules'])

    async def get_all(self, db: AsyncSession) -> Sequence[DataScope]:
        """
        Get all data scopes

        :param db: database session
        :return:
        """
        return await self.select_models(db)

    async def get_select(self, name: str | None, status: int | None) -> Select:
        """
        Get the query expression for the data scope list

        :param name: scope name
        :param status: scope status
        :return:
        """
        filters = {}

        if name is not None:
            filters['name__like'] = f'%{name}%'
        if status is not None:
            filters['status'] = status

        return await self.select_order('id', **filters)

    async def create(self, db: AsyncSession, obj: CreateDataScopeParam) -> None:
        """
        Create data scope

        :param db: database session
        :param obj: data scope creation params
        :return:
        """
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateDataScopeParam) -> int:
        """
        Update data scope

        :param db: database session
        :param pk: scope ID
        :param obj: data scope update params
        :return:
        """
        return await self.update_model(db, pk, obj)

    @staticmethod
    async def update_rules(db: AsyncSession, pk: int, rule_ids: UpdateDataScopeRuleParam) -> int:
        """
        Update data scope rules

        :param db: database session
        :param pk: scope ID
        :param rule_ids: data rule ID list
        :return:
        """
        data_scope_rule_stmt = delete(data_scope_rule).where(data_scope_rule.c.data_scope_id == pk)
        await db.execute(data_scope_rule_stmt)

        if rule_ids.rules:
            data_scope_rule_data = [
                CreateDataScopeRuleParam(data_scope_id=pk, data_rule_id=rule_id).model_dump()
                for rule_id in rule_ids.rules
            ]
            data_scope_rule_stmt = insert(data_scope_rule)
            await db.execute(data_scope_rule_stmt, data_scope_rule_data)

        return len(rule_ids.rules)

    async def delete(self, db: AsyncSession, pks: list[int]) -> int:
        """
        Batch delete data scopes

        :param db: database session
        :param pks: scope ID list
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


data_scope_dao: CRUDDataScope = CRUDDataScope(DataScope)
