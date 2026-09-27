from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, TimeZone, id_key


class MCPServer(Base, SoftDeleteMixin):
    """MCP servers table"""

    __tablename__ = 'oa_mcp_server'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Owner ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='Server name')
    connection_config: Mapped[dict] = mapped_column(sa.JSON(), comment='Connection config')
    description: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='Description')
    transport_type: Mapped[str] = mapped_column(
        sa.String(32), default='sse', comment='Transport type stdio/sse/streamable_http'
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, comment='Whether enabled')
    last_discovered_at: Mapped[datetime | None] = mapped_column(
        TimeZone, default=None, init=False, comment='Last discovered time'
    )
    visibility: Mapped[str] = mapped_column(
        sa.String(16), default='private', comment='Visibility private/public/official'
    )
