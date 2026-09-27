from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Path, UploadFile
from fastapi.params import Query
from starlette.responses import StreamingResponse

from backend.app.admin.service.plugin_service import plugin_service
from backend.common.enums import PluginType
from backend.common.response.response_code import CustomResponse
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC

router = APIRouter()


@router.get('', summary='Get all plugins', dependencies=[DependsJwtAuth])
async def get_all_plugins() -> ResponseSchemaModel[list[dict[str, Any]]]:
    plugins = await plugin_service.get_all()
    return response_base.success(data=plugins)


@router.get('/changed', summary='Check whether any plugin has changed', dependencies=[DependsJwtAuth])
async def plugin_changed() -> ResponseSchemaModel[bool]:
    plugins = await plugin_service.changed()
    return response_base.success(data=bool(plugins))


@router.post(
    '',
    summary='Install plugin',
    description='Install using a plugin zip archive or a git repository URL (dev environment only)',
    dependencies=[
        Depends(RequestPermission('sys:plugin:install')),
        DependsRBAC,
    ],
)
async def install_plugin(
    type: Annotated[PluginType, Query(description='Plugin type')],
    file: Annotated[UploadFile | None, File()] = None,
    repo_url: Annotated[str | None, Query(description='Plugin git repository URL')] = None,
) -> ResponseModel:
    plugin_name = await plugin_service.install(type=type, file=file, repo_url=repo_url)
    return response_base.success(
        res=CustomResponse(
            code=200,
            msg=f'Plugin {plugin_name} installed successfully, please configure it per its README.md and restart the service',
        ),
    )


@router.delete(
    '/{plugin}',
    summary='Uninstall plugin',
    description='This removes the plugin dependencies directly, but does not delete the plugin itself; instead it moves the plugin to the backup directory (dev environment only)',
    dependencies=[
        Depends(RequestPermission('sys:plugin:uninstall')),
        DependsRBAC,
    ],
)
async def uninstall_plugin(plugin: Annotated[str, Path(description='Plugin name')]) -> ResponseModel:
    await plugin_service.uninstall(plugin=plugin)
    return response_base.success(
        res=CustomResponse(code=200, msg=f'Plugin {plugin} uninstalled successfully, please remove its config per its README.md and restart the service'),
    )


@router.put(
    '/{plugin}/status',
    summary='Update plugin status',
    dependencies=[
        Depends(RequestPermission('sys:plugin:edit')),
        DependsRBAC,
    ],
)
async def update_plugin_status(plugin: Annotated[str, Path(description='Plugin name')]) -> ResponseModel:
    await plugin_service.update_status(plugin=plugin)
    return response_base.success()


@router.get('/{plugin}', summary='Download plugin', dependencies=[DependsJwtAuth])
async def download_plugin(plugin: Annotated[str, Path(description='Plugin name')]) -> StreamingResponse:
    bio = await plugin_service.build(plugin=plugin)
    return StreamingResponse(
        bio,
        media_type='application/x-zip-compressed',
        headers={'Content-Disposition': f'attachment; filename={plugin}.zip'},
    )
