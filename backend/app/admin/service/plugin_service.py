import io
import json

from typing import Any

import anyio

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from backend.common.enums import PluginType, StatusType
from backend.common.exception import errors
from backend.core.conf import settings
from backend.core.path_conf import PLUGIN_DIR
from backend.database.redis import redis_client
from backend.plugin.installer import install_git_plugin, install_zip_plugin, remove_plugin, zip_plugin
from backend.plugin.requirements import uninstall_requirements_async
from backend.utils.timezone import timezone


class PluginService:
    """Plugin service class"""

    @staticmethod
    async def get_all() -> list[dict[str, Any]]:
        """Get all plugins"""

        keys = [key async for key in redis_client.scan_iter(f'{settings.PLUGIN_REDIS_PREFIX}:*')]

        result = [json.loads(info) for info in await redis_client.mget(*keys)]

        return result

    @staticmethod
    async def changed() -> str | None:
        """Check whether any plugin has changed"""
        return await redis_client.get(f'{settings.PLUGIN_REDIS_PREFIX}:changed')

    @staticmethod
    async def install(*, type: PluginType, file: UploadFile | None = None, repo_url: str | None = None) -> str:
        """
        Install plugin

        :param type: plugin type
        :param file: plugin zip archive
        :param repo_url: git repository URL
        :return:
        """
        if settings.ENVIRONMENT != 'dev':
            raise errors.RequestError(msg='Installing plugins is disabled outside the dev environment')
        if type == PluginType.zip:
            if not file:
                raise errors.RequestError(msg='ZIP archive cannot be empty')
            return await install_zip_plugin(file)
        if not repo_url:
            raise errors.RequestError(msg='Git repository URL cannot be empty')
        return await install_git_plugin(repo_url)

    @staticmethod
    async def uninstall(*, plugin: str) -> None:
        """
        Uninstall plugin

        :param plugin: plugin name
        :return:
        """
        if settings.ENVIRONMENT != 'dev':
            raise errors.RequestError(msg='Uninstalling plugins is disabled outside the dev environment')
        plugin_dir = anyio.Path(PLUGIN_DIR / plugin)
        if not await plugin_dir.exists():
            raise errors.NotFoundError(msg='Plugin does not exist')
        await uninstall_requirements_async(plugin)
        backup_file = PLUGIN_DIR / f'{plugin}.{timezone.now().strftime("%Y%m%d%H%M%S")}.backup.zip'
        await run_in_threadpool(zip_plugin, plugin_dir, backup_file)
        await run_in_threadpool(remove_plugin, plugin_dir)
        await redis_client.delete(f'{settings.PLUGIN_REDIS_PREFIX}:{plugin}')
        await redis_client.set(f'{settings.PLUGIN_REDIS_PREFIX}:changed', 'true')

    @staticmethod
    async def update_status(*, plugin: str) -> None:
        """
        Update plugin status

        :param plugin: plugin name
        :return:
        """
        plugin_info = await redis_client.get(f'{settings.PLUGIN_REDIS_PREFIX}:{plugin}')
        if not plugin_info:
            raise errors.NotFoundError(msg='Plugin does not exist')
        plugin_info = json.loads(plugin_info)

        # Update the persistent cache status
        new_status = (
            str(StatusType.enable.value)
            if plugin_info['plugin']['enable'] == str(StatusType.disable.value)
            else str(StatusType.disable.value)
        )
        plugin_info['plugin']['enable'] = new_status
        await redis_client.set(f'{settings.PLUGIN_REDIS_PREFIX}:{plugin}', json.dumps(plugin_info, ensure_ascii=False))

    @staticmethod
    async def build(*, plugin: str) -> io.BytesIO:
        """
        Package plugin as a zip archive

        :param plugin: plugin name
        :return:
        """
        plugin_dir = anyio.Path(PLUGIN_DIR / plugin)
        if not await plugin_dir.exists():
            raise errors.NotFoundError(msg='Plugin does not exist')

        bio = io.BytesIO()
        await run_in_threadpool(zip_plugin, plugin_dir, bio)
        bio.seek(0)
        return bio


plugin_service: PluginService = PluginService()
