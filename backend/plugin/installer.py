import io
import os
import re
import stat
import zipfile

import anyio

from anyio import open_file
from dulwich import porcelain
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from backend.common.exception import errors
from backend.common.log import log
from backend.core.conf import settings
from backend.core.path_conf import ENV_FILE_PATH, PLUGIN_DIR
from backend.database.redis import redis_client
from backend.plugin.requirements import install_requirements_async
from backend.utils.locks import acquire_distributed_reload_lock
from backend.utils.pattern_validate import is_git_url


async def _append_env_example(plugin_path: anyio.Path) -> None:
    """
    Append to the main .env file

    :param plugin_path: Plugin directory path
    :return:
    """
    env_example_path = plugin_path / '.env.example'
    if not await env_example_path.exists():
        return

    async with await open_file(env_example_path, mode='r', encoding='utf-8') as f:
        env_example_content = await f.read()

    if not env_example_content.strip():
        return

    env_path = anyio.Path(ENV_FILE_PATH)
    existing_content = ''
    if await env_path.exists():
        async with await open_file(env_path, mode='r', encoding='utf-8') as f:
            existing_content = await f.read()

    separator = '\n' if existing_content and not existing_content.endswith('\n') else ''
    new_content = f'{existing_content}{separator}{env_example_content}'

    async with await open_file(env_path, mode='w', encoding='utf-8') as f:
        await f.write(new_content)


async def install_zip_plugin(file: UploadFile | str) -> str:
    """
    Install a ZIP plugin

    :param file: FastAPI upload file object or full file path
    :return:
    """
    if isinstance(file, str):
        async with await open_file(file, mode='rb') as fb:
            contents = await fb.read()
    else:
        contents = await file.read()
    file_bytes = io.BytesIO(contents)
    if not zipfile.is_zipfile(file_bytes):
        raise errors.RequestError(msg='Invalid plugin archive format')

    async with acquire_distributed_reload_lock():
        with zipfile.ZipFile(file_bytes) as zf:
            # Validate the archive
            plugin_namelist = zf.namelist()
            plugin_dir_name = plugin_namelist[0].split('/')[0]
            if not plugin_namelist:
                raise errors.RequestError(msg='Invalid plugin archive contents')
            if (
                len(plugin_namelist) <= 3
                or f'{plugin_dir_name}/plugin.toml' not in plugin_namelist
                or f'{plugin_dir_name}/README.md' not in plugin_namelist
            ):
                raise errors.RequestError(msg='Plugin archive is missing required files')

            # Check whether the plugin can be installed
            plugin_name = re.match(
                r'^([a-zA-Z0-9_]+)',
                file.split(os.sep)[-1].split('.')[0].strip()
                if isinstance(file, str)
                else file.filename.split('.')[0].strip(),
            ).group()
            full_plugin_path = anyio.Path(PLUGIN_DIR / plugin_name)
            if await full_plugin_path.exists():
                raise errors.ConflictError(msg='This plugin is already installed')
            await full_plugin_path.mkdir(parents=True, exist_ok=True)

            # Extract (install)
            members = []
            for member in zf.infolist():
                if member.filename.startswith(plugin_dir_name):
                    new_filename = member.filename.replace(plugin_dir_name, '')
                    if new_filename:
                        member.filename = new_filename
                        members.append(member)
            await run_in_threadpool(zf.extractall, full_plugin_path, members)

        await _append_env_example(full_plugin_path)
        await install_requirements_async(plugin_dir_name)
        await redis_client.set(f'{settings.PLUGIN_REDIS_PREFIX}:changed', 'true')

    return plugin_name


async def install_git_plugin(repo_url: str) -> str:
    """
    Install a Git plugin

    :param repo_url:
    :return:
    """
    match = is_git_url(repo_url)
    if not match:
        raise errors.RequestError(msg='Invalid Git repository URL format, only HTTP/HTTPS protocols are supported')
    repo_name = match.group('repo')
    path = anyio.Path(PLUGIN_DIR / repo_name)
    if await path.exists():
        raise errors.ConflictError(msg=f'Plugin {repo_name} is already installed')

    async with acquire_distributed_reload_lock():
        try:
            await run_in_threadpool(porcelain.clone, repo_url, PLUGIN_DIR / repo_name, checkout=True)
        except Exception as e:
            log.error(f'Plugin installation failed: {e}')
            raise errors.ServerError(msg='Plugin installation failed, please try again later') from e

        await _append_env_example(path)
        await install_requirements_async(repo_name)
        await redis_client.set(f'{settings.PLUGIN_REDIS_PREFIX}:changed', 'true')

    return repo_name


def remove_plugin(plugin_dir: os.PathLike) -> None:
    """
    Remove a plugin

    :param plugin_dir: Plugin directory
    :return:
    """
    import shutil

    def _on_error(func, path, _exc_info) -> None:  # noqa: ANN001
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(plugin_dir, onerror=_on_error)


def zip_plugin(plugin_dir: os.PathLike, target: os.PathLike | io.BytesIO) -> None:
    """
    Zip-compress a plugin

    :param plugin_dir: Plugin directory
    :param target: Compression target
    :return:
    """
    with zipfile.ZipFile(target, 'w') as zf:
        plugin_dir_parent = os.path.dirname(plugin_dir)
        for root, dirs, files in os.walk(plugin_dir):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=plugin_dir_parent)
                zf.write(file_path, arcname)
