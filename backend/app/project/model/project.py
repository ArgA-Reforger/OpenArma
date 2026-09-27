import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, id_key


class Project(Base, SoftDeleteMixin):
    """Projects table"""

    __tablename__ = 'oa_project'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(128), comment='Project name')
    owner_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Owner ID')
    description: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='Project description')
    api_key: Mapped[str | None] = mapped_column(sa.String(128), default=None, unique=True, comment='API Key')
    settings: Mapped[dict | None] = mapped_column(sa.JSON(), default=dict, comment='Project settings')
    status: Mapped[str] = mapped_column(sa.String(32), default='active', comment='Status active/archived')
    map_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='Associated map ID')
