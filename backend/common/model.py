from datetime import datetime
from typing import Annotated

from sqlalchemy import BigInteger, DateTime, Text, TypeDecorator
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, declared_attr, mapped_column

from backend.common.enums import DataBaseType, PrimaryKeyType
from backend.core.conf import settings
from backend.utils.snowflake import snowflake
from backend.utils.timezone import timezone

# Generic Mapped-type primary key, must be added manually, see the usage below
# MappedBase -> id: Mapped[id_key]
# DataClassBase && Base -> id: Mapped[id_key] = mapped_column(init=False)
id_key = Annotated[
    int,
    mapped_column(
        BigInteger,
        primary_key=True,
        unique=True,
        index=True,
        autoincrement=True,
        sort_order=-999,
        comment='Primary key ID',
    )
    if PrimaryKeyType.autoincrement == settings.DATABASE_PK_MODE
    # Snowflake algorithm Mapped-type primary key
    # Details: https://fastapi-practices.github.io/fastapi_best_architecture_docs/backend/reference/pk.html
    else mapped_column(
        BigInteger,
        primary_key=True,
        unique=True,
        index=True,
        default=snowflake.generate,
        sort_order=-999,
        comment='Snowflake algorithm primary key ID',
    ),
]


class UniversalText(TypeDecorator[str]):
    """PostgreSQL / MySQL compatible (long) text type"""

    impl = LONGTEXT if DataBaseType.mysql == settings.DATABASE_TYPE else Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:  # noqa: ANN001
        return value

    def process_result_value(self, value: str | None, dialect) -> str | None:  # noqa: ANN001
        return value


class TimeZone(TypeDecorator[datetime]):
    """PostgreSQL / MySQL compatible timezone-aware type"""

    impl = DateTime(timezone=True)
    cache_ok = True

    @property
    def python_type(self) -> type[datetime]:
        return datetime

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:  # noqa: ANN001
        if value is not None and value.utcoffset() != timezone.now().utcoffset():
            # TODO handle daylight saving time offset
            value = timezone.from_datetime(value)
        return value

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:  # noqa: ANN001
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.tz_info)
        return value


# Mixin: an object-oriented programming concept that makes the structure clearer, `Wiki <https://en.wikipedia.org/wiki/Mixin/>`__
class UserMixin(MappedAsDataclass):
    """User Mixin data class"""

    created_by: Mapped[int] = mapped_column(sort_order=998, comment='Creator')
    updated_by: Mapped[int | None] = mapped_column(init=False, default=None, sort_order=998, comment='Last modifier')


class DateTimeMixin(MappedAsDataclass):
    """Date/time Mixin data class"""

    created_time: Mapped[datetime] = mapped_column(
        TimeZone,
        init=False,
        default_factory=timezone.now,
        sort_order=999,
        comment='Creation time',
    )
    updated_time: Mapped[datetime | None] = mapped_column(
        TimeZone,
        init=False,
        onupdate=timezone.now,
        sort_order=999,
        comment='Last update time',
    )


class SoftDeleteMixin(MappedAsDataclass):
    """Soft-delete Mixin data class, used uniformly by OA business tables"""

    del_flag: Mapped[bool] = mapped_column(
        init=False, default=False, sort_order=999, comment='Delete flag (False = exists, True = deleted)'
    )


class MappedBase(AsyncAttrs, DeclarativeBase):
    """
    Declarative base class, serving as the parent of all base or data model classes

    `AsyncAttrs <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncAttrs>`__

    `DeclarativeBase <https://docs.sqlalchemy.org/en/20/orm/declarative_config.html>`__

    `mapped_column() <https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.mapped_column>`__
    """

    @declared_attr.directive
    def __tablename__(self) -> str:
        """Generate the table name"""
        return self.__name__.lower()

    @declared_attr.directive
    def __table_args__(self) -> dict:
        """Table configuration"""
        return {'comment': self.__doc__ or ''}


class DataClassBase(MappedAsDataclass, MappedBase):
    """
    Declarative data class base class with dataclass integration, allowing more advanced configuration, but you
    must be aware of some of its characteristics, especially when used together with DeclarativeBase

    `MappedAsDataclass <https://docs.sqlalchemy.org/en/20/orm/dataclasses.html#orm-declarative-native-dataclasses>`__
    """

    __abstract__ = True


class Base(DataClassBase, DateTimeMixin):
    """
    Declarative data class base class with dataclass integration, including the Mixin data class base table structure
    """

    __abstract__ = True
