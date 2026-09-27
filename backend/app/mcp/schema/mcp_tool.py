from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class GetMCPToolDetail(SchemaBase):
    """MCP tool details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Primary key ID')
    mcp_server_id: int = Field(description='MCP server ID')
    name: str = Field(description='Tool name')
    description: str | None = Field(None, description='Tool description')
    input_schema: dict | None = Field(None, description='Input parameters JSON Schema')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
