from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, id_key


class CommandPool(Base):
    """Command pool table"""

    __tablename__ = 'oa_command_pool'

    id: Mapped[id_key] = mapped_column(init=False)
    conversation_id: Mapped[str] = mapped_column(sa.String(64), index=True, comment='Conversation ID')
    request_id: Mapped[int] = mapped_column(sa.Integer, comment='Corresponding request ID')
    project_id: Mapped[int | None] = mapped_column(sa.BigInteger, index=True, default=None, comment='Project ID')
    orders_json: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='Orders JSON')
    status: Mapped[str] = mapped_column(sa.String(16), default='pending', comment='pending/delivered/expired')
    delivered_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, comment='Delivered time')
