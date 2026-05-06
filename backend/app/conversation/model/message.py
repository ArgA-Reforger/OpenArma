import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, UniversalText, id_key


class Message(Base, SoftDeleteMixin):
    """消息表"""

    __tablename__ = 'oa_message'

    id: Mapped[id_key] = mapped_column(init=False)
    conversation_id: Mapped[int] = mapped_column(sa.BigInteger, comment='对话 ID')
    role: Mapped[str] = mapped_column(sa.String(32), comment='角色 user/assistant/system')
    content: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='内容')
    structured_data: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='结构化数据')
    metadata_: Mapped[dict | None] = mapped_column('metadata', sa.JSON(), default=None, comment='消息元数据')
    parent_message_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='父消息 ID')
