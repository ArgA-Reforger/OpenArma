import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class AgentTool(Base):
    """智能体-工具绑定表"""

    __tablename__ = 'oa_agent_tool'

    id: Mapped[id_key] = mapped_column(init=False)
    agent_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Agent ID')
    mcp_tool_id: Mapped[int] = mapped_column(sa.BigInteger, comment='MCP 工具 ID')
    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, comment='是否启用')
