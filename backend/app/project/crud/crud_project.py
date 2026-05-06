from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.project.model import Project
from backend.app.project.schema.project import CreateProjectParam, UpdateProjectParam


class CRUDProject(CRUDPlus[Project]):
    """项目数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> Project | None:
        return await self.select_model_by_column(db, id=pk, del_flag=False)

    async def get_list(self, owner_id: int, name: str | None, status: str | None) -> Select:
        filters: dict = {'owner_id': owner_id, 'del_flag': False}
        if name is not None:
            filters['name__like'] = f'%{name}%'
        if status is not None:
            filters['status'] = status
        return await self.select_order('id', 'desc', **filters)

    async def get_by_api_key(self, db: AsyncSession, api_key: str) -> Project | None:
        return await self.select_model_by_column(db, api_key=api_key, del_flag=False)

    async def create(self, db: AsyncSession, obj: CreateProjectParam, owner_id: int) -> Project:
        create_data = obj.model_dump()
        create_data['owner_id'] = owner_id
        instance = self.model(**create_data)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def update(self, db: AsyncSession, pk: int, obj: UpdateProjectParam) -> int:
        return await self.update_model(db, pk, obj.model_dump(exclude_unset=True))

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(db, id=pk, logical_deletion=True, deleted_flag_column='del_flag')


project_dao: CRUDProject = CRUDProject(Project)
