import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class SituationLog(Base):
    """态势日志表"""

    __tablename__ = 'oa_situation_log'

    id: Mapped[id_key] = mapped_column(init=False)
    conversation_id: Mapped[str] = mapped_column(sa.String(64), index=True, comment='对话 ID')
    request_id: Mapped[int] = mapped_column(sa.Integer, comment='请求 ID')
    priority: Mapped[str] = mapped_column(sa.String(16), default='normal', comment='优先级 normal/urgent')
    situation_json: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='态势 JSON')
    response_json: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='响应 JSON')
    processing_time_ms: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='处理耗时(ms)')
