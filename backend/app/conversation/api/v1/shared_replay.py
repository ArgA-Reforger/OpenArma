"""Public replay API — accessible via share_code, no JWT required.

Reuses the same snapshot query logic as the authenticated replay API,
but validates access through the conversation's share_code instead of JWT.
"""

import os
from typing import Annotated

from fastapi import APIRouter, Path, Query
from sqlalchemy import select

from backend.app.conversation.crud.crud_conversation import conversation_dao
from backend.app.map.crud.crud_map import landmark_dao, map_dao, road_dao, zone_dao
from backend.app.map.schema.map import (
    GetLandmarkDetail,
    GetMapDetail,
    GetRoadDetail,
    GetZoneDetail,
)
from backend.app.open.model.battle_snapshot import BattleSnapshot
from backend.app.project.crud.crud_project import project_dao
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.core.path_conf import UPLOAD_DIR
from backend.database.db import CurrentSession

router = APIRouter()

TILE_DIR = UPLOAD_DIR / 'maps'

ANALYSIS_LAYER_NAMES = (
    'vegetation', 'builtup', 'slope', 'hillshade',
    'contour', 'water', 'trafficability', 'cover', 'mcoo',
    'vegetation_real', 'buildings_real', 'roads', 'features',
)


async def _resolve_share(db, share_code: str):
    """Validate share_code and return (conversation, project)."""
    conv = await conversation_dao.get_by_share_code(db, share_code)
    if not conv:
        raise errors.NotFoundError(msg='分享链接不存在或已过期')
    project = await project_dao.get(db, conv.project_id)
    if not project:
        raise errors.NotFoundError(msg='项目不存在')
    return conv, project


def _build_snapshot_filter(project_id: int, group_id: int | None = None):
    conditions = [BattleSnapshot.project_id == project_id]
    if group_id is not None:
        conditions.append(BattleSnapshot.conversation_group_id == group_id)
    return conditions


@router.get('/{share_code}/replay/info', summary='分享回放基础信息')
async def shared_replay_info(
    db: CurrentSession,
    share_code: Annotated[str, Path(description='分享码')],
) -> ResponseSchemaModel:
    """Return project/map info needed to initialise the replay viewer."""
    conv, project = await _resolve_share(db, share_code)

    if not project.map_id:
        return response_base.success(data={
            'has_replay': False,
            'project_name': project.name,
        })

    group_id = conv.conversation_group_id
    conditions = _build_snapshot_filter(project.id, group_id)
    count_stmt = select(BattleSnapshot.id).where(*conditions).limit(1)
    result = await db.execute(count_stmt)
    has_frames = result.scalar_one_or_none() is not None

    game_map = await map_dao.get(db, project.map_id)
    map_data = None
    if game_map:
        detail = GetMapDetail.model_validate(game_map).model_dump()
        map_data = {
            'id': detail['id'],
            'name': detail['name'],
            'size_x': detail['size_x'],
            'size_z': detail['size_z'],
            'tile_min_zoom': detail.get('tile_min_zoom', 0),
            'tile_max_zoom': detail.get('tile_max_zoom', 4),
        }

    return response_base.success(data={
        'has_replay': has_frames,
        'project_name': project.name,
        'map': map_data,
        'conversation_group_id': conv.conversation_group_id,
    })


@router.get('/{share_code}/replay/metadata', summary='分享回放元数据')
async def shared_replay_metadata(
    db: CurrentSession,
    share_code: Annotated[str, Path(description='分享码')],
) -> ResponseSchemaModel:
    conv, project = await _resolve_share(db, share_code)
    group_id = conv.conversation_group_id

    conditions = _build_snapshot_filter(project.id, group_id)
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


@router.get('/{share_code}/replay/frames', summary='分享回放帧数据')
async def shared_replay_frames(
    db: CurrentSession,
    share_code: Annotated[str, Path(description='分享码')],
    from_frame: int = Query(alias='from', ge=1),
    to_frame: int = Query(alias='to', ge=1),
) -> ResponseSchemaModel:
    conv, project = await _resolve_share(db, share_code)

    if to_frame - from_frame > 200:
        raise errors.RequestError(msg='单次最多请求200帧')

    group_id = conv.conversation_group_id
    conditions = _build_snapshot_filter(project.id, group_id)
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

        frames.append({
            'request_id': s.request_id,
            'game_time': s.game_time,
            'timestamp': s.timestamp,
            'groups': groups_light,
            'units': units_light,
            'known_enemies': [],
            'events': s.events or [],
        })

    return response_base.success(data={'frames': frames})


@router.get('/{share_code}/replay/map/{map_id}', summary='分享回放地图详情')
async def shared_replay_map(
    db: CurrentSession,
    share_code: Annotated[str, Path(description='分享码')],
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    conv, project = await _resolve_share(db, share_code)
    if project.map_id != map_id:
        raise errors.NotFoundError(msg='地图不匹配')

    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')
    return response_base.success(data=GetMapDetail.model_validate(game_map).model_dump())


@router.get('/{share_code}/replay/map/{map_id}/tiles/info', summary='分享回放瓦片信息')
async def shared_replay_tile_info(
    db: CurrentSession,
    share_code: Annotated[str, Path(description='分享码')],
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    conv, project = await _resolve_share(db, share_code)
    if project.map_id != map_id:
        raise errors.NotFoundError(msg='地图不匹配')

    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')

    tile_root = TILE_DIR / str(map_id) / 'tiles'
    available_zooms: list[int] = []
    overview_grid_size = 1
    if os.path.isdir(tile_root):
        for entry in sorted(os.listdir(tile_root)):
            if entry.isdigit() and os.path.isdir(tile_root / entry):
                available_zooms.append(int(entry))
        max_lod = max(available_zooms) if available_zooms else -1
        if max_lod >= 0:
            overview_dir = tile_root / str(max_lod)
            if os.path.isdir(overview_dir):
                overview_grid_size = len([d for d in os.listdir(overview_dir) if os.path.isdir(overview_dir / d)])

    military_root = TILE_DIR / str(map_id) / 'military_tiles'
    military_zooms: list[int] = []
    military_grid_size = 1
    has_military = os.path.isdir(military_root)
    if has_military:
        for entry in sorted(os.listdir(military_root)):
            if entry.isdigit() and os.path.isdir(military_root / entry):
                military_zooms.append(int(entry))
        if military_zooms:
            mil_max = max(military_zooms)
            mil_dir = military_root / str(mil_max)
            if os.path.isdir(mil_dir):
                military_grid_size = len([d for d in os.listdir(mil_dir) if os.path.isdir(mil_dir / d)])

    analysis_tiles: dict[str, dict] = {}
    for layer_name in ANALYSIS_LAYER_NAMES:
        layer_root = TILE_DIR / str(map_id) / f'{layer_name}_tiles'
        if os.path.isdir(layer_root):
            layer_zooms = sorted(
                int(e) for e in os.listdir(layer_root)
                if e.isdigit() and os.path.isdir(layer_root / e)
            )
            if layer_zooms:
                analysis_tiles[layer_name] = {
                    'ready': True,
                    'zooms': layer_zooms,
                    'url_template': f'/api/v1/maps/tiles/maps/{map_id}/analysis/{layer_name}/{{z}}/{{x}}/{{y}}/tile.png',
                }

    return response_base.success(data={
        'has_satellite_tiles': game_map.has_satellite_tiles,
        'tile_min_zoom': game_map.tile_min_zoom,
        'tile_max_zoom': game_map.tile_max_zoom,
        'available_zooms': available_zooms,
        'overview_grid_size': overview_grid_size,
        'tile_url_template': f'/api/v1/maps/tiles/maps/{map_id}/tiles/{{z}}/{{x}}/{{y}}/tile.jpg',
        'tile_dir_exists': os.path.isdir(tile_root),
        'has_military_tiles': has_military and len(military_zooms) > 0,
        'military_zooms': military_zooms,
        'military_grid_size': military_grid_size,
        'military_url_template': f'/api/v1/maps/tiles/maps/{map_id}/military/{{z}}/{{x}}/{{y}}/tile.png',
        'analysis_tiles': analysis_tiles,
    })


@router.get('/{share_code}/replay/map/{map_id}/landmarks', summary='分享回放地标')
async def shared_replay_landmarks(
    db: CurrentSession,
    share_code: Annotated[str, Path(description='分享码')],
    map_id: Annotated[int, Path(description='Map ID')],
    limit: Annotated[int, Query(ge=1, le=5000)] = 2000,
) -> ResponseSchemaModel:
    conv, project = await _resolve_share(db, share_code)
    if project.map_id != map_id:
        raise errors.NotFoundError(msg='地图不匹配')
    items = await landmark_dao.get_by_map(db, map_id, limit=limit)
    data = [GetLandmarkDetail.model_validate(i).model_dump() for i in items]
    return response_base.success(data=data)


@router.get('/{share_code}/replay/map/{map_id}/zones', summary='分享回放区域')
async def shared_replay_zones(
    db: CurrentSession,
    share_code: Annotated[str, Path(description='分享码')],
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    conv, project = await _resolve_share(db, share_code)
    if project.map_id != map_id:
        raise errors.NotFoundError(msg='地图不匹配')
    items = await zone_dao.get_by_map(db, map_id)
    data = [GetZoneDetail.model_validate(i).model_dump() for i in items]
    return response_base.success(data=data)


@router.get('/{share_code}/replay/map/{map_id}/roads', summary='分享回放道路')
async def shared_replay_roads(
    db: CurrentSession,
    share_code: Annotated[str, Path(description='分享码')],
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    conv, project = await _resolve_share(db, share_code)
    if project.map_id != map_id:
        raise errors.NotFoundError(msg='地图不匹配')
    items = await road_dao.get_by_map(db, map_id)
    data = [GetRoadDetail.model_validate(i).model_dump() for i in items]
    return response_base.success(data=data)
