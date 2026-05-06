from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.app.topology.schema.topology import CreateTopologyParam, GetTopologyDetail, UpdateTopologyParam
from backend.app.topology.service.topology_service import topology_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.post('', summary='创建拓扑', dependencies=[DependsJwtAuth])
async def create_topology(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateTopologyParam,
) -> ResponseSchemaModel[GetTopologyDetail]:
    data = await topology_service.create(db=db, obj=obj, user_id=request.user.id)
    return response_base.success(data=data)


@router.get('', summary='拓扑列表', dependencies=[DependsJwtAuth, DependsPagination])
async def get_topologies(
    db: CurrentSession,
    request: Request,
    visibility: Annotated[str | None, Query(description='可见性过滤: private/public/official')] = None,
) -> ResponseSchemaModel[PageData[GetTopologyDetail]]:
    page_data = await topology_service.get_list(db=db, user_id=request.user.id, visibility=visibility)
    return response_base.success(data=page_data)


@router.get('/{pk}', summary='拓扑详情', dependencies=[DependsJwtAuth])
async def get_topology(
    db: CurrentSession,
    request: Request,
    pk: Annotated[int, Path(description='Topology ID')],
) -> ResponseSchemaModel[GetTopologyDetail]:
    data = await topology_service.get(db=db, pk=pk, user_id=request.user.id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新拓扑', dependencies=[DependsJwtAuth])
async def update_topology(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='Topology ID')],
    obj: UpdateTopologyParam,
) -> ResponseModel:
    count = await topology_service.update(db=db, pk=pk, obj=obj, user_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/{pk}', summary='删除拓扑', dependencies=[DependsJwtAuth])
async def delete_topology(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='Topology ID')],
) -> ResponseModel:
    count = await topology_service.delete(db=db, pk=pk, user_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{pk}/clone', summary='克隆拓扑', dependencies=[DependsJwtAuth])
async def clone_topology(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='源 Topology ID')],
) -> ResponseSchemaModel[GetTopologyDetail]:
    data = await topology_service.clone(db=db, pk=pk, user_id=request.user.id)
    return response_base.success(data=data)
