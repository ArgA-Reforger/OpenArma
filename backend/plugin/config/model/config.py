import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key


class Config(Base):
    """Parameter config table"""

    __tablename__ = 'sys_config'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(32), comment='Name')
    type: Mapped[str | None] = mapped_column(sa.String(32), server_default=None, comment='Type')
    key: Mapped[str] = mapped_column(sa.String(64), unique=True, comment='Key')
    value: Mapped[str] = mapped_column(UniversalText, comment='Value')
    is_frontend: Mapped[bool] = mapped_column(default=False, comment='Whether it is a frontend parameter')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='Remark')
