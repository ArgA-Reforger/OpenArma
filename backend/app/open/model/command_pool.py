from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, id_key


class CommandPool(Base):
    """指令池表"""

    __tablename__ = 'oa_command_pool'

    id: Mapped[id_key] = mapped_column(init=False)
    conversation_id: Mapped[str] = mapped_column(sa.String(64), index=True, comment='对话 ID')
    request_id: Mapped[int] = mapped_column(sa.Integer, comment='对应的请求 ID')
    project_id: Mapped[int | None] = mapped_column(sa.BigInteger, index=True, default=None, comment='项目 ID')
    orders_json: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='指令 JSON')
    status: Mapped[str] = mapped_column(sa.String(16), default='pending', comment='pending/delivered/expired')
    delivered_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment='交付时间')
