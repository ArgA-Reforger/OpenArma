from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.app.mcp.schema.mcp_server import CreateMCPServerParam, GetMCPServerDetail, UpdateMCPServerParam
from backend.app.mcp.schema.mcp_tool import GetMCPToolDetail
from backend.app.mcp.service.mcp_server_service import mcp_server_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.post('', summary='注册 MCP 服务器', dependencies=[DependsJwtAuth])
async def create_mcp_server(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateMCPServerParam,
) -> ResponseSchemaModel[GetMCPServerDetail]:
    server = await mcp_server_service.create(db=db, obj=obj, user_id=request.user.id)
    data = GetMCPServerDetail.model_validate(server)
    return response_base.success(data=data)


@router.get(
    '',
    summary='MCP 服务器列表',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_mcp_servers(
    db: CurrentSession,
    request: Request,
    visibility: Annotated[str | None, Query(description='可见性过滤: private/public/official')] = None,
) -> ResponseSchemaModel[PageData[GetMCPServerDetail]]:
    page_data = await mcp_server_service.get_list(db=db, user_id=request.user.id, visibility=visibility)
    return response_base.success(data=page_data)


@router.get('/{pk}', summary='MCP 服务器详情', dependencies=[DependsJwtAuth])
async def get_mcp_server(
    db: CurrentSession,
    request: Request,
    pk: Annotated[int, Path(description='主键 ID')],
) -> ResponseSchemaModel[GetMCPServerDetail]:
    data = await mcp_server_service.get(db=db, pk=pk, user_id=request.user.id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新 MCP 服务器', dependencies=[DependsJwtAuth])
async def update_mcp_server(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='主键 ID')],
    obj: UpdateMCPServerParam,
) -> ResponseModel:
    count = await mcp_server_service.update(db=db, pk=pk, obj=obj, user_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/{pk}', summary='删除 MCP 服务器', dependencies=[DependsJwtAuth])
async def delete_mcp_server(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='主键 ID')],
) -> ResponseModel:
    count = await mcp_server_service.delete(db=db, pk=pk, user_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{pk}/discover', summary='发现工具', dependencies=[DependsJwtAuth])
async def discover_mcp_tools(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='主键 ID')],
) -> ResponseSchemaModel[list[GetMCPToolDetail]]:
    tools = await mcp_server_service.discover(db=db, pk=pk, user_id=request.user.id)
    return response_base.success(data=tools)


@router.post('/{pk}/clone', summary='克隆 MCP 服务器', dependencies=[DependsJwtAuth])
async def clone_mcp_server(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='源 MCP 服务器 ID')],
) -> ResponseSchemaModel[GetMCPServerDetail]:
    server = await mcp_server_service.clone(db=db, pk=pk, user_id=request.user.id)
    data = GetMCPServerDetail.model_validate(server)
    return response_base.success(data=data)
