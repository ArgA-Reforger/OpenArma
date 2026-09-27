import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class Dept(Base):
    """Department table"""

    __tablename__ = 'sys_dept'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(64), comment='Department name')
    sort: Mapped[int] = mapped_column(default=0, comment='Sort order')
    leader: Mapped[str | None] = mapped_column(sa.String(32), default=None, comment='Leader')
    phone: Mapped[str | None] = mapped_column(sa.String(11), default=None, comment='Phone number')
    email: Mapped[str | None] = mapped_column(sa.String(64), default=None, comment='Email address')
    status: Mapped[int] = mapped_column(default=1, comment='Department status (0 disabled, 1 normal)')
    del_flag: Mapped[bool] = mapped_column(default=False, comment='Deletion flag (0 deleted, 1 exists)')

    # Parent department
    parent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, index=True, comment='Parent department ID')
