from datetime import datetime

from pydantic import ConfigDict, Field

from backend.app.admin.schema.data_scope import GetDataScopeWithRelationDetail
from backend.app.admin.schema.menu import GetMenuDetail
from backend.common.enums import StatusType
from backend.common.schema import SchemaBase


class RoleSchemaBase(SchemaBase):
    """Role base model"""

    name: str = Field(description='Role name')
    status: StatusType = Field(description='Status')
    is_filter_scopes: bool = Field(True, description='Filter data permissions')
    remark: str | None = Field(None, description='Remark')


class CreateRoleParam(RoleSchemaBase):
    """Role creation params"""


class UpdateRoleParam(RoleSchemaBase):
    """Role update params"""


class DeleteRoleParam(SchemaBase):
    """Role deletion params"""

    pks: list[int] = Field(description='Role ID list')


class CreateRoleMenuParam(SchemaBase):
    """Role menu creation params"""

    role_id: int = Field(description='Role ID')
    menu_id: int = Field(description='Menu ID')


class UpdateRoleMenuParam(SchemaBase):
    """Role menu update params"""

    menus: list[int] = Field(description='Menu ID list')


class CreateRoleScopeParam(SchemaBase):
    """Role data scope creation params"""

    role_id: int = Field(description='Role ID')
    data_scope_id: int = Field(description='Data scope ID')


class UpdateRoleScopeParam(SchemaBase):
    """Role data scope update params"""

    scopes: list[int] = Field(description='Data scope ID list')


class GetRoleDetail(RoleSchemaBase):
    """Role detail"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Role ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')


class GetRoleWithRelationDetail(GetRoleDetail):
    """Role relational detail"""

    menus: list[GetMenuDetail | None] = Field([], description='Menu detail list')
    scopes: list[GetDataScopeWithRelationDetail | None] = Field([], description='Data scope list')
