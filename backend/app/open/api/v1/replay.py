from fastapi import APIRouter, Query
from sqlalchemy import select

from backend.app.open.model.battle_snapshot import BattleSnapshot
from backend.app.project.crud.crud_project import project_dao
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession

router = APIRouter(dependencies=[DependsJwtAuth])


def _build_snapshot_filter(project_id: int, group_id: int | None = None):
    """Build common WHERE clause: prefer conversation_group_id, fallback to project_id."""
    conditions = [BattleSnapshot.project_id == project_id]
    if group_id is not None:
        conditions.append(BattleSnapshot.conversation_group_id == group_id)
    return conditions


@router.get('/replay/{project_id}/metadata', summary='回放元数据')
async def replay_metadata(
    project_id: int,
    db: CurrentSession,
    group_id: int | None = Query(default=None, description='对话组 ID'),
) -> ResponseSchemaModel:
    project = await project_dao.get(db, project_id)
    if not project:
        raise errors.NotFoundError(msg='项目不存在')

    conditions = _build_snapshot_filter(project_id, group_id)
    stmt = (
        select(
            BattleSnapshot.request_id,
            BattleSnapshot.game_time,
            BattleSnapshot.timestamp,
        )
        .where(*conditions)
        .order_by(BattleSnapshot.request_id.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return response_base.success(data={'total_frames': 0, 'sessions': []})

    sessions: list[dict] = []
    current_session: dict | None = None
    prev_ts = 0

    for req_id, game_time, ts in rows:
        gap = ts - prev_ts if prev_ts else 0
        if gap > 600 or current_session is None:
            if current_session:
                sessions.append(current_session)
            current_session = {
                'start_frame': req_id,
                'end_frame': req_id,
                'start_time': game_time,
                'end_time': game_time,
                'frame_count': 1,
            }
        else:
            current_session['end_frame'] = req_id
            current_session['end_time'] = game_time
            current_session['frame_count'] += 1
        prev_ts = ts

    if current_session:
        sessions.append(current_session)

    return response_base.success(data={
        'total_frames': len(rows),
        'sessions': sessions,
    })


@router.get('/replay/{project_id}/frames', summary='批量帧数据(轻量)')
async def replay_frames(
    project_id: int,
    db: CurrentSession,
    from_frame: int = Query(alias='from', ge=1),
    to_frame: int = Query(alias='to', ge=1),
    group_id: int | None = Query(default=None),
) -> ResponseSchemaModel:
    project = await project_dao.get(db, project_id)
    if not project:
        raise errors.NotFoundError(msg='项目不存在')

    if to_frame - from_frame > 200:
        raise errors.RequestError(msg='单次最多请求200帧')

    conditions = _build_snapshot_filter(project_id, group_id)
    stmt = (
        select(BattleSnapshot)
        .where(
            *conditions,
            BattleSnapshot.request_id >= from_frame,
            BattleSnapshot.request_id <= to_frame,
        )
        .order_by(BattleSnapshot.request_id.asc())
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    frames = []
    for s in snapshots:
        groups_light = []
        for g in (s.groups or []):
            groups_light.append({
                'id': g.get('id'),
                'label': g.get('label'),
                'faction': g.get('faction'),
                'control': g.get('control'),
                'position': g.get('position'),
                'member_count': g.get('member_count'),
                'casualties': g.get('casualties'),
                'current_waypoint_type': g.get('current_waypoint_type'),
                'combat_mode': g.get('combat_mode'),
                'speed_mode': g.get('speed_mode'),
                'formation': g.get('formation'),
            })

        units_light = []
        for u in (s.units or []):
            units_light.append({
                'entity_id': u.get('entity_id'),
                'group_id': u.get('group_id'),
                'faction': u.get('faction'),
                'position': u.get('position'),
                'life_state': u.get('life_state'),
                'health': u.get('health'),
            })

        enemies_light = []
        for e in (s.known_enemies or []):
            enemies_light.append({
                'entity_id': e.get('entity_id'),
                'position': e.get('position'),
                'perceived_faction': e.get('perceived_faction'),
                'observer_faction': e.get('observer_faction'),
                'distance': e.get('distance'),
            })

        frames.append({
            'request_id': s.request_id,
            'game_time': s.game_time,
            'timestamp': s.timestamp,
            'groups': groups_light,
            'units': units_light,
            'known_enemies': enemies_light,
            'events': s.events or [],
        })

    return response_base.success(data={'frames': frames})


@router.get('/replay/{project_id}/frame/{request_id}', summary='单帧完整数据')
async def replay_frame_detail(
    project_id: int,
    request_id: int,
    db: CurrentSession,
    group_id: int | None = Query(default=None),
) -> ResponseSchemaModel:
    project = await project_dao.get(db, project_id)
    if not project:
        raise errors.NotFoundError(msg='项目不存在')

    conditions = _build_snapshot_filter(project_id, group_id)
    stmt = (
        select(BattleSnapshot)
        .where(*conditions, BattleSnapshot.request_id == request_id)
    )
    result = await db.execute(stmt)
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        raise errors.NotFoundError(msg='帧数据不存在')

    return response_base.success(data={
        'request_id': snapshot.request_id,
        'game_time': snapshot.game_time,
        'timestamp': snapshot.timestamp,
        'game_state': snapshot.game_state,
        'groups': snapshot.groups,
        'units': snapshot.units,
        'vehicles': snapshot.vehicles,
        'known_enemies': snapshot.known_enemies,
        'events': snapshot.events,
        'markers': snapshot.markers,
        'human_messages': snapshot.human_messages,
        'response_json': snapshot.response_json,
        'processing_time_ms': snapshot.processing_time_ms,
    })
