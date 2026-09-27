from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse

from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.core.conf import settings
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.code_generator.schema.gen import ImportParam
from backend.plugin.code_generator.service.gen_service import gen_service

router = APIRouter()


@router.get('/tables', summary='Get database tables')
async def get_all_tables(
    db: CurrentSession,
    table_schema: Annotated[str, Query(description='Database name')] = 'fba',
) -> ResponseSchemaModel[list[dict[str, str | None]]]:
    data = await gen_service.get_tables(db=db, table_schema=table_schema)
    return response_base.success(data=data)


@router.post(
    '/imports',
    summary='Import code generator business and model columns (dev environment only)',
    dependencies=[
        Depends(RequestPermission('codegen:table:import')),
        DependsRBAC,
    ],
)
async def import_table(db: CurrentSessionTransaction, obj: ImportParam) -> ResponseModel:
    await gen_service.import_business_and_model(db=db, obj=obj)
    return response_base.success()


@router.get('/{pk}/preview', summary='Preview generated code', dependencies=[DependsJwtAuth])
async def preview_code(
    db: CurrentSession, pk: Annotated[int, Path(description='Business ID')]
) -> ResponseSchemaModel[dict[str, bytes]]:
    data = await gen_service.preview(db=db, pk=pk)
    return response_base.success(data=data)


@router.get('/{pk}/paths', summary='Get code generation path', dependencies=[DependsJwtAuth])
async def get_generate_paths(
    db: CurrentSession, pk: Annotated[int, Path(description='Business ID')]
) -> ResponseSchemaModel[list[str]]:
    data = await gen_service.get_generate_path(db=db, pk=pk)
    return response_base.success(data=data)


@router.post(
    '/{pk}',
    summary='Generate code',
    description='Writes files to disk, use with caution (dev environment only)',
    dependencies=[
        Depends(RequestPermission('codegen:local:write')),
        DependsRBAC,
    ],
)
async def generate_code(db: CurrentSession, pk: Annotated[int, Path(description='Business ID')]) -> ResponseModel:
    await gen_service.generate(db=db, pk=pk)
    return response_base.success()


@router.get('/{pk}', summary='Download code', dependencies=[DependsJwtAuth])
async def download_code(db: CurrentSession, pk: Annotated[int, Path(description='Business ID')]):  # noqa: ANN201
    bio = await gen_service.download(db=db, pk=pk)
    return StreamingResponse(
        bio,
        media_type='application/x-zip-compressed',
        headers={'Content-Disposition': f'attachment; filename={settings.CODE_GENERATOR_DOWNLOAD_ZIP_FILENAME}.zip'},
    )
