from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.project.crud.crud_project import project_dao
from backend.app.project.model import Project
from backend.app.project.schema.project import CreateProjectParam, UpdateProjectParam
from backend.common.exception import errors
from backend.common.pagination import paging_data


class ProjectService:
    """项目服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int, owner_id: int) -> Project:
        project = await project_dao.get(db, pk)
        if not project:
            raise errors.NotFoundError(msg='项目不存在')
        if project.owner_id != owner_id:
            raise errors.NotFoundError(msg='项目不存在')
        return project

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        owner_id: int,
        name: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        project_select = await project_dao.get_list(owner_id=owner_id, name=name, status=status)
        return await paging_data(db, project_select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateProjectParam, owner_id: int) -> Project:
        if obj.api_key and await project_dao.get_by_api_key(db, obj.api_key):
            raise errors.ConflictError(msg='API Key 已存在')
        return await project_dao.create(db, obj, owner_id=owner_id)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateProjectParam, owner_id: int) -> int:
        project = await project_dao.get(db, pk)
        if not project:
            raise errors.NotFoundError(msg='项目不存在')
        if project.owner_id != owner_id:
            raise errors.NotFoundError(msg='项目不存在')
        if obj.api_key is not None and obj.api_key != project.api_key:
            if await project_dao.get_by_api_key(db, obj.api_key):
                raise errors.ConflictError(msg='API Key 已存在')
        return await project_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int, owner_id: int) -> int:
        project = await project_dao.get(db, pk)
        if not project:
            raise errors.NotFoundError(msg='项目不存在')
        if project.owner_id != owner_id:
            raise errors.NotFoundError(msg='项目不存在')
        return await project_dao.delete(db, pk)


project_service: ProjectService = ProjectService()
