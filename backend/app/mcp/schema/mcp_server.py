from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class MCPServerSchemaBase(SchemaBase):
    """Base MCP server model"""

    name: str = Field(description='Server name')
    description: str | None = Field(None, description='Description')
    transport_type: str = Field(default='sse', description='Transport type')
    connection_config: dict = Field(description='Connection config')
    is_active: bool = Field(default=True, description='Whether enabled')
    visibility: str = Field(default='private', description='Visibility private/public/official')


class CreateMCPServerParam(MCPServerSchemaBase):
    """Create MCP server parameters"""


class BindProjectMCPServerParam(SchemaBase):
    """Bind project MCP server parameters"""

    mcp_server_id: int = Field(description='MCP server ID')


class BindAgentToolParam(SchemaBase):
    """Bind agent tool parameters"""

    mcp_tool_id: int = Field(description='MCP tool ID')


class UpdateMCPServerParam(SchemaBase):
    """Update MCP server parameters"""

    name: str | None = Field(None, description='Server name')
    description: str | None = Field(None, description='Description')
    transport_type: str | None = Field(None, description='Transport type')
    connection_config: dict | None = Field(None, description='Connection config')
    is_active: bool | None = Field(None, description='Whether enabled')
    visibility: str | None = Field(None, description='Visibility private/public/official')


class GetMCPServerDetail(MCPServerSchemaBase):
    """MCP server details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Primary key ID')
    user_id: int = Field(description='Owner ID')
    created_time: datetime = Field(description='Creation time')
    updated_time: datetime | None = Field(None, description='Update time')
    last_discovered_at: datetime | None = Field(None, description='Last discovered time')
    tools: list['GetMCPToolDetail'] = Field(default_factory=list, description='Discovered tools')


from backend.app.mcp.schema.mcp_tool import GetMCPToolDetail  # noqa: E402

GetMCPServerDetail.model_rebuild()
