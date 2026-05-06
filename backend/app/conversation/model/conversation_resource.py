import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base, id_key


class ConversationResource(Base):
    """对话-资源绑定表（KB / MCP）"""

    __tablename__ = 'oa_conversation_resource'

    id: Mapped[id_key] = mapped_column(init=False)
    conversation_id: Mapped[int] = mapped_column(sa.BigInteger, comment='对话 ID')
    resource_type: Mapped[str] = mapped_column(sa.String(32), comment='资源类型 knowledge_base/mcp_server')
    resource_id: Mapped[int] = mapped_column(sa.BigInteger, comment='资源 ID')
