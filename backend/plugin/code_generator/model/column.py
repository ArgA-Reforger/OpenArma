import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, UniversalText, id_key


class GenColumn(DataClassBase):
    """Code generator model column list"""

    __tablename__ = 'gen_column'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(64), comment='Column name')
    comment: Mapped[str | None] = mapped_column(sa.String(256), default=None, comment='Column description')
    type: Mapped[str] = mapped_column(sa.String(32), default='String', comment='SQLA model column type')
    pd_type: Mapped[str] = mapped_column(sa.String(32), default='str', comment='Pydantic type for the column type')
    default: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='Column default value')
    sort: Mapped[int | None] = mapped_column(default=1, comment='Column sort order')
    length: Mapped[int] = mapped_column(default=0, comment='Column length')
    is_pk: Mapped[bool] = mapped_column(default=False, comment='Whether it is a primary key')
    is_nullable: Mapped[bool] = mapped_column(default=False, comment='Whether it can be null')

    # Logical foreign key
    gen_business_id: Mapped[int] = mapped_column(sa.BigInteger, default=0, comment='Code generator business ID')
