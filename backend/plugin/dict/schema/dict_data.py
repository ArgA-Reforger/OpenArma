from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.enums import StatusType
from backend.common.schema import SchemaBase


class DictDataSchemaBase(SchemaBase):
    """Dict data base model"""

    type_id: int = Field(description='Dict type ID')
    label: str = Field(description='Dict label')
    value: str = Field(description='Dict value')
    color: str | None = Field(None, description='Label color')
    sort: int = Field(description='Sort order')
    status: StatusType = Field(description='Status')
    remark: str | None = Field(None, description='Remark')


class CreateDictDataParam(DictDataSchemaBase):
    """Create dict data parameters"""


class UpdateDictDataParam(DictDataSchemaBase):
    """Update dict data parameters"""


class DeleteDictDataParam(SchemaBase):
    """Delete dict data parameters"""

    pks: list[int] = Field(description='List of dict data IDs')


class GetDictDataDetail(DictDataSchemaBase):
    """Dict data detail"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Dict data ID')
    type_code: str = Field(description='Dict type code')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
