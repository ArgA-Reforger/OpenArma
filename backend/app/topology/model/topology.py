import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base, SoftDeleteMixin, UniversalText, id_key


class Topology(Base, SoftDeleteMixin):
    """拓扑编排资源表"""

    __tablename__ = 'oa_topology'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='所有者 ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='拓扑名称')
    description: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='描述')
    topology_json: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='拓扑定义 {nodes, edges}')
    visibility: Mapped[str] = mapped_column(sa.String(16), default='private', comment='可见性 private/public/official')
