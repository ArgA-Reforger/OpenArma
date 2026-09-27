import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base, id_key


class ConversationResource(Base):
    """Conversation-resource binding table (KB / MCP)"""

    __tablename__ = 'oa_conversation_resource'

    id: Mapped[id_key] = mapped_column(init=False)
    conversation_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Conversation ID')
    resource_type: Mapped[str] = mapped_column(sa.String(32), comment='Resource type knowledge_base/mcp_server')
    resource_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Resource ID')
