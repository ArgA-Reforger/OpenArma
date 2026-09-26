import os
import subprocess
import sys

from importlib.metadata import PackageNotFoundError, distribution

from packaging.requirements import Requirement
from starlette.concurrency import run_in_threadpool

from backend.core.conf import settings
from backend.core.path_conf import PLUGIN_DIR
from backend.plugin.core import get_plugins
from backend.plugin.errors import PluginInstallError


def _is_in_virtualenv() -> bool:
    """Detect whether currently running inside a virtual environment"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)


def install_requirements(plugin: str | None) -> None:  # noqa: C901
    """
    Install plugin dependencies

    :param plugin: Specific plugin name, otherwise check all plugins
    :return:
    """
    plugins = [plugin] if plugin else get_plugins()

    for plugin in plugins:
        requirements_file = PLUGIN_DIR / plugin / 'requirements.txt'
        missing_dependencies = False
        if os.path.exists(requirements_file):
            with open(requirements_file, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    try:
                        req = Requirement(line)
                        dependency = req.name.lower()
                    except Exception as e:
                        raise PluginInstallError(f'Plugin {plugin} dependency {line} has an invalid format: {e!s}') from e
                    try:
                        distribution(dependency)
                    except PackageNotFoundError:
                        missing_dependencies = True

        if missing_dependencies:
            pip_install = ['uv', 'pip', 'install', '-r', requirements_file]
            if not _is_in_virtualenv():
                pip_install.append('--system')
            if settings.PLUGIN_PIP_CHINA:
                pip_install.extend(['-i', settings.PLUGIN_PIP_INDEX_URL])

            max_retries = settings.PLUGIN_PIP_MAX_RETRY
            for attempt in range(max_retries):
                try:
                    subprocess.check_call(pip_install)
                    break
                except subprocess.TimeoutExpired:
                    if attempt == max_retries - 1:
                        raise PluginInstallError(f'Plugin {plugin} dependency installation timed out')
                    continue
                except subprocess.CalledProcessError as e:
                    if attempt == max_retries - 1:
                        raise PluginInstallError(f'Plugin {plugin} dependency installation failed: {e}') from e
                    continue


def uninstall_requirements(plugin: str) -> None:
    """
    Uninstall plugin dependencies

    :param plugin: Plugin name
    :return:
    """
    requirements_file = PLUGIN_DIR / plugin / 'requirements.txt'
    if os.path.exists(requirements_file):
        try:
            pip_uninstall = ['uv', 'pip', 'uninstall', '-r', str(requirements_file)]
            if not _is_in_virtualenv():
                pip_uninstall.append('--system')
            subprocess.check_call(pip_uninstall, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            raise PluginInstallError(f'Plugin {plugin} dependency uninstallation failed: {e}') from e


async def install_requirements_async(plugin: str | None = None) -> None:
    """
    Asynchronously install plugin dependencies

    Due to Windows platform limitations, a fully async solution isn't possible, see:
    https://stackoverflow.com/questions/44633458/why-am-i-getting-notimplementederror-with-async-and-await-on-windows
    """
    await run_in_threadpool(install_requirements, plugin)


async def uninstall_requirements_async(plugin: str) -> None:
    """
    Asynchronously uninstall plugin dependencies

    :param plugin: Plugin name
    :return:
    """
    await run_in_threadpool(uninstall_requirements, plugin)
