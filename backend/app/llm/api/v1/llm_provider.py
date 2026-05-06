from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.app.llm.presets import LLM_PRESETS
from backend.app.llm.schema.llm_provider import (
    CreateLLMProviderParam,
    GetLLMProviderDetail,
    UpdateLLMProviderParam,
    VerifyModelParam,
)
from backend.app.llm.service.llm_provider_service import llm_provider_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/presets', summary='获取 LLM 服务商预设配置')
async def get_presets() -> ResponseSchemaModel[list]:
    return response_base.success(data=LLM_PRESETS)


@router.post('', summary='添加 LLM 服务商', dependencies=[DependsJwtAuth])
async def create_llm_provider(
    request: Request,
    db: CurrentSessionTransaction,
    obj: CreateLLMProviderParam,
) -> ResponseSchemaModel[dict]:
    pk = await llm_provider_service.create(db=db, obj=obj, user_id=request.user.id)
    return response_base.success(data={'id': pk})


@router.get(
    '',
    summary='LLM 服务商列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_llm_providers(
    request: Request,
    db: CurrentSession,
    name: Annotated[str | None, Query(description='服务商名称')] = None,
    provider_type: Annotated[str | None, Query(description='服务商类型')] = None,
    is_active: Annotated[bool | None, Query(description='是否启用')] = None,
    visibility: Annotated[str | None, Query(description='可见性过滤: private/public/official')] = None,
) -> ResponseSchemaModel[PageData[GetLLMProviderDetail]]:
    page_data = await llm_provider_service.get_list(
        db=db,
        user_id=request.user.id,
        name=name,
        provider_type=provider_type,
        is_active=is_active,
        visibility=visibility,
    )
    return response_base.success(data=page_data)


@router.get('/{pk}', summary='LLM 服务商详情', dependencies=[DependsJwtAuth])
async def get_llm_provider(
    request: Request,
    db: CurrentSession,
    pk: Annotated[int, Path(description='主键 ID')],
) -> ResponseSchemaModel[GetLLMProviderDetail]:
    data = await llm_provider_service.get(db=db, pk=pk, user_id=request.user.id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新 LLM 服务商', dependencies=[DependsJwtAuth])
async def update_llm_provider(
    request: Request,
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='主键 ID')],
    obj: UpdateLLMProviderParam,
) -> ResponseModel:
    count = await llm_provider_service.update(db=db, pk=pk, obj=obj, user_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/{pk}', summary='删除 LLM 服务商', dependencies=[DependsJwtAuth])
async def delete_llm_provider(
    request: Request,
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='主键 ID')],
) -> ResponseModel:
    count = await llm_provider_service.delete(db=db, pk=pk, user_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{pk}/verify', summary='验证 LLM 服务商模型连接', dependencies=[DependsJwtAuth])
async def verify_llm_provider(
    request: Request,
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='主键 ID')],
    obj: VerifyModelParam,
) -> ResponseSchemaModel[dict]:
    result = await llm_provider_service.verify_connection(
        db=db, pk=pk, user_id=request.user.id, model_name=obj.model_name
    )
    return response_base.success(data=result)


@router.post('/{pk}/fetch-models', summary='获取远程模型列表', dependencies=[DependsJwtAuth])
async def fetch_remote_models(
    request: Request,
    db: CurrentSession,
    pk: Annotated[int, Path(description='主键 ID')],
) -> ResponseSchemaModel[dict]:
    result = await llm_provider_service.fetch_remote_models(
        db=db, pk=pk, user_id=request.user.id
    )
    return response_base.success(data=result)
