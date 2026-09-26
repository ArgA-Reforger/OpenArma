from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ConfigSchemaBase(SchemaBase):
    """Parameter config base model"""

    name: str = Field(description='Parameter config name')
    type: str | None = Field(None, description='Parameter config type')
    key: str = Field(description='Parameter config key')
    value: str = Field(description='Parameter config value')
    is_frontend: bool = Field(description='Whether it is a frontend parameter config')
    remark: str | None = Field(None, description='Remark')


class CreateConfigParam(ConfigSchemaBase):
    """Create parameter config parameters"""


class UpdateConfigParam(ConfigSchemaBase):
    """Update parameter config parameters"""


class UpdateConfigsParam(UpdateConfigParam):
    """Batch update parameter config parameters"""

    id: int = Field(description='Parameter config ID')


class GetConfigDetail(ConfigSchemaBase):
    """Parameter config detail"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Parameter config ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
