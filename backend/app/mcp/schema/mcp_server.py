from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class MCPServerSchemaBase(SchemaBase):
    """MCP 服务器基础模型"""

    name: str = Field(description='服务器名称')
    description: str | None = Field(None, description='描述')
    transport_type: str = Field(default='sse', description='传输类型')
    connection_config: dict = Field(description='连接配置')
    is_active: bool = Field(default=True, description='是否启用')
    visibility: str = Field(default='private', description='可见性 private/public/official')


class CreateMCPServerParam(MCPServerSchemaBase):
    """创建 MCP 服务器参数"""


class BindProjectMCPServerParam(SchemaBase):
    """绑定项目 MCP 服务器参数"""

    mcp_server_id: int = Field(description='MCP 服务器 ID')


class BindAgentToolParam(SchemaBase):
    """绑定 Agent 工具参数"""

    mcp_tool_id: int = Field(description='MCP 工具 ID')


class UpdateMCPServerParam(SchemaBase):
    """更新 MCP 服务器参数"""

    name: str | None = Field(None, description='服务器名称')
    description: str | None = Field(None, description='描述')
    transport_type: str | None = Field(None, description='传输类型')
    connection_config: dict | None = Field(None, description='连接配置')
    is_active: bool | None = Field(None, description='是否启用')
    visibility: str | None = Field(None, description='可见性 private/public/official')


class GetMCPServerDetail(MCPServerSchemaBase):
    """MCP 服务器详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='主键 ID')
    user_id: int = Field(description='所有者 ID')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
    last_discovered_at: datetime | None = Field(None, description='最后发现时间')
    tools: list['GetMCPToolDetail'] = Field(default_factory=list, description='已发现的工具')


from backend.app.mcp.schema.mcp_tool import GetMCPToolDetail  # noqa: E402

GetMCPServerDetail.model_rebuild()
