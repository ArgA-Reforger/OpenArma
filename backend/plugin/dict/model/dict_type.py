import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key


class DictType(Base):
    """Dict type table"""

    __tablename__ = 'sys_dict_type'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(32), comment='Dict type name')
    code: Mapped[str] = mapped_column(sa.String(32), unique=True, comment='Dict type code')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='Remark')
