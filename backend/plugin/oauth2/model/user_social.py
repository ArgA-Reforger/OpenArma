import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class UserSocial(Base):
    """User social table (OAuth2)"""

    __tablename__ = 'sys_user_social'

    id: Mapped[id_key] = mapped_column(init=False)
    sid: Mapped[str] = mapped_column(sa.String(256), comment='Third-party user ID')
    source: Mapped[str] = mapped_column(sa.String(32), comment='Third-party user source')

    # Logical foreign key
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Related user ID')
