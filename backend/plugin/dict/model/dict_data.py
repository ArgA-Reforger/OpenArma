import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key


class DictData(Base):
    """Dict data table"""

    __tablename__ = 'sys_dict_data'

    id: Mapped[id_key] = mapped_column(init=False)
    type_code: Mapped[str] = mapped_column(sa.String(32), comment='Corresponding dict type code')
    label: Mapped[str] = mapped_column(sa.String(32), comment='Dict label')
    value: Mapped[str] = mapped_column(sa.String(32), comment='Dict value')
    color: Mapped[str | None] = mapped_column(sa.String(32), default=None, comment='Label color')
    sort: Mapped[int] = mapped_column(default=0, comment='Sort order')
    status: Mapped[int] = mapped_column(default=1, comment='Status (0 disabled 1 normal)')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='Remark')

    # Logical foreign key
    type_id: Mapped[int] = mapped_column(sa.BigInteger, default=0, comment='Related dict type ID')
