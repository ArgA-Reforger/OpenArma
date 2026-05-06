from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class TopologySchemaBase(SchemaBase):
    name: str = Field(description='拓扑名称')
    description: str | None = Field(None, description='描述')
    topology_json: dict | None = Field(None, description='拓扑定义 {nodes, edges}')
    visibility: str = Field('private', description='可见性 private/public/official')


class CreateTopologyParam(TopologySchemaBase):
    pass


class UpdateTopologyParam(SchemaBase):
    name: str | None = Field(None, description='拓扑名称')
    description: str | None = Field(None, description='描述')
    topology_json: dict | None = Field(None, description='拓扑定义 {nodes, edges}')
    visibility: str | None = Field(None, description='可见性 private/public/official')


class GetTopologyDetail(TopologySchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Topology ID')
    user_id: int = Field(description='所有者 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
