from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class GetMCPToolDetail(SchemaBase):
    """MCP 工具详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='主键 ID')
    mcp_server_id: int = Field(description='MCP 服务器 ID')
    name: str = Field(description='工具名称')
    description: str | None = Field(None, description='工具描述')
    input_schema: dict | None = Field(None, description='输入参数 JSON Schema')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
