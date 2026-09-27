from datetime import datetime

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, id_key
from backend.database.db import uuid4_str
from backend.utils.timezone import timezone


class User(Base):
    """User table"""

    __tablename__ = 'sys_user'

    id: Mapped[id_key] = mapped_column(init=False)
    uuid: Mapped[str] = mapped_column(sa.String(64), init=False, default_factory=uuid4_str, unique=True)
    username: Mapped[str] = mapped_column(sa.String(64), unique=True, index=True, comment='Username')
    nickname: Mapped[str] = mapped_column(sa.String(64), comment='Nickname')
    password: Mapped[str | None] = mapped_column(sa.String(256), comment='Password')
    salt: Mapped[bytes | None] = mapped_column(sa.LargeBinary(255), comment='Encryption salt')
    email: Mapped[str | None] = mapped_column(sa.String(256), default=None, unique=True, index=True, comment='Email address')
    phone: Mapped[str | None] = mapped_column(sa.String(11), default=None, comment='Phone number')
    avatar: Mapped[str | None] = mapped_column(sa.String(256), default=None, comment='Avatar')
    status: Mapped[int] = mapped_column(default=1, index=True, comment='User account status (0 disabled, 1 normal)')
    is_superuser: Mapped[bool] = mapped_column(default=False, comment='Superuser privileges (0 no, 1 yes)')
    is_staff: Mapped[bool] = mapped_column(default=False, comment='Can log in to the backend (0 no, 1 yes)')
    is_multi_login: Mapped[bool] = mapped_column(default=False, comment='Whether multi-device login is allowed (0 no, 1 yes)')
    join_time: Mapped[datetime] = mapped_column(TimeZone, init=False, default_factory=timezone.now, comment='Registration time')
    last_login_time: Mapped[datetime | None] = mapped_column(
        TimeZone, init=False, onupdate=timezone.now, comment='Last login time'
    )
    last_password_changed_time: Mapped[datetime | None] = mapped_column(
        TimeZone, init=False, default_factory=timezone.now, comment='Last password change time'
    )

    # Logical foreign key
    dept_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='Department reference ID')
