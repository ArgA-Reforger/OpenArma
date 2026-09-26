from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class DictTypeSchemaBase(SchemaBase):
    """Dict type base model"""

    name: str = Field(description='Dict name')
    code: str = Field(description='Dict code')
    remark: str | None = Field(None, description='Remark')


class CreateDictTypeParam(DictTypeSchemaBase):
    """Create dict type parameters"""


class UpdateDictTypeParam(DictTypeSchemaBase):
    """Update dict type parameters"""


class DeleteDictTypeParam(SchemaBase):
    """Delete dict type parameters"""

    pks: list[int] = Field(description='List of dict type IDs')


class GetDictTypeDetail(DictTypeSchemaBase):
    """Dict type detail"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Dict type ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
