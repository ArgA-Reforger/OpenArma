from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ProjectSchemaBase(SchemaBase):
    """项目基础模型"""

    name: str = Field(description='项目名称')
    description: str | None = Field(None, description='项目描述')
    api_key: str | None = Field(None, description='API Key')
    settings: dict | None = Field(default_factory=dict, description='项目设置')
    status: str = Field(default='active', description='状态 active/archived')


class CreateProjectParam(ProjectSchemaBase):
    """创建项目参数"""


class UpdateProjectParam(SchemaBase):
    """更新项目参数"""

    name: str | None = Field(None, description='项目名称')
    description: str | None = Field(None, description='项目描述')
    api_key: str | None = Field(None, description='API Key')
    settings: dict | None = Field(None, description='项目设置')
    status: str | None = Field(None, description='状态 active/archived')
    map_id: int | None = Field(None, description='关联地图 ID')


class GetProjectDetail(ProjectSchemaBase):
    """项目详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='项目 ID')
    owner_id: int = Field(description='所有者 ID')
    map_id: int | None = Field(None, description='关联地图 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
