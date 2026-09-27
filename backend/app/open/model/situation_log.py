import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class SituationLog(Base):
    """Situation log table"""

    __tablename__ = 'oa_situation_log'

    id: Mapped[id_key] = mapped_column(init=False)
    conversation_id: Mapped[str] = mapped_column(sa.String(64), index=True, comment='Conversation ID')
    request_id: Mapped[int] = mapped_column(sa.Integer, comment='Request ID')
    priority: Mapped[str] = mapped_column(sa.String(16), default='normal', comment='Priority normal/urgent')
    situation_json: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='Situation JSON')
    response_json: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='Response JSON')
    processing_time_ms: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Processing duration (ms)')
