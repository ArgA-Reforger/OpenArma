from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.builtin_tool.schema.builtin_tool import (
    CreateBuiltinToolParam,
    GetBuiltinToolDetail,
    UpdateBuiltinToolParam,
)
from backend.app.builtin_tool.service.builtin_tool_service import builtin_tool_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth, DependsSuperUser
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('', summary='内置工具列表', dependencies=[DependsJwtAuth, DependsPagination])
async def get_builtin_tools(
    db: CurrentSession,
) -> ResponseSchemaModel[PageData[GetBuiltinToolDetail]]:
    """获取所有内置工具（管理员用）。"""
    page_data = await builtin_tool_service.get_list(db=db)
    return response_base.success(data=page_data)


@router.get('/active', summary='可用内置工具列表', dependencies=[DependsJwtAuth])
async def get_active_builtin_tools(
    db: CurrentSession,
    category: Annotated[str | None, Query(description='逗号分隔的分类过滤，如 general,arma')] = None,
) -> ResponseSchemaModel[list[GetBuiltinToolDetail]]:
    """获取所有启用的内置工具（用户端 Agent 配置用）。"""
    categories = [c.strip() for c in category.split(',') if c.strip()] if category else None
    tools = await builtin_tool_service.get_active_tools(db=db, categories=categories)
    return response_base.success(data=tools)


@router.get('/{pk}', summary='内置工具详情', dependencies=[DependsJwtAuth])
async def get_builtin_tool(
    db: CurrentSession,
    pk: Annotated[int, Path(description='工具 ID')],
) -> ResponseSchemaModel[GetBuiltinToolDetail]:
    data = await builtin_tool_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.post('', summary='创建内置工具', dependencies=[DependsJwtAuth, DependsSuperUser])
async def create_builtin_tool(
    db: CurrentSessionTransaction,
    obj: CreateBuiltinToolParam,
) -> ResponseSchemaModel[GetBuiltinToolDetail]:
    data = await builtin_tool_service.create(db=db, obj=obj)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新内置工具', dependencies=[DependsJwtAuth, DependsSuperUser])
async def update_builtin_tool(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='工具 ID')],
    obj: UpdateBuiltinToolParam,
) -> ResponseModel:
    count = await builtin_tool_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/{pk}', summary='删除内置工具', dependencies=[DependsJwtAuth, DependsSuperUser])
async def delete_builtin_tool(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='工具 ID')],
) -> ResponseModel:
    count = await builtin_tool_service.delete(db=db, pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()
