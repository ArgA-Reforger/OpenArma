import warnings

from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.common.enums import PluginLevelType
from backend.plugin.errors import PluginConfigError
from backend.utils.pattern_validate import match_string

# Supported tag types
_VALID_TAGS = frozenset({'ai', 'mcp', 'agent', 'auth', 'storage', 'notification', 'task', 'payment', 'other'})

# Supported database types
_VALID_DATABASES = frozenset({'mysql', 'postgresql'})


class PluginInfoSchema(BaseModel):
    """Plugin info model"""

    icon: str | None = Field(default=None, description='Icon path or link URL')
    summary: str = Field(..., min_length=1, max_length=100, description='Summary')
    version: str = Field(..., description='Version number')
    description: str = Field(..., min_length=1, max_length=500, description='Description')
    author: str = Field(..., min_length=1, max_length=50, description='Author')
    tags: list[str] = Field(default_factory=list, description='Tags')
    database: list[str] = Field(default_factory=list, description='Supported databases')

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version number format"""
        if not match_string(r'^\d+\.\d+\.\d+$', v):
            raise PluginConfigError(f'Invalid version format, must be x.y.z (e.g. 1.0.0), current value: {v}')
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tags"""
        if v:
            invalid_tags = set(v) - _VALID_TAGS
            if invalid_tags:
                raise PluginConfigError(
                    f'Invalid tag values: {", ".join(invalid_tags)}, supported tags: {", ".join(sorted(_VALID_TAGS))}'
                )
        return v

    @field_validator('database')
    @classmethod
    def validate_database(cls, v: list[str]) -> list[str]:
        """Validate database type"""
        if v:
            invalid_dbs = set(v) - _VALID_DATABASES
            if invalid_dbs:
                raise PluginConfigError(
                    f'Invalid database type: {", ".join(invalid_dbs)}, '
                    f'supported databases: {", ".join(sorted(_VALID_DATABASES))}'
                )
        return v


class AppPluginAppSchema(BaseModel):
    """App-level plugin app config model"""

    router: list[str] = Field(..., min_length=1, description='List of router instances')

    @field_validator('router')
    @classmethod
    def validate_router(cls, v: list[str]) -> list[str]:
        """Validate router config"""
        if not v:
            raise PluginConfigError('router config cannot be empty')
        for router in v:
            if not router or not isinstance(router, str):
                raise PluginConfigError(f'router config item must be a non-empty string, current value: {router}')
        return v


class ExtendPluginAppSchema(BaseModel):
    """Extend-level plugin app config model"""

    extend: str = Field(..., min_length=1, description='Name of the extended app folder')


class ApiConfigSchema(BaseModel):
    """API config model"""

    prefix: str = Field(..., min_length=1, description='Route prefix')
    tags: str = Field(..., min_length=1, description='Swagger doc tags')

    @field_validator('prefix')
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        """Validate route prefix"""
        if not v.startswith('/'):
            raise PluginConfigError(f'Route prefix must start with "/", current value: {v}')
        if not match_string(r'^/[a-zA-Z0-9_/-]*$', v):
            raise PluginConfigError(
                f'Invalid route prefix format, only letters, digits, underscores, slashes and hyphens are '
                f'allowed, current value: {v}'
            )
        return v


class AppPluginConfigSchema(BaseModel):
    """App-level plugin config model"""

    plugin: PluginInfoSchema = Field(..., description='Plugin info')
    app: AppPluginAppSchema = Field(..., description='App config')
    settings: dict[str, Any] = Field(default_factory=dict, description='Settings')

    @field_validator('settings')
    @classmethod
    def validate_settings(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate that setting names are all uppercase"""
        if v:
            invalid_keys = [key for key in v if not key.isupper()]
            if invalid_keys:
                raise PluginConfigError(f'Setting names must be all uppercase, invalid keys: {", ".join(invalid_keys)}')
        return v


class ExtendPluginConfigSchema(BaseModel):
    """Extend-level plugin config model"""

    plugin: PluginInfoSchema = Field(..., description='Plugin info')
    app: ExtendPluginAppSchema = Field(..., description='App config')
    api: dict[str, ApiConfigSchema] = Field(..., min_length=1, description='API config')
    settings: dict[str, Any] = Field(default_factory=dict, description='Settings')

    @field_validator('api', mode='before')
    @classmethod
    def validate_api_config(cls, v: dict[str, Any]) -> dict[str, ApiConfigSchema]:
        """Validate and convert API config"""
        if not v:
            raise PluginConfigError('Extend-level plugin must include at least one api config')
        validated_api = {}
        for api_name, api_config in v.items():
            if not api_name or not isinstance(api_name, str):
                raise PluginConfigError(f'api config name must be a non-empty string, current value: {api_name}')
            if not match_string(r'^[a-zA-Z_][a-zA-Z0-9_]*$', api_name):
                raise PluginConfigError(
                    f'Invalid api config name format, must start with a letter or underscore and contain only '
                    f'letters, digits and underscores, current value: {api_name}'
                )
            validated_api[api_name] = ApiConfigSchema(**api_config) if isinstance(api_config, dict) else api_config
        return validated_api

    @field_validator('settings')
    @classmethod
    def validate_settings(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate that setting names are all uppercase"""
        if v:
            invalid_keys = [key for key in v if not key.isupper()]
            if invalid_keys:
                raise PluginConfigError(f'Setting names must be all uppercase, invalid keys: {", ".join(invalid_keys)}')
        return v


def validate_plugin_config(plugin_name: str, config: dict[str, Any]) -> PluginLevelType:
    """
    Validate plugin config

    :param plugin_name: Plugin name
    :param config: Plugin config dict
    :return:
    """
    is_extend_plugin = 'api' in config

    try:
        if is_extend_plugin:
            ExtendPluginConfigSchema.model_validate(config)
            plugin_level = PluginLevelType.extend
        else:
            AppPluginConfigSchema.model_validate(config)
            plugin_level = PluginLevelType.app
    except Exception as e:
        error_msg = str(e)
        # Format Pydantic error message
        if hasattr(e, 'errors'):
            errors = e.errors()
            error_details = []
            for error in errors:
                loc = '.'.join(str(loc) for loc in error['loc'])
                msg = error['msg']
                error_details.append(f'{loc}: {msg}')
            error_msg = '; '.join(error_details)
        raise PluginConfigError(f'Plugin {plugin_name} config validation failed: {error_msg}') from e

    # TODO Make required in the next major version
    plugin_info = config.get('plugin', {})
    if not plugin_info.get('tags'):
        warnings.warn(
            f"Plugin '{plugin_name}' has no 'tags' field configured; this field will become required in the next "
            f"major version, please contact the plugin author to update it",
            FutureWarning,
            stacklevel=2,
        )
    if not plugin_info.get('database'):
        warnings.warn(
            f"Plugin '{plugin_name}' has no 'database' field configured; this field will become required in the "
            f"next major version, please contact the plugin author to update it",
            FutureWarning,
            stacklevel=2,
        )

    return plugin_level
