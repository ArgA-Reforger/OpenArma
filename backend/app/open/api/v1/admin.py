from typing import Annotated

from fastapi import APIRouter, Path, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.conversation.model.conversation import Conversation
from backend.app.open.model.command_pool import CommandPool
from backend.app.open.model.situation_log import SituationLog
from backend.app.project.crud.crud_project import project_dao
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession

router = APIRouter(dependencies=[DependsJwtAuth])


async def _get_arma_conversation_ids(db, project_id: int) -> list[str]:
    """Get all Arma conversation IDs for a project."""
    stmt = select(Conversation.id).where(
        Conversation.project_id == project_id,
        Conversation.source == 'arma',
        Conversation.del_flag == False,  # noqa: E712
    )
    result = await db.execute(stmt)
    return [str(cid) for cid in result.scalars().all()]


async def _get_group_conversation_ids(db, project_id: int, group_id: int) -> list[str]:
    """Get Arma conversation IDs belonging to a specific conversation group."""
    stmt = select(Conversation.id).where(
        Conversation.project_id == project_id,
        Conversation.conversation_group_id == group_id,
        Conversation.source == 'arma',
        Conversation.del_flag == False,  # noqa: E712
    )
    result = await db.execute(stmt)
    return [str(cid) for cid in result.scalars().all()]


@router.get('/{project_id}/commands')
async def list_commands(
    db: CurrentSession,
    request: Request,
    project_id: Annotated[int, Path(description='Project ID')],
    group_id: Annotated[int | None, Query(description='Filter by conversation group')] = None,
    status: Annotated[str | None, Query(description='Filter by status')] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ResponseSchemaModel:
    project = await project_dao.get(db, project_id)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='Project not found')

    if group_id:
        conv_ids = await _get_group_conversation_ids(db, project_id, group_id)
    else:
        conv_ids = await _get_arma_conversation_ids(db, project_id)
    if not conv_ids:
        return response_base.success(data={'items': [], 'total': 0})

    stmt = select(CommandPool).where(CommandPool.conversation_id.in_(conv_ids))
    count_stmt = select(func.count()).select_from(CommandPool).where(
        CommandPool.conversation_id.in_(conv_ids)
    )

    if status:
        stmt = stmt.where(CommandPool.status == status)
        count_stmt = count_stmt.where(CommandPool.status == status)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(CommandPool.created_time.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    data = {
        'items': [
            {
                'id': str(item.id),
                'conversation_id': item.conversation_id,
                'request_id': item.request_id,
                'status': item.status,
                'orders_json': item.orders_json,
                'delivered_at': item.delivered_at.isoformat() if item.delivered_at else None,
                'created_time': item.created_time.isoformat() if item.created_time else None,
            }
            for item in items
        ],
        'total': total,
    }
    return response_base.success(data=data)


@router.get('/{project_id}/logs')
async def list_situation_logs(
    db: CurrentSession,
    request: Request,
    project_id: Annotated[int, Path(description='Project ID')],
    group_id: Annotated[int | None, Query(description='Filter by conversation group')] = None,
    priority: Annotated[str | None, Query(description='Filter by priority')] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ResponseSchemaModel:
    project = await project_dao.get(db, project_id)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='Project not found')

    if group_id:
        conv_ids = await _get_group_conversation_ids(db, project_id, group_id)
    else:
        conv_ids = await _get_arma_conversation_ids(db, project_id)
    if not conv_ids:
        return response_base.success(data={'items': [], 'total': 0})

    stmt = select(SituationLog).where(SituationLog.conversation_id.in_(conv_ids))
    count_stmt = select(func.count()).select_from(SituationLog).where(
        SituationLog.conversation_id.in_(conv_ids)
    )

    if priority:
        stmt = stmt.where(SituationLog.priority == priority)
        count_stmt = count_stmt.where(SituationLog.priority == priority)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(SituationLog.created_time.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    data = {
        'items': [
            {
                'id': str(item.id),
                'conversation_id': item.conversation_id,
                'request_id': item.request_id,
                'priority': item.priority,
                'situation_json': item.situation_json,
                'response_json': item.response_json,
                'processing_time_ms': item.processing_time_ms,
                'created_time': item.created_time.isoformat() if item.created_time else None,
            }
            for item in items
        ],
        'total': total,
    }
    return response_base.success(data=data)


@router.get('/{project_id}/situation')
async def get_latest_situation(
    db: CurrentSession,
    request: Request,
    project_id: Annotated[int, Path(description='Project ID')],
) -> ResponseSchemaModel:
    """Return the latest situation report data for the project's active Arma conversation."""
    project = await project_dao.get(db, project_id)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='Project not found')

    conv_ids = await _get_arma_conversation_ids(db, project_id)
    if not conv_ids:
        return response_base.success(data=None)

    stmt = (
        select(SituationLog)
        .where(SituationLog.conversation_id.in_(conv_ids))
        .order_by(SituationLog.created_time.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    latest = result.scalar_one_or_none()

    if not latest or not latest.situation_json:
        return response_base.success(data=None)

    sit = latest.situation_json
    groups = sit.get('groups', [])
    llm_groups = [g for g in groups if g.get('control', 'llm') == 'llm']
    other_groups = [g for g in groups if g.get('control', 'llm') != 'llm']

    pending_stmt = (
        select(func.count())
        .select_from(CommandPool)
        .where(
            CommandPool.conversation_id.in_(conv_ids),
            CommandPool.status == 'pending',
        )
    )
    pending_count = (await db.execute(pending_stmt)).scalar() or 0

    data = {
        'request_id': latest.request_id,
        'timestamp': sit.get('timestamp'),
        'game_state': sit.get('game_state', {}),
        'llm_groups': llm_groups,
        'other_groups': other_groups,
        'total_groups': len(groups),
        'pending_commands': pending_count,
        'last_processing_time_ms': latest.processing_time_ms,
        'last_orders': latest.response_json,
        'updated_at': latest.created_time.isoformat() if latest.created_time else None,
    }
    return response_base.success(data=data)


@router.post('/{project_id}/regenerate-key')
async def regenerate_api_key(
    db: CurrentSession,
    request: Request,
    project_id: Annotated[int, Path(description='Project ID')],
) -> ResponseSchemaModel:
    project = await project_dao.get(db, project_id)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='Project not found')

    import secrets

    new_key = f'oa_{secrets.token_urlsafe(32)}'
    project.api_key = new_key
    await db.commit()

    return response_base.success(data={'api_key': new_key})


@router.post('/{project_id}/generate-ao-briefing', summary='Generate AO terrain briefing')
async def generate_ao_briefing_endpoint(
    request: Request,
    db: CurrentSession,
    project_id: Annotated[int, Path(description='Project ID')],
    group_id: Annotated[int | None, Query(description='Conversation group ID')] = None,
    conversation_id: Annotated[int | None, Query(description='Conversation ID to read mission from')] = None,
) -> ResponseSchemaModel:
    project = await project_dao.get(db, project_id)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='Project not found')

    map_id = project.map_id if project.map_id else None
    if not map_id:
        raise errors.NotFoundError(msg='No map configured — set map in Project Settings → Map tab')

    mission: dict = {}

    if conversation_id:
        from sqlalchemy import select as sa_select
        from backend.app.conversation.model import Conversation
        conv_stmt = (
            sa_select(Conversation.mission_objective)
            .where(Conversation.id == conversation_id)
            .where(Conversation.del_flag == False)  # noqa: E712
        )
        conv_result = await db.execute(conv_stmt)
        conv_mission = conv_result.scalar_one_or_none()
        if conv_mission:
            mission = conv_mission

    if not mission:
        from backend.app.open.crud.crud_arma_config import arma_config_dao
        arma_config = None
        if group_id:
            arma_config = await arma_config_dao.get_by_conversation_group(db, group_id)
        if not arma_config:
            arma_config = await arma_config_dao.get_by_project(db, project_id)

        if arma_config:
            mission = arma_config.mission_objective or {}

        if not mission and arma_config:
            from sqlalchemy import select as sa_select
            from backend.app.conversation.model import Conversation
            group_id_val = arma_config.conversation_group_id
            if group_id_val:
                conv_stmt = (
                    sa_select(Conversation.mission_objective)
                    .where(Conversation.conversation_group_id == group_id_val)
                    .where(Conversation.del_flag == False)  # noqa: E712
                    .where(Conversation.mission_objective.isnot(None))
                    .limit(1)
                )
                conv_result = await db.execute(conv_stmt)
                conv_mission = conv_result.scalar_one_or_none()
                if conv_mission:
                    mission = conv_mission

    ao_config = mission.get('ao') if mission else None
    if not ao_config:
        focus_points = []
        targets = mission.get('primary_targets', []) if mission else []
        for t in targets:
            pos = t.get('position')
            if pos:
                focus_points.append({'position': pos[:2] if len(pos) >= 2 else pos, 'label': t.get('name', '')})
        if focus_points:
            ao_config = {'focus_points': focus_points}
        else:
            raise errors.NotFoundError(msg='No AO or mission targets configured')

    from backend.app.map.crud.crud_map import map_dao
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')

    from backend.app.map.service.ao_briefing import cache_briefing, generate_ao_briefing
    briefing = await generate_ao_briefing(db, game_map, ao_config)
    await cache_briefing(project_id, briefing)

    return response_base.success(data={
        'briefing_length': len(briefing),
        'briefing_preview': briefing[:500] + '...' if len(briefing) > 500 else briefing,
    })
