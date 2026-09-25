from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.enums import StatusType
from backend.common.schema import CustomEmailStr, CustomPhoneNumber, SchemaBase


class DeptSchemaBase(SchemaBase):
    """Department base model"""

    name: str = Field(description='Department name')
    parent_id: int | None = Field(None, description='Parent department ID')
    sort: int = Field(0, ge=0, description='Sort order')
    leader: str | None = Field(None, description='Leader')
    phone: CustomPhoneNumber | None = Field(None, description='Contact phone number')
    email: CustomEmailStr | None = Field(None, description='Email address')
    status: StatusType = Field(description='Status')


class CreateDeptParam(DeptSchemaBase):
    """Department creation params"""


class UpdateDeptParam(DeptSchemaBase):
    """Department update params"""


class GetDeptDetail(DeptSchemaBase):
    """Department detail"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Department ID')
    del_flag: bool = Field(description='Whether deleted')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')


class GetDeptTree(GetDeptDetail):
    """Get department tree"""

    children: list['GetDeptTree'] | None = Field(None, description='Sub-menus')
