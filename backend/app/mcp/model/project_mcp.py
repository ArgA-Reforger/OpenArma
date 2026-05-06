import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class ProjectMCP(Base):
    """项目-MCP 绑定表"""

    __tablename__ = 'oa_project_mcp'

    id: Mapped[id_key] = mapped_column(init=False)
    project_id: Mapped[int] = mapped_column(sa.BigInteger, comment='项目 ID')
    mcp_server_id: Mapped[int] = mapped_column(sa.BigInteger, comment='MCP 服务器 ID')
