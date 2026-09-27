from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class BuiltinToolBase(SchemaBase):
    """Base builtin tool schema"""

    name: str = Field(description='Tool identifier name')
    display_name: str = Field(description='Display name')
    description: str = Field(description='Tool description')
    input_schema: dict = Field(description='Input parameters JSON Schema')
    handler_type: str = Field('python_builtin', description='Handler type')
    handler_config: dict | None = Field(None, description='Handler configuration')
    category: str = Field('general', description='Tool category general/arma/...')
    is_system: bool = Field(False, description='Whether system preset')
    is_active: bool = Field(True, description='Whether enabled')


class CreateBuiltinToolParam(BuiltinToolBase):
    """Create builtin tool"""
    pass


class UpdateBuiltinToolParam(SchemaBase):
    """Update builtin tool"""

    display_name: str | None = Field(None, description='Display name')
    description: str | None = Field(None, description='Tool description')
    input_schema: dict | None = Field(None, description='Input parameters JSON Schema')
    handler_type: str | None = Field(None, description='Handler type')
    handler_config: dict | None = Field(None, description='Handler configuration')
    is_active: bool | None = Field(None, description='Whether enabled')


class GetBuiltinToolDetail(BuiltinToolBase):
    """Builtin tool details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Tool ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
