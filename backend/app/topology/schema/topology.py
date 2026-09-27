from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class TopologySchemaBase(SchemaBase):
    name: str = Field(description='Topology name')
    description: str | None = Field(None, description='Description')
    topology_json: dict | None = Field(None, description='Topology definition {nodes, edges}')
    visibility: str = Field('private', description='Visibility private/public/official')


class CreateTopologyParam(TopologySchemaBase):
    pass


class UpdateTopologyParam(SchemaBase):
    name: str | None = Field(None, description='Topology name')
    description: str | None = Field(None, description='Description')
    topology_json: dict | None = Field(None, description='Topology definition {nodes, edges}')
    visibility: str | None = Field(None, description='Visibility private/public/official')


class GetTopologyDetail(TopologySchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Topology ID')
    user_id: int = Field(description='Owner ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
