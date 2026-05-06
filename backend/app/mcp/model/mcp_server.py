from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, TimeZone, id_key


class MCPServer(Base, SoftDeleteMixin):
    """MCP 服务器表"""

    __tablename__ = 'oa_mcp_server'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='所有者 ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='服务器名称')
    connection_config: Mapped[dict] = mapped_column(sa.JSON(), comment='连接配置')
    description: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='描述')
    transport_type: Mapped[str] = mapped_column(sa.String(32), default='sse', comment='传输类型 stdio/sse/streamable_http')
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, comment='是否启用')
    last_discovered_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None, init=False, comment='最后发现时间')
    visibility: Mapped[str] = mapped_column(sa.String(16), default='private', comment='可见性 private/public/official')
