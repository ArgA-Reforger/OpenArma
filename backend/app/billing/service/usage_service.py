from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.billing.crud.crud_usage import usage_dao


class UsageService:

    @staticmethod
    async def get_records(
        db: AsyncSession, user_id: int, start: datetime, end: datetime,
        *, page: int = 1, size: int = 20, call_type: str | None = None,
        status: str | None = None, provider_type: str | None = None,
    ) -> dict:
        return await usage_dao.get_records(
            db, user_id, start, end,
            page=page, size=size, call_type=call_type,
            status=status, provider_type=provider_type,
        )

    @staticmethod
    async def get_summary(db: AsyncSession, user_id: int, start: datetime, end: datetime) -> dict:
        return await usage_dao.get_summary(db, user_id, start, end)

    @staticmethod
    async def get_by_provider(db: AsyncSession, user_id: int, start: datetime, end: datetime) -> list[dict]:
        return await usage_dao.get_by_provider(db, user_id, start, end)

    @staticmethod
    async def get_by_project(db: AsyncSession, user_id: int, start: datetime, end: datetime) -> list[dict]:
        return await usage_dao.get_by_project(db, user_id, start, end)

    @staticmethod
    async def get_daily(db: AsyncSession, user_id: int, start: datetime, end: datetime) -> list[dict]:
        return await usage_dao.get_daily(db, user_id, start, end)


usage_service: UsageService = UsageService()
