import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, UniversalText, id_key


class Message(Base, SoftDeleteMixin):
    """Message table"""

    __tablename__ = 'oa_message'

    id: Mapped[id_key] = mapped_column(init=False)
    conversation_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Conversation ID')
    role: Mapped[str] = mapped_column(sa.String(32), comment='Role user/assistant/system')
    content: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='Content')
    structured_data: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='Structured data')
    metadata_: Mapped[dict | None] = mapped_column('metadata', sa.JSON(), default=None, comment='Message metadata')
    parent_message_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='Parent message ID')
