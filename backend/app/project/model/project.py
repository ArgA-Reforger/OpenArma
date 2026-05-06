import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, id_key


class Project(Base, SoftDeleteMixin):
    """项目表"""

    __tablename__ = 'oa_project'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(128), comment='项目名称')
    owner_id: Mapped[int] = mapped_column(sa.BigInteger, comment='所有者 ID')
    description: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='项目描述')
    api_key: Mapped[str | None] = mapped_column(sa.String(128), default=None, unique=True, comment='API Key')
    settings: Mapped[dict | None] = mapped_column(sa.JSON(), default=dict, comment='项目设置')
    status: Mapped[str] = mapped_column(sa.String(32), default='active', comment='状态 active/archived')
    map_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='关联地图 ID')
