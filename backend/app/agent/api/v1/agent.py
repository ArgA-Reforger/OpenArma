from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.app.agent.schema.agent import CreateAgentParam, GetAgentDetail, UpdateAgentParam
from backend.app.agent.service.agent_service import agent_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.post('', summary='创建 Agent', dependencies=[DependsJwtAuth])
async def create_agent(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateAgentParam,
) -> ResponseSchemaModel[GetAgentDetail]:
    data = await agent_service.create(db=db, obj=obj, user_id=request.user.id)
    return response_base.success(data=data)


@router.get('', summary='Agent 列表', dependencies=[DependsJwtAuth, DependsPagination])
async def get_agents(
    db: CurrentSession,
    request: Request,
    visibility: Annotated[str | None, Query(description='可见性过滤: private/public/official')] = None,
) -> ResponseSchemaModel[PageData[GetAgentDetail]]:
    page_data = await agent_service.get_list(db=db, user_id=request.user.id, visibility=visibility)
    return response_base.success(data=page_data)


@router.get('/{pk}', summary='Agent 详情', dependencies=[DependsJwtAuth])
async def get_agent(
    db: CurrentSession,
    request: Request,
    pk: Annotated[int, Path(description='Agent ID')],
) -> ResponseSchemaModel[GetAgentDetail]:
    data = await agent_service.get(db=db, pk=pk, user_id=request.user.id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新 Agent', dependencies=[DependsJwtAuth])
async def update_agent(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='Agent ID')],
    obj: UpdateAgentParam,
) -> ResponseModel:
    count = await agent_service.update(db=db, pk=pk, obj=obj, user_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/{pk}', summary='删除 Agent', dependencies=[DependsJwtAuth])
async def delete_agent(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='Agent ID')],
) -> ResponseModel:
    count = await agent_service.delete(db=db, pk=pk, user_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{pk}/set-default', summary='设为默认 Agent', dependencies=[DependsJwtAuth])
async def set_default_agent(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='Agent ID')],
) -> ResponseModel:
    await agent_service.set_default(db=db, pk=pk, user_id=request.user.id)
    return response_base.success()


@router.post('/{pk}/clone', summary='克隆 Agent', dependencies=[DependsJwtAuth])
async def clone_agent(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='源 Agent ID')],
) -> ResponseSchemaModel[GetAgentDetail]:
    data = await agent_service.clone(db=db, pk=pk, user_id=request.user.id)
    return response_base.success(data=data)
