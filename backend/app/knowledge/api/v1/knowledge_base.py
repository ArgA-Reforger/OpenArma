from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.app.knowledge.schema.knowledge_base import CreateKnowledgeBaseParam, GetKnowledgeBaseDetail, UpdateKnowledgeBaseParam
from backend.app.knowledge.service.knowledge_base_service import knowledge_base_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.post('', summary='创建知识库', dependencies=[DependsJwtAuth])
async def create_knowledge_base(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateKnowledgeBaseParam,
) -> ResponseSchemaModel[GetKnowledgeBaseDetail]:
    data = await knowledge_base_service.create(db=db, obj=obj, owner_id=request.user.id)
    return response_base.success(data=data)


@router.get(
    '',
    summary='知识库列表',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_knowledge_bases(
    db: CurrentSession,
    request: Request,
    visibility: Annotated[str | None, Query(description='可见性过滤: private/public/official')] = None,
) -> ResponseSchemaModel[PageData[GetKnowledgeBaseDetail]]:
    page_data = await knowledge_base_service.get_list(db=db, owner_id=request.user.id, visibility=visibility)
    return response_base.success(data=page_data)


@router.get('/{pk}', summary='知识库详情', dependencies=[DependsJwtAuth])
async def get_knowledge_base(
    db: CurrentSession,
    request: Request,
    pk: Annotated[int, Path(description='知识库 ID')],
) -> ResponseSchemaModel[GetKnowledgeBaseDetail]:
    data = await knowledge_base_service.get(db=db, pk=pk, owner_id=request.user.id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新知识库', dependencies=[DependsJwtAuth])
async def update_knowledge_base(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='知识库 ID')],
    obj: UpdateKnowledgeBaseParam,
) -> ResponseModel:
    count = await knowledge_base_service.update(db=db, pk=pk, obj=obj, owner_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/{pk}', summary='删除知识库', dependencies=[DependsJwtAuth])
async def delete_knowledge_base(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='知识库 ID')],
) -> ResponseModel:
    count = await knowledge_base_service.delete(db=db, pk=pk, owner_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{pk}/clone', summary='克隆知识库', dependencies=[DependsJwtAuth])
async def clone_knowledge_base(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='源知识库 ID')],
) -> ResponseSchemaModel[GetKnowledgeBaseDetail]:
    data = await knowledge_base_service.clone(db=db, pk=pk, owner_id=request.user.id)
    return response_base.success(data=data)
