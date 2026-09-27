import sys

from collections.abc import AsyncGenerator
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import URL, text as sa_text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.common.enums import DataBaseType
from backend.common.log import log
from backend.common.model import MappedBase
from backend.core.conf import settings


def create_database_url(*, unittest: bool = False, with_database: bool = True) -> URL:
    """
    Create the database connection URL

    :param unittest: whether this is for unit tests
    :param with_database: whether to include the database name (not needed when creating a database)
    :return:
    """
    if with_database:
        database = settings.DATABASE_SCHEMA if not unittest else f'{settings.DATABASE_SCHEMA}_test'
    else:
        database = None if DataBaseType.mysql == settings.DATABASE_TYPE else 'postgres'

    url = URL.create(
        drivername='mysql+asyncmy' if DataBaseType.mysql == settings.DATABASE_TYPE else 'postgresql+asyncpg',
        username=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        database=database,
    )
    if DataBaseType.mysql == settings.DATABASE_TYPE and with_database:
        url = url.update_query_dict({'charset': settings.DATABASE_CHARSET})
    return url


def create_database_async_engine(url: str | URL) -> AsyncEngine:
    """
    Create the database async engine

    :param url: database connection URL
    :return:
    """
    try:
        return create_async_engine(
            url,
            echo=settings.DATABASE_ECHO,
            echo_pool=settings.DATABASE_POOL_ECHO,
            future=True,
            # Medium concurrency
            pool_size=10,  # low: - high: +
            max_overflow=20,  # low: - high: +
            pool_timeout=30,  # low: + high: -
            pool_recycle=3600,  # low: + high: -
            pool_pre_ping=True,  # low: False high: True
            pool_use_lifo=False,  # low: False high: True
        )
    except Exception as e:
        log.error(f'Database connection failed {e}')
        sys.exit()


def create_database_async_session(engine: AsyncEngine) -> async_sessionmaker[AsyncSession | Any]:
    """
    Create the database async session

    :param engine: database async engine
    :return:
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,  # Disable autoflush
        expire_on_commit=False,  # Disable expire-on-commit
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session"""
    async with async_db_session() as session:
        yield session


async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with a transaction"""
    async with async_db_session.begin() as session:
        yield session


async def create_tables() -> None:
    """Create the database tables"""
    async with async_engine.begin() as coon:
        if DataBaseType.mysql != settings.DATABASE_TYPE:
            await coon.execute(sa_text('CREATE EXTENSION IF NOT EXISTS vector'))
        await coon.run_sync(MappedBase.metadata.create_all)


async def drop_tables() -> None:
    """Drop the database tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(MappedBase.metadata.drop_all)


def uuid4_str() -> str:
    """UUID type compatibility workaround for the database engine"""
    return str(uuid4())


# SQLA database connection URL
SQLALCHEMY_DATABASE_URL = create_database_url()

# SQLA async engine and session
async_engine = create_database_async_engine(SQLALCHEMY_DATABASE_URL)
async_db_session = create_database_async_session(async_engine)

# Session Annotated
CurrentSession = Annotated[AsyncSession, Depends(get_db)]
CurrentSessionTransaction = Annotated[AsyncSession, Depends(get_db_transaction)]
