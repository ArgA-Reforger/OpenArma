from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class BuiltinToolBase(SchemaBase):
    """内置工具基础 Schema"""

    name: str = Field(description='工具标识名')
    display_name: str = Field(description='显示名称')
    description: str = Field(description='工具描述')
    input_schema: dict = Field(description='输入参数 JSON Schema')
    handler_type: str = Field('python_builtin', description='执行器类型')
    handler_config: dict | None = Field(None, description='执行器配置')
    category: str = Field('general', description='工具分类 general/arma/...')
    is_system: bool = Field(False, description='是否系统预置')
    is_active: bool = Field(True, description='是否启用')


class CreateBuiltinToolParam(BuiltinToolBase):
    """创建内置工具"""
    pass


class UpdateBuiltinToolParam(SchemaBase):
    """更新内置工具"""

    display_name: str | None = Field(None, description='显示名称')
    description: str | None = Field(None, description='工具描述')
    input_schema: dict | None = Field(None, description='输入参数 JSON Schema')
    handler_type: str | None = Field(None, description='执行器类型')
    handler_config: dict | None = Field(None, description='执行器配置')
    is_active: bool | None = Field(None, description='是否启用')


class GetBuiltinToolDetail(BuiltinToolBase):
    """内置工具详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='工具 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
