from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ProjectSchemaBase(SchemaBase):
    """Base project model"""

    name: str = Field(description='Project name')
    description: str | None = Field(None, description='Project description')
    api_key: str | None = Field(None, description='API Key')
    settings: dict | None = Field(default_factory=dict, description='Project settings')
    status: str = Field(default='active', description='Status active/archived')


class CreateProjectParam(ProjectSchemaBase):
    """Create project parameters"""


class UpdateProjectParam(SchemaBase):
    """Update project parameters"""

    name: str | None = Field(None, description='Project name')
    description: str | None = Field(None, description='Project description')
    api_key: str | None = Field(None, description='API Key')
    settings: dict | None = Field(None, description='Project settings')
    status: str | None = Field(None, description='Status active/archived')
    map_id: int | None = Field(None, description='Associated map ID')


class GetProjectDetail(ProjectSchemaBase):
    """Project details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Project ID')
    owner_id: int = Field(description='Owner ID')
    map_id: int | None = Field(None, description='Associated map ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
