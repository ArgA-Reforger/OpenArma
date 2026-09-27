from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.project.schema.project import CreateProjectParam, GetProjectDetail, UpdateProjectParam
from backend.app.project.service.project_service import project_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.post('', summary='Create project', dependencies=[DependsJwtAuth])
async def create_project(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateProjectParam,
) -> ResponseSchemaModel[GetProjectDetail]:
    data = await project_service.create(db=db, obj=obj, owner_id=request.user.id)
    return response_base.success(data=data)


@router.get(
    '',
    summary='Project list',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_projects(
    db: CurrentSession,
    request: Request,
    name: Annotated[str | None, Query(description='Project name')] = None,
    status: Annotated[str | None, Query(description='Status')] = None,
) -> ResponseSchemaModel[PageData[GetProjectDetail]]:
    page_data = await project_service.get_list(db=db, owner_id=request.user.id, name=name, status=status)
    return response_base.success(data=page_data)


@router.get('/{pk}', summary='Project details', dependencies=[DependsJwtAuth])
async def get_project(
    db: CurrentSession,
    request: Request,
    pk: Annotated[int, Path(description='Project ID')],
) -> ResponseSchemaModel[GetProjectDetail]:
    data = await project_service.get(db=db, pk=pk, owner_id=request.user.id)
    return response_base.success(data=data)


@router.put('/{pk}', summary='Update project', dependencies=[DependsJwtAuth])
async def update_project(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='Project ID')],
    obj: UpdateProjectParam,
) -> ResponseModel:
    count = await project_service.update(db=db, pk=pk, obj=obj, owner_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/{pk}', summary='Delete project', dependencies=[DependsJwtAuth])
async def delete_project(
    db: CurrentSessionTransaction,
    request: Request,
    pk: Annotated[int, Path(description='Project ID')],
) -> ResponseModel:
    count = await project_service.delete(db=db, pk=pk, owner_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()
