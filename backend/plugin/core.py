import json
import os
import warnings

from functools import lru_cache
from typing import Any

import anyio
import rtoml

from fastapi import APIRouter, Depends, Request

from backend.common.enums import DataBaseType, PluginLevelType, PrimaryKeyType, StatusType
from backend.common.exception import errors
from backend.common.log import log
from backend.core.conf import settings
from backend.core.path_conf import PLUGIN_DIR
from backend.database.redis import RedisCli, redis_client
from backend.plugin.errors import PluginConfigError, PluginInjectError
from backend.plugin.validator import validate_plugin_config
from backend.utils.async_helper import run_await
from backend.utils.dynamic_import import get_model_objects, import_module_cached


@lru_cache(maxsize=128)
def get_plugins() -> tuple[str, ...]:
    """Get the list of plugins"""
    plugin_packages = []

    # Walk the plugins directory
    for item in os.listdir(PLUGIN_DIR):
        item_path = PLUGIN_DIR / item
        if not os.path.isdir(item_path) and item == '__pycache__':
            continue

        # Check whether it's a directory containing an __init__.py file
        if os.path.isdir(item_path) and '__init__.py' in os.listdir(item_path):
            plugin_packages.append(item)

    return tuple(plugin_packages)


def get_plugin_models() -> list[object]:
    """Get all model classes of every plugin"""
    objs = []

    for plugin in get_plugins():
        module_path = f'backend.plugin.{plugin}.model'
        model_objs = get_model_objects(module_path)
        if model_objs:
            objs.extend(model_objs)

    return objs


async def get_plugin_sql(plugin: str, db_type: DataBaseType, pk_type: PrimaryKeyType) -> str | None:
    """
    Get the plugin's SQL script

    :param plugin: Plugin name
    :param db_type: Database type
    :param pk_type: Primary key type
    :return:
    """
    if db_type == DataBaseType.mysql:
        mysql_dir = PLUGIN_DIR / plugin / 'sql' / 'mysql'
        sql_file = (
            mysql_dir / 'init.sql' if pk_type == PrimaryKeyType.autoincrement else mysql_dir / 'init_snowflake.sql'
        )
    else:
        postgresql_dir = PLUGIN_DIR / plugin / 'sql' / 'postgresql'
        sql_file = (
            postgresql_dir / 'init.sql'
            if pk_type == PrimaryKeyType.autoincrement
            else postgresql_dir / 'init_snowflake.sql'
        )

    path = anyio.Path(sql_file)
    if not await path.exists():
        return None

    return sql_file


def load_plugin_config(plugin: str) -> dict[str, Any]:
    """
    Load a plugin's config

    :param plugin: Plugin name
    :return:
    """
    toml_path = PLUGIN_DIR / plugin / 'plugin.toml'
    if not os.path.exists(toml_path):
        raise PluginInjectError(f'Plugin {plugin} is missing its plugin.toml config file, please check if the plugin is valid')

    with open(toml_path, encoding='utf-8') as f:
        return rtoml.load(f)


def parse_plugin_config() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse plugin configs"""
    extend_plugins = []
    app_plugins = []

    plugins = get_plugins()

    # Use a dedicated connection
    current_redis_client = RedisCli()
    run_await(current_redis_client.init)()

    # Clean up info of unknown plugins
    run_await(current_redis_client.delete_prefix)(
        settings.PLUGIN_REDIS_PREFIX,
        exclude=[f'{settings.PLUGIN_REDIS_PREFIX}:{key}' for key in plugins],
    )

    for plugin in plugins:
        data = load_plugin_config(plugin)
        plugin_type = validate_plugin_config(plugin, data)

        if plugin_type == PluginLevelType.extend:
            extend_plugins.append(data)
        else:
            app_plugins.append(data)

        # Fill in extra plugin info
        data['plugin']['name'] = plugin
        plugin_cache_info = run_await(current_redis_client.get)(f'{settings.PLUGIN_REDIS_PREFIX}:{plugin}')
        if plugin_cache_info:
            data['plugin']['enable'] = json.loads(plugin_cache_info)['plugin']['enable']
        else:
            data['plugin']['enable'] = str(StatusType.enable.value)

        # Cache the latest plugin info
        run_await(current_redis_client.set)(
            f'{settings.PLUGIN_REDIS_PREFIX}:{plugin}',
            json.dumps(data, ensure_ascii=False),
        )

    # Reset the plugin-changed state
    run_await(current_redis_client.delete)(f'{settings.PLUGIN_REDIS_PREFIX}:changed')

    # Close the connection
    run_await(current_redis_client.aclose)()

    return extend_plugins, app_plugins


def inject_extend_router(plugin: dict[str, Any]) -> None:
    """
    Inject routes for an extend-level plugin

    :param plugin: Plugin name
    :return:
    """
    plugin_name: str = plugin['plugin']['name']
    plugin_api_path = PLUGIN_DIR / plugin_name / 'api'
    if not os.path.exists(plugin_api_path):
        raise PluginConfigError(f'Plugin {plugin} is missing its api directory, please check the plugin files')

    for root, _, api_files in os.walk(plugin_api_path):
        for file in api_files:
            if not (file.endswith('.py') and file != '__init__.py'):
                continue

            # Parse the plugin route config
            file_config = plugin['api'][file[:-3]]
            prefix = file_config['prefix']
            tags = file_config['tags']

            # Get the plugin route module
            file_path = os.path.join(root, file)
            path_to_module_str = os.path.relpath(file_path, PLUGIN_DIR).replace(os.sep, '.')[:-3]
            module_path = f'backend.plugin.{path_to_module_str}'

            try:
                module = import_module_cached(module_path)
                plugin_router = getattr(module, 'router', None)
                if not plugin_router:
                    warnings.warn(
                        f'Extend-level plugin {plugin_name} module {module_path} has no valid router, '
                        f'please check that the plugin files are complete',
                        FutureWarning,
                    )
                    continue

                # Get the target app router
                relative_path = os.path.relpath(root, plugin_api_path)
                app_name = plugin.get('app', {}).get('extend')
                target_module_path = f'backend.app.{app_name}.api.{relative_path.replace(os.sep, ".")}'
                target_module = import_module_cached(target_module_path)
                target_router = getattr(target_module, 'router', None)

                if not target_router or not isinstance(target_router, APIRouter):
                    raise PluginInjectError(
                        f'Extend-level plugin {plugin_name} module {module_path} has no valid router, '
                        f'please check that the plugin files are complete',
                    )

                # Inject the plugin router into the target router
                target_router.include_router(
                    router=plugin_router,
                    prefix=prefix,
                    tags=[tags] if tags else [],
                    dependencies=[Depends(PluginStatusChecker(plugin_name))],
                )
            except Exception as e:
                raise PluginInjectError(f'Extend-level plugin {plugin_name} route injection failed: {e!s}') from e


def inject_app_router(plugin: dict[str, Any], target_router: APIRouter) -> None:
    """
    Inject routes for an app-level plugin

    :param plugin: Plugin name
    :param target_router: FastAPI router
    :return:
    """
    plugin_name: str = plugin['plugin']['name']
    module_path = f'backend.plugin.{plugin_name}.api.router'
    try:
        module = import_module_cached(module_path)
        routers = plugin['app']['router']
        if not routers or not isinstance(routers, list):
            raise PluginConfigError(f'App-level plugin {plugin_name} config file has an error, please check it')

        for router in routers:
            plugin_router = getattr(module, router, None)
            if not plugin_router or not isinstance(plugin_router, APIRouter):
                raise PluginInjectError(
                    f'App-level plugin {plugin_name} module {module_path} has no valid router, '
                    f'please check that the plugin files are complete',
                )

            # Inject the plugin router into the target router
            target_router.include_router(plugin_router, dependencies=[Depends(PluginStatusChecker(plugin_name))])
    except Exception as e:
        raise PluginInjectError(f'App-level plugin {plugin_name} route injection failed: {e!s}') from e


def build_final_router() -> APIRouter:
    """Build the final router"""
    extend_plugins, app_plugins = parse_plugin_config()

    for plugin in extend_plugins:
        inject_extend_router(plugin)

    # Main router, must be imported after extend-level plugin route injection and before
    # app-level plugin route injection
    from backend.app.router import router as main_router

    for plugin in app_plugins:
        inject_app_router(plugin, main_router)

    return main_router


class PluginStatusChecker:
    """Plugin status checker"""

    def __init__(self, plugin: str) -> None:
        """
        Initialize the plugin status checker

        :param plugin: Plugin name
        :return:
        """
        self.plugin = plugin

    async def __call__(self, request: Request) -> None:
        """
        Verify the plugin status

        :param request: FastAPI request object
        :return:
        """
        plugin_info = await redis_client.get(f'{settings.PLUGIN_REDIS_PREFIX}:{self.plugin}')
        if not plugin_info:
            log.error('Plugin status not initialized or lost, restarting the service should auto-fix it')
            raise PluginInjectError('Plugin status not initialized or lost, please contact the system administrator')

        if not int(json.loads(plugin_info)['plugin']['enable']):
            raise errors.ServerError(msg=f'Plugin {self.plugin} is not enabled, please contact the system administrator')
