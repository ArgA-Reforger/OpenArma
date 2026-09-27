import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base, SoftDeleteMixin, UniversalText, id_key


class Topology(Base, SoftDeleteMixin):
    """Topology orchestration resource table"""

    __tablename__ = 'oa_topology'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Owner ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='Topology name')
    description: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='Description')
    topology_json: Mapped[dict | None] = mapped_column(
        sa.JSON(), default=None, comment='Topology definition {nodes, edges}'
    )
    visibility: Mapped[str] = mapped_column(
        sa.String(16), default='private', comment='Visibility private/public/official'
    )
