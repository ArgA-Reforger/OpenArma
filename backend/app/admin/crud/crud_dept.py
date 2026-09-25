from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus, JoinConfig

from backend.app.admin.model import Dept, User
from backend.app.admin.schema.dept import CreateDeptParam, UpdateDeptParam
from backend.utils.serializers import select_join_serialize


class CRUDDept(CRUDPlus[Dept]):
    """Department database operations"""

    async def get(self, db: AsyncSession, dept_id: int) -> Dept | None:
        """
        Get department detail

        :param db: database session
        :param dept_id: department ID
        :return:
        """
        return await self.select_model_by_column(db, id=dept_id, del_flag=False)

    async def get_by_name(self, db: AsyncSession, name: str) -> Dept | None:
        """
        Get a department by name

        :param db: database session
        :param name: department name
        :return:
        """
        return await self.select_model_by_column(db, name=name, del_flag=False)

    async def get_all(
        self,
        db: AsyncSession,
        data_filter: ColumnElement[bool],
        name: str | None,
        leader: str | None,
        phone: str | None,
        status: int | None,
    ) -> Sequence[Dept]:
        """
        Get all departments

        :param db: database session
        :param data_filter: requesting user
        :param name: department name
        :param leader: leader
        :param phone: contact phone number
        :param status: department status
        :return:
        """
        filters = {'del_flag': False}

        if name is not None:
            filters['name__like'] = f'%{name}%'
        if leader is not None:
            filters['leader__like'] = f'%{leader}%'
        if phone is not None:
            filters['phone__startswith'] = phone
        if status is not None:
            filters['status'] = status

        return await self.select_models_order(db, 'sort', 'asc', data_filter, **filters)

    async def create(self, db: AsyncSession, obj: CreateDeptParam) -> None:
        """
        Create department

        :param db: database session
        :param obj: department creation params
        :return:
        """
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, dept_id: int, obj: UpdateDeptParam) -> int:
        """
        Update department

        :param db: database session
        :param dept_id: department ID
        :param obj: department update params
        :return:
        """
        return await self.update_model(db, dept_id, obj)

    async def delete(self, db: AsyncSession, dept_id: int) -> int:
        """
        Delete department

        :param db: database session
        :param dept_id: department ID
        :return:
        """
        return await self.delete_model_by_column(db, id=dept_id, logical_deletion=True, deleted_flag_column='del_flag')

    async def get_join(self, db: AsyncSession, dept_id: int) -> Any | None:
        """
        Get department with related data

        :param db: database session
        :param dept_id: department ID
        :return:
        """
        result = await self.select_model(
            db,
            dept_id,
            join_conditions=[JoinConfig(model=User, join_on=User.dept_id == self.model.id, fill_result=True)],
        )
        return select_join_serialize(result, relationships=['Dept-o2m-User'])

    async def get_children(self, db: AsyncSession, dept_id: int) -> Sequence[Dept | None]:
        """
        Get sub-department list

        :param db: database session
        :param dept_id: department ID
        :return:
        """
        return await self.select_models(db, parent_id=dept_id, del_flag=False)


dept_dao: CRUDDept = CRUDDept(Dept)
