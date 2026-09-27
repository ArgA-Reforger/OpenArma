import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class MCPTool(Base):
    """MCP tools table"""

    __tablename__ = 'oa_mcp_tool'

    id: Mapped[id_key] = mapped_column(init=False)
    mcp_server_id: Mapped[int] = mapped_column(sa.BigInteger, comment='MCP server ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='Tool name')
    description: Mapped[str | None] = mapped_column(sa.String(1024), default=None, comment='Tool description')
    input_schema: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='Input parameters JSON Schema')
