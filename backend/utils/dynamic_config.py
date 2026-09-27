from collections.abc import Callable

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.conf import settings
from backend.database.db import async_engine
from backend.plugin.config.enums import ConfigType
from backend.plugin.config.service.config_service import config_service
from backend.utils.serializers import select_list_serialize

_sys_config_table_exists: bool | None = None


async def check_sys_config_table_exists() -> bool:
    """Check whether the sys_config table exists"""
    global _sys_config_table_exists
    if _sys_config_table_exists is None:
        async with async_engine.connect() as conn:
            _sys_config_table_exists = await conn.run_sync(lambda c: inspect(c).has_table('sys_config', schema=None))
    return _sys_config_table_exists


def _to_bool(value: str) -> bool:
    """Convert a string to a boolean"""
    return value == 'true'


async def _load_config(
    db: AsyncSession,
    config_type: ConfigType,
    mapping: dict[str, Callable],
    status_key: str,
) -> None:
    """
    Load config based on the config type

    :param db: database session
    :param config_type: config type enum
    :param mapping: config mapping {config_key: converter}
    :param status_key: status key
    :return:
    """
    if not await check_sys_config_table_exists():
        return

    dynamic_config = await config_service.get_all(db=db, type=config_type)
    if not dynamic_config:
        return

    config_list = select_list_serialize(dynamic_config) if hasattr(dynamic_config[0], '__table__') else dynamic_config
    configs = {dc['key']: dc['value'] for dc in config_list}
    if configs.get(status_key, '1') == '0':
        return

    for config_key, converter in mapping.items():
        if config_key in configs:
            setattr(settings, config_key, converter(configs[config_key]))


async def load_user_security_config(db: AsyncSession) -> None:
    """
    Get user security config

    :param db: database session
    :return:
    """
    mapping = {
        'USER_LOCK_THRESHOLD': int,
        'USER_LOCK_SECONDS': int,
        'USER_PASSWORD_EXPIRY_DAYS': int,
        'USER_PASSWORD_REMINDER_DAYS': int,
        'USER_PASSWORD_HISTORY_CHECK_COUNT': int,
        'USER_PASSWORD_MIN_LENGTH': int,
        'USER_PASSWORD_MAX_LENGTH': int,
        'USER_PASSWORD_REQUIRE_SPECIAL_CHAR': _to_bool,
    }
    await _load_config(db, ConfigType.user_security, mapping, 'USER_SECURITY_CONFIG_STATUS')


async def load_login_config(db: AsyncSession) -> None:
    """
    Get login config

    :param db: database session
    :return:
    """
    mapping = {
        'LOGIN_CAPTCHA_ENABLED': _to_bool,
    }
    await _load_config(db, ConfigType.login, mapping, 'LOGIN_CONFIG_STATUS')


async def load_email_config(db: AsyncSession) -> None:
    """
    Get email config

    :param db: database session
    :return:
    """
    mapping = {
        'EMAIL_HOST': str,
        'EMAIL_PORT': int,
        'EMAIL_SSL': _to_bool,
        'EMAIL_USERNAME': str,
        'EMAIL_PASSWORD': str,
    }
    await _load_config(db, ConfigType.email, mapping, 'EMAIL_CONFIG_STATUS')
