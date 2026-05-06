from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.builtin_tool.crud.crud_builtin_tool import builtin_tool_dao
from backend.app.builtin_tool.model import BuiltinTool
from backend.app.builtin_tool.schema.builtin_tool import CreateBuiltinToolParam, UpdateBuiltinToolParam
from backend.common.exception import errors
from backend.common.pagination import paging_data


class BuiltinToolService:
    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> BuiltinTool:
        obj = await builtin_tool_dao.get(db, pk)
        if not obj:
            raise errors.NotFoundError(msg='内置工具不存在')
        return obj

    @staticmethod
    async def get_list(*, db: AsyncSession) -> dict[str, Any]:
        select_stmt = await builtin_tool_dao.get_list()
        return await paging_data(db, select_stmt)

    @staticmethod
    async def get_active_tools(*, db: AsyncSession, categories: list[str] | None = None) -> list[BuiltinTool]:
        return await builtin_tool_dao.get_active_list(db, categories=categories)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateBuiltinToolParam) -> BuiltinTool:
        existing = await builtin_tool_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.RequestError(msg=f'工具名 {obj.name} 已存在')
        return await builtin_tool_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateBuiltinToolParam) -> int:
        tool = await builtin_tool_dao.get(db, pk)
        if not tool:
            raise errors.NotFoundError(msg='内置工具不存在')
        return await builtin_tool_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int) -> int:
        tool = await builtin_tool_dao.get(db, pk)
        if not tool:
            raise errors.NotFoundError(msg='内置工具不存在')
        if tool.is_system:
            raise errors.RequestError(msg='系统预置工具不可删除')
        return await builtin_tool_dao.delete(db, pk)


builtin_tool_service: BuiltinToolService = BuiltinToolService()
