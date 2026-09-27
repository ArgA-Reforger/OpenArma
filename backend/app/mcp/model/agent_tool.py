import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class AgentTool(Base):
    """Agent-tool bindings table"""

    __tablename__ = 'oa_agent_tool'

    id: Mapped[id_key] = mapped_column(init=False)
    agent_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Agent ID')
    mcp_tool_id: Mapped[int] = mapped_column(sa.BigInteger, comment='MCP tool ID')
    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, comment='Whether enabled')
