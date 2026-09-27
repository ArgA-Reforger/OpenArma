from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query, Request

from backend.app.billing.service.usage_service import usage_service
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession
from backend.utils.timezone import timezone

router = APIRouter()


def _parse_range(
    start_date: str | None,
    end_date: str | None,
) -> tuple[datetime, datetime]:
    now = timezone.now()
    if end_date:
        end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
        end = timezone.from_datetime(end)
    else:
        end = now

    if start_date:
        start = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0)
        start = timezone.from_datetime(start)
    else:
        start = end - timedelta(days=30)

    return start, end


@router.get('/records', summary='Call details', dependencies=[DependsJwtAuth])
async def usage_records(
    request: Request,
    db: CurrentSession,
    start_date: Annotated[str | None, Query(description='Start date YYYY-MM-DD')] = None,
    end_date: Annotated[str | None, Query(description='End date YYYY-MM-DD')] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    call_type: Annotated[str | None, Query(description='Call type chat/title_gen/rag_embed')] = None,
    status: Annotated[str | None, Query(description='Status success/failed/partial')] = None,
    provider_type: Annotated[str | None, Query(description='Provider type')] = None,
) -> ResponseSchemaModel[dict]:
    start, end = _parse_range(start_date, end_date)
    data = await usage_service.get_records(
        db, request.user.id, start, end,
        page=page, size=size, call_type=call_type,
        status=status, provider_type=provider_type,
    )
    return response_base.success(data=data)


@router.get('/summary', summary='Usage summary', dependencies=[DependsJwtAuth])
async def usage_summary(
    request: Request,
    db: CurrentSession,
    start_date: Annotated[str | None, Query(description='Start date YYYY-MM-DD')] = None,
    end_date: Annotated[str | None, Query(description='End date YYYY-MM-DD')] = None,
) -> ResponseSchemaModel[dict]:
    start, end = _parse_range(start_date, end_date)
    data = await usage_service.get_summary(db, request.user.id, start, end)
    return response_base.success(data=data)


@router.get('/by-provider', summary='Statistics by provider/model', dependencies=[DependsJwtAuth])
async def usage_by_provider(
    request: Request,
    db: CurrentSession,
    start_date: Annotated[str | None, Query(description='Start date YYYY-MM-DD')] = None,
    end_date: Annotated[str | None, Query(description='End date YYYY-MM-DD')] = None,
) -> ResponseSchemaModel[list[dict]]:
    start, end = _parse_range(start_date, end_date)
    data = await usage_service.get_by_provider(db, request.user.id, start, end)
    return response_base.success(data=data)


@router.get('/by-project', summary='Statistics by project', dependencies=[DependsJwtAuth])
async def usage_by_project(
    request: Request,
    db: CurrentSession,
    start_date: Annotated[str | None, Query(description='Start date YYYY-MM-DD')] = None,
    end_date: Annotated[str | None, Query(description='End date YYYY-MM-DD')] = None,
) -> ResponseSchemaModel[list[dict]]:
    start, end = _parse_range(start_date, end_date)
    data = await usage_service.get_by_project(db, request.user.id, start, end)
    return response_base.success(data=data)


@router.get('/daily', summary='Daily trend', dependencies=[DependsJwtAuth])
async def usage_daily(
    request: Request,
    db: CurrentSession,
    start_date: Annotated[str | None, Query(description='Start date YYYY-MM-DD')] = None,
    end_date: Annotated[str | None, Query(description='End date YYYY-MM-DD')] = None,
) -> ResponseSchemaModel[list[dict]]:
    start, end = _parse_range(start_date, end_date)
    data = await usage_service.get_daily(db, request.user.id, start, end)
    return response_base.success(data=data)
