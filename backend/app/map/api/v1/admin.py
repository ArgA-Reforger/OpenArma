import asyncio
import math
from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.map.crud.crud_map import (
    entity_dao,
    landmark_dao,
    layer_dao,
    map_dao,
    road_dao,
    zone_dao,
)
from backend.app.map.schema.map import (
    CreateLayerParam,
    CreateLandmarkParam,
    CreateMapManualParam,
    CreateRoadParam,
    CreateZoneParam,
    GetEntityDetail,
    GetLandmarkDetail,
    GetLayerDetail,
    GetMapDetail,
    GetMapSummary,
    GetRoadDetail,
    GetZoneDetail,
    UpdateLandmarkParam,
    UpdateLayerParam,
    UpdateMapParam,
    UpdateZoneParam,
)
from backend.app.map.service.coordinates import (
    LayerGeometry,
    MapGeometry,
    format_mgrs,
    grid_resolution,
    pixel_to_world,
    world_to_mgrs,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth, DependsSuperUser
from backend.database.db import CurrentSession

router = APIRouter(dependencies=[DependsJwtAuth])


@router.get('/maps')
async def list_maps(
    db: CurrentSession,
    status: Annotated[str | None, Query(description='Filter by status')] = None,
    source: Annotated[str | None, Query(description='Filter by source: manual/scanner/import')] = None,
) -> ResponseSchemaModel:
    maps = await map_dao.get_list(db, status=status, source=source)
    data = [GetMapSummary.model_validate(m).model_dump() for m in maps]
    return response_base.success(data=data)


@router.post('/maps/create', dependencies=[DependsSuperUser])
async def create_map_manual(
    db: CurrentSession,
    obj: CreateMapManualParam,
) -> ResponseSchemaModel:
    """Create a map manually (no Scanner data required)."""
    existing = await map_dao.get_by_name(db, obj.name)
    if existing:
        raise errors.RequestError(msg=f'Map "{obj.name}" already exists')

    game_map = await map_dao.create(
        db,
        name=obj.name,
        size_x=obj.size_x,
        size_z=obj.size_z,
        max_elevation=obj.max_elevation,
        offset_x=obj.offset_x,
        offset_z=obj.offset_z,
        description=obj.description,
        source='manual',
        status='draft',
    )
    await db.commit()
    await db.refresh(game_map)
    return response_base.success(data=GetMapDetail.model_validate(game_map).model_dump())


@router.get('/maps/{map_id}')
async def get_map(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')
    return response_base.success(data=GetMapDetail.model_validate(game_map).model_dump())


@router.put('/maps/{map_id}', dependencies=[DependsSuperUser])
async def update_map(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    obj: UpdateMapParam,
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')
    await map_dao.update(db, map_id, obj)
    await db.commit()
    updated = await map_dao.get(db, map_id)
    return response_base.success(data=GetMapDetail.model_validate(updated).model_dump())


@router.delete('/maps/{map_id}', dependencies=[DependsSuperUser])
async def delete_map(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')
    await entity_dao.delete_by_map(db, map_id)
    await layer_dao.delete_by_map(db, map_id)
    await landmark_dao.delete_by_map(db, map_id)
    await road_dao.delete_by_map(db, map_id)
    await zone_dao.delete_by_map(db, map_id)
    await map_dao.delete(db, map_id)
    await db.commit()
    return response_base.success()


@router.get('/maps/{map_id}/landmarks')
async def list_landmarks(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    type_filter: Annotated[str | None, Query(alias='type', description='Filter by landmark type')] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ResponseSchemaModel:
    items = await landmark_dao.get_by_map(db, map_id, type_filter=type_filter, limit=limit, offset=offset)
    data = [GetLandmarkDetail.model_validate(i).model_dump() for i in items]
    return response_base.success(data=data)


@router.put('/maps/{map_id}/landmarks/{landmark_id}', dependencies=[DependsSuperUser])
async def update_landmark(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    landmark_id: Annotated[int, Path(description='Landmark ID')],
    obj: UpdateLandmarkParam,
) -> ResponseSchemaModel:
    item = await landmark_dao.get(db, landmark_id)
    if not item or item.map_id != map_id:
        raise errors.NotFoundError(msg='Landmark not found')
    await landmark_dao.update(db, landmark_id, obj)
    await db.commit()
    updated = await landmark_dao.get(db, landmark_id)
    return response_base.success(data=GetLandmarkDetail.model_validate(updated).model_dump())


@router.get('/maps/{map_id}/entities')
async def list_entities(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    category: Annotated[str | None, Query(description='Filter by category: building/tree/rock/structure/vehicle/infrastructure/other')] = None,
    chunk: Annotated[str | None, Query(description='Filter by chunk name')] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ResponseSchemaModel:
    items = await entity_dao.get_by_map(db, map_id, category=category, chunk_name=chunk, limit=limit, offset=offset)
    data = [GetEntityDetail.model_validate(i).model_dump() for i in items]
    return response_base.success(data=data)


@router.get('/maps/{map_id}/entities/count')
async def count_entities(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    count = await entity_dao.count_by_map(db, map_id)
    return response_base.success(data={'count': count})


@router.get('/maps/{map_id}/roads')
async def list_roads(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    items = await road_dao.get_by_map(db, map_id)
    data = [GetRoadDetail.model_validate(i).model_dump() for i in items]
    return response_base.success(data=data)


@router.get('/maps/{map_id}/zones')
async def list_zones(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    items = await zone_dao.get_by_map(db, map_id)
    data = [GetZoneDetail.model_validate(i).model_dump() for i in items]
    return response_base.success(data=data)


@router.put('/maps/{map_id}/zones/{zone_id}', dependencies=[DependsSuperUser])
async def update_zone(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    zone_id: Annotated[int, Path(description='Zone ID')],
    obj: UpdateZoneParam,
) -> ResponseSchemaModel:
    items = await zone_dao.get_by_map(db, map_id)
    item = next((z for z in items if z.id == zone_id), None)
    if not item:
        raise errors.NotFoundError(msg='Zone not found')
    await zone_dao.update(db, zone_id, obj)
    await db.commit()
    updated_items = await zone_dao.get_by_map(db, map_id)
    updated = next((z for z in updated_items if z.id == zone_id), None)
    return response_base.success(data=GetZoneDetail.model_validate(updated).model_dump())


# ---------------------------------------------------------------------------
# Manual annotation endpoints (MAP-09 ~ MAP-12)
# ---------------------------------------------------------------------------

def _calc_road_length(points: list[list[float]]) -> float:
    """Calculate 2D road length from [x,z] points."""
    total = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dz = points[i][-1] - points[i - 1][-1]
        total += math.sqrt(dx * dx + dz * dz)
    return round(total, 2)


@router.post('/maps/{map_id}/landmarks', dependencies=[DependsSuperUser])
async def create_landmark(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    obj: CreateLandmarkParam,
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')
    item = await landmark_dao.create_single(db, map_id, obj)
    await db.commit()
    await db.refresh(item)
    return response_base.success(data=GetLandmarkDetail.model_validate(item).model_dump())


@router.delete('/maps/{map_id}/landmarks/{landmark_id}', dependencies=[DependsSuperUser])
async def delete_landmark(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    landmark_id: Annotated[int, Path(description='Landmark ID')],
) -> ResponseSchemaModel:
    item = await landmark_dao.get(db, landmark_id)
    if not item or item.map_id != map_id:
        raise errors.NotFoundError(msg='Landmark not found')
    await landmark_dao.delete_single(db, landmark_id)
    await db.commit()
    return response_base.success()


@router.post('/maps/{map_id}/roads', dependencies=[DependsSuperUser])
async def create_road(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    obj: CreateRoadParam,
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')
    length = _calc_road_length(obj.points)
    item = await road_dao.create_single(db, map_id, obj, length=length)
    await db.commit()
    await db.refresh(item)
    return response_base.success(data=GetRoadDetail.model_validate(item).model_dump())


@router.delete('/maps/{map_id}/roads/{road_id}', dependencies=[DependsSuperUser])
async def delete_road(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    road_id: Annotated[int, Path(description='Road ID')],
) -> ResponseSchemaModel:
    roads = await road_dao.get_by_map(db, map_id)
    item = next((r for r in roads if r.id == road_id), None)
    if not item:
        raise errors.NotFoundError(msg='Road not found')
    await road_dao.delete_single(db, road_id)
    await db.commit()
    return response_base.success()


@router.post('/maps/{map_id}/zones', dependencies=[DependsSuperUser])
async def create_zone(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    obj: CreateZoneParam,
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')
    item = await zone_dao.create_single(db, map_id, obj)
    await db.commit()
    await db.refresh(item)
    return response_base.success(data=GetZoneDetail.model_validate(item).model_dump())


@router.delete('/maps/{map_id}/zones/{zone_id}', dependencies=[DependsSuperUser])
async def delete_zone(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    zone_id: Annotated[int, Path(description='Zone ID')],
) -> ResponseSchemaModel:
    zones = await zone_dao.get_by_map(db, map_id)
    item = next((z for z in zones if z.id == zone_id), None)
    if not item:
        raise errors.NotFoundError(msg='Zone not found')
    await zone_dao.delete_single(db, zone_id)
    await db.commit()
    return response_base.success()


@router.get('/maps/{map_id}/coordinate')
async def convert_coordinate(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    digits: Annotated[int, Query(description='MGRS digit precision 4/6/8/10')] = 6,
    layer_id: Annotated[int | None, Query(description='Layer ID for pixel conversions')] = None,
    pixel_x: Annotated[float | None, Query(description='Pixel X on layer image')] = None,
    pixel_y: Annotated[float | None, Query(description='Pixel Y on layer image')] = None,
    world_x: Annotated[float | None, Query(description='World X in meters')] = None,
    world_z: Annotated[float | None, Query(description='World Z in meters')] = None,
) -> ResponseSchemaModel:
    """Convert between pixel, world, and MGRS coordinate systems."""
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')

    if digits not in (4, 6, 8, 10):
        raise errors.RequestError(msg='digits must be 4, 6, 8, or 10')

    geo = MapGeometry(
        size_x=game_map.size_x,
        size_z=game_map.size_z,
        offset_x=game_map.offset_x,
        offset_z=game_map.offset_z,
    )

    result: dict = {'grid_digits': digits, 'grid_resolution_m': round(grid_resolution(geo.size_x, digits), 2)}

    if pixel_x is not None and pixel_y is not None:
        if not layer_id:
            raise errors.RequestError(msg='layer_id is required for pixel conversions')
        layer = await layer_dao.get(db, layer_id)
        if not layer or layer.map_id != map_id:
            raise errors.NotFoundError(msg='Layer not found')
        if not layer.image_width_px or not layer.image_height_px:
            raise errors.RequestError(msg='Layer has no image dimensions; upload an image first')
        lg = LayerGeometry(
            image_width_px=layer.image_width_px,
            image_height_px=layer.image_height_px,
            bound_left=layer.bound_left,
            bound_bottom=layer.bound_bottom,
            bound_right=layer.bound_right,
            bound_top=layer.bound_top,
        )
        wx, wz = pixel_to_world(lg, pixel_x, pixel_y)
        e, n = world_to_mgrs(geo, wx, wz, digits)
        result.update({
            'pixel': [pixel_x, pixel_y],
            'world': [round(wx, 2), round(wz, 2)],
            'mgrs': [e, n],
            'mgrs_formatted': format_mgrs(e, n, digits),
        })
    elif world_x is not None and world_z is not None:
        e, n = world_to_mgrs(geo, world_x, world_z, digits)
        result.update({
            'world': [world_x, world_z],
            'mgrs': [e, n],
            'mgrs_formatted': format_mgrs(e, n, digits),
        })
    else:
        raise errors.RequestError(msg='Provide either (pixel_x, pixel_y) or (world_x, world_z)')

    return response_base.success(data=result)


# ---------------------------------------------------------------------------
# Layer CRUD endpoints
# ---------------------------------------------------------------------------


@router.get('/maps/{map_id}/layers')
async def list_layers(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')
    items = await layer_dao.get_by_map(db, map_id)
    data = [GetLayerDetail.model_validate(i).model_dump() for i in items]
    return response_base.success(data=data)


@router.post('/maps/{map_id}/layers', dependencies=[DependsSuperUser])
async def create_layer(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    obj: CreateLayerParam,
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')
    layer = await layer_dao.create(
        db,
        map_id=map_id,
        name=obj.name,
        layer_type=obj.layer_type,
        bound_left=obj.bound_left,
        bound_bottom=obj.bound_bottom,
        bound_right=obj.bound_right,
        bound_top=obj.bound_top,
        z_index=obj.z_index,
        opacity=obj.opacity,
        visible=obj.visible,
    )
    await db.commit()
    await db.refresh(layer)
    return response_base.success(data=GetLayerDetail.model_validate(layer).model_dump())


@router.put('/maps/{map_id}/layers/{layer_id}', dependencies=[DependsSuperUser])
async def update_layer(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    layer_id: Annotated[int, Path(description='Layer ID')],
    obj: UpdateLayerParam,
) -> ResponseSchemaModel:
    layer = await layer_dao.get(db, layer_id)
    if not layer or layer.map_id != map_id:
        raise errors.NotFoundError(msg='Layer not found')
    await layer_dao.update(db, layer_id, obj)
    await db.commit()
    updated = await layer_dao.get(db, layer_id)
    return response_base.success(data=GetLayerDetail.model_validate(updated).model_dump())


@router.delete('/maps/{map_id}/layers/{layer_id}', dependencies=[DependsSuperUser])
async def delete_layer(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    layer_id: Annotated[int, Path(description='Layer ID')],
) -> ResponseSchemaModel:
    layer = await layer_dao.get(db, layer_id)
    if not layer or layer.map_id != map_id:
        raise errors.NotFoundError(msg='Layer not found')
    await layer_dao.delete(db, layer_id)
    await db.commit()
    return response_base.success()


async def _resolve_embedding_kwargs(
    db: AsyncSession, provider_id: int | None = None,
) -> tuple[dict | None, str | None, int | None]:
    """Resolve embedding API credentials.

    If *provider_id* is given, look up that specific provider.
    Otherwise fall back to any active openai/openai_compatible provider.
    Returns (kwargs_dict, provider_type, rpm_limit) or (None, None, None).
    """
    from backend.app.llm.model import LLMProvider as LlmProvider
    from backend.app.llm.service.llm_provider_service import _decrypt_api_key

    if provider_id:
        provider = await db.get(LlmProvider, provider_id)
    else:
        embedding_capable = ('openai', 'openai_compatible')
        stmt = (
            select(LlmProvider)
            .where(LlmProvider.is_active.is_(True), LlmProvider.provider_type.in_(embedding_capable))
            .limit(1)
        )
        result = await db.execute(stmt)
        provider = result.scalar_one_or_none()

    if not provider or not provider.api_key_encrypted:
        return None, None, None
    key = _decrypt_api_key(provider.api_key_encrypted)
    if not key:
        return None, None, None
    rpm = getattr(provider, 'rpm_limit', None)
    return {'api_key': key, 'api_base': provider.api_base}, provider.provider_type, rpm


@router.post('/maps/{map_id}/generate-hex-cells', summary='Generate H3 hex terrain cells for a map', dependencies=[DependsSuperUser])
async def generate_hex_cells_for_map(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    provider_id: Annotated[int | None, Query(description='LLM Provider ID for embedding')] = None,
    model_name: Annotated[str | None, Query(description='Embedding model name')] = None,
    batch_size: Annotated[int, Query(description='Embedding batch size per request', ge=1, le=100)] = 20,
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')

    embedding_kwargs, provider_type, rpm_limit = await _resolve_embedding_kwargs(db, provider_id)

    emb_model = model_name or 'text-embedding-3-small'
    if provider_type and provider_type != 'openai':
        emb_model = f'openai/{emb_model}'

    asyncio.create_task(_run_hex_cell_generation(
        map_id, emb_model, embedding_kwargs, rpm_limit, batch_size,
    ))

    return response_base.success(data={
        'map_id': map_id,
        'status': 'started',
        'message': 'Hex cell generation started in background',
    })


async def _run_hex_cell_generation(
    map_id: int,
    emb_model: str,
    embedding_kwargs: dict | None,
    rpm_limit: int | None,
    batch_size: int,
) -> None:
    from backend.app.map.service.hex_terrain import generate_hex_cells
    from backend.app.map.service.tile_progress import clear_progress
    from backend.common.log import log
    from backend.database.db import async_db_session

    try:
        async with async_db_session() as db:
            game_map = await map_dao.get(db, map_id)
            if not game_map:
                log.error('Hex cell gen: map %s not found', map_id)
                return

            count = await generate_hex_cells(
                db, game_map, embedding_model=emb_model, embedding_kwargs=embedding_kwargs,
                rpm_limit=rpm_limit, batch_size=batch_size,
            )
            await db.commit()
            log.info('Hex cell gen complete: map=%s, cells=%d', map_id, count)
    except Exception:
        log.exception('Hex cell gen failed for map %s', map_id)
    finally:
        clear_progress(map_id, 'hex_cells')


@router.post('/test-embedding-batch', summary='Test if an embedding provider supports a given batch size', dependencies=[DependsSuperUser])
async def test_embedding_batch(
    db: CurrentSession,
    provider_id: Annotated[int, Query(description='LLM Provider ID')],
    model_name: Annotated[str, Query(description='Embedding model name')],
    batch_size: Annotated[int, Query(description='Batch size to test', ge=1, le=100)] = 20,
) -> ResponseSchemaModel:
    embedding_kwargs, provider_type, _ = await _resolve_embedding_kwargs(db, provider_id)
    if not embedding_kwargs:
        raise errors.RequestError(msg='Provider not found or has no API key')

    emb_model = model_name
    if provider_type and provider_type != 'openai':
        emb_model = f'openai/{emb_model}'

    test_texts = [
        f'Test terrain description for batch validation sentence {i}. '
        'This area contains mixed vegetation with moderate slopes.'
        for i in range(batch_size)
    ]

    import time
    import litellm

    start = time.monotonic()
    try:
        response = await litellm.aembedding(
            model=emb_model,
            input=test_texts,
            **embedding_kwargs,
        )
        elapsed = round(time.monotonic() - start, 2)
        dims = len(response.data[0]['embedding']) if response.data else 0
        return response_base.success(data={
            'success': True,
            'batch_size': batch_size,
            'embeddings_returned': len(response.data),
            'dimensions': dims,
            'elapsed_seconds': elapsed,
        })
    except Exception as exc:
        elapsed = round(time.monotonic() - start, 2)
        return response_base.success(data={
            'success': False,
            'batch_size': batch_size,
            'error': str(exc)[:300],
            'elapsed_seconds': elapsed,
        })


@router.post('/maps/{map_id}/generate-military-tiles', summary='Generate military-style base map tiles', dependencies=[DependsSuperUser])
async def generate_military_tiles_for_map(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')

    asyncio.create_task(_run_military_tile_generation(map_id))

    return response_base.success(data={
        'map_id': map_id,
        'status': 'started',
        'message': 'Military tile generation started in background',
    })


async def _run_military_tile_generation(map_id: int) -> None:
    from backend.app.map.service.military_renderer import generate_military_tiles
    from backend.app.map.service.tile_progress import clear_progress
    from backend.common.log import log
    from backend.core.path_conf import UPLOAD_DIR
    from backend.database.db import async_db_session

    try:
        async with async_db_session() as db:
            game_map = await map_dao.get(db, map_id)
            if not game_map:
                log.error('Military tile gen: map %s not found', map_id)
                return

            result = await generate_military_tiles(db, game_map, str(UPLOAD_DIR / 'maps'))

            terrain_stats = result.get('terrain_stats', {})
            if terrain_stats:
                existing_cache = game_map.stats_cache or {}
                existing_cache.update(terrain_stats)
                game_map.stats_cache = existing_cache
                await db.commit()

            log.info('Military tile gen complete: map=%s, tiles=%d', map_id, result['total_tiles'])
    except Exception:
        log.exception('Military tile gen failed for map %s', map_id)
    finally:
        clear_progress(map_id, 'military')


@router.post('/maps/{map_id}/generate-analysis-tiles/{layer}', summary='Generate analysis layer tiles', dependencies=[DependsSuperUser])
async def generate_analysis_tiles_for_map(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    layer: Annotated[str, Path(description='Layer name: vegetation/builtup/slope/hillshade/contours/water/trafficability/cover/mcoo')],
) -> ResponseSchemaModel:
    from backend.app.map.service.analysis_tile_renderer import LAYER_GENERATORS

    if layer not in LAYER_GENERATORS:
        raise errors.RequestError(msg=f'Unknown layer: {layer}. Valid: {", ".join(LAYER_GENERATORS)}')

    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')

    asyncio.create_task(_run_analysis_tile_generation(map_id, layer))

    return response_base.success(data={
        'map_id': map_id,
        'layer': layer,
        'status': 'started',
        'message': f'Analysis tile generation ({layer}) started in background',
    })


async def _run_analysis_tile_generation(map_id: int, layer: str) -> None:
    from backend.app.map.service.analysis_tile_renderer import LAYER_GENERATORS, LAYERS_NEED_DB
    from backend.app.map.service.tile_progress import clear_progress
    from backend.common.log import log
    from backend.core.path_conf import UPLOAD_DIR
    from backend.database.db import async_db_session

    try:
        async with async_db_session() as db:
            game_map = await map_dao.get(db, map_id)
            if not game_map:
                log.error('Analysis tile gen: map %s not found', map_id)
                return

            gen_fn = LAYER_GENERATORS[layer]
            out_dir = str(UPLOAD_DIR / 'maps')

            if layer in LAYERS_NEED_DB:
                await gen_fn(db, game_map, out_dir)
            else:
                await gen_fn(game_map, out_dir)

            log.info('Analysis tile gen complete: map=%s, layer=%s', map_id, layer)
    except Exception:
        log.exception('Analysis tile gen failed: map=%s, layer=%s', map_id, layer)
    finally:
        clear_progress(map_id, layer)


@router.get('/maps/{map_id}/tile-gen-progress', summary='Get tile generation progress')
async def get_tile_generation_progress(
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    from backend.app.map.service.tile_progress import get_all_progress
    progress = await get_all_progress(map_id)
    return response_base.success(data=progress)


@router.get('/maps/{map_id}/stats', summary='Get map statistics')
async def get_map_stats(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    from backend.app.map.model.map import HexCell, MapEntity, MapLandmark, MapRoad, MapZone

    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')

    cache = game_map.stats_cache or {}

    landmark_count = (await db.execute(
        select(func.count()).where(MapLandmark.map_id == map_id)
    )).scalar() or 0

    road_agg = (await db.execute(
        select(func.count(), func.coalesce(func.sum(MapRoad.length), 0))
        .where(MapRoad.map_id == map_id)
    )).one()
    road_count = road_agg[0] or 0
    road_total_length_m = float(road_agg[1] or 0)

    zone_count = (await db.execute(
        select(func.count()).where(MapZone.map_id == map_id)
    )).scalar() or 0

    category_rows = (await db.execute(
        select(MapEntity.category, func.count())
        .where(MapEntity.map_id == map_id)
        .group_by(MapEntity.category)
    )).all()
    entity_by_category: dict[str, int] = {cat: cnt for cat, cnt in category_rows}
    total_entities = sum(entity_by_category.values())

    vegetation_cats = {'tree', 'bush', 'grass', 'vegetation'}
    building_cats = {'building', 'building_residential', 'building_commercial',
                     'building_industrial', 'building_public', 'building_military'}
    vegetation_count = sum(entity_by_category.get(c, 0) for c in vegetation_cats)
    building_count = sum(entity_by_category.get(c, 0) for c in building_cats)

    hex_count = (await db.execute(
        select(func.count()).where(HexCell.map_id == map_id)
    )).scalar() or 0

    terrain_distribution: dict[str, int] = {}
    cover_distribution: dict[str, int] = {}
    trafficability_distribution: dict[str, int] = {}
    avg_slope = 0.0
    max_slope_global = 0.0
    vegetation_coverage_pct = 0.0
    urban_coverage_pct = 0.0

    if hex_count > 0:
        terrain_rows = (await db.execute(
            select(HexCell.terrain_type, func.count())
            .where(HexCell.map_id == map_id)
            .group_by(HexCell.terrain_type)
        )).all()
        terrain_distribution = {t: c for t, c in terrain_rows}

        water_cells = terrain_distribution.get('water', 0)
        land_cells = hex_count - water_cells

        if land_cells > 0:
            veg_types = {'forest', 'forested_slope', 'forest_floor'}
            veg_cells = sum(terrain_distribution.get(t, 0) for t in veg_types)
            vegetation_coverage_pct = round(100.0 * veg_cells / land_cells, 1)

            urban_types = {'urban', 'suburban'}
            urban_cells = sum(terrain_distribution.get(t, 0) for t in urban_types)
            urban_coverage_pct = round(100.0 * urban_cells / land_cells, 1)

        land_filter = HexCell.terrain_type != 'water'

        cover_rows = (await db.execute(
            select(HexCell.cover_rating, func.count())
            .where(HexCell.map_id == map_id, land_filter)
            .group_by(HexCell.cover_rating)
        )).all()
        cover_distribution = {t: c for t, c in cover_rows}

        traf_rows = (await db.execute(
            select(HexCell.trafficability, func.count())
            .where(HexCell.map_id == map_id, land_filter)
            .group_by(HexCell.trafficability)
        )).all()
        trafficability_distribution = {t: c for t, c in traf_rows}

        slope_agg = (await db.execute(
            select(func.avg(HexCell.max_slope), func.max(HexCell.max_slope))
            .where(HexCell.map_id == map_id, land_filter)
        )).one()
        avg_slope = round(float(slope_agg[0] or 0), 1)
        max_slope_global = round(float(slope_agg[1] or 0), 1)

    elev_min = cache.get('elev_p2', game_map.min_elevation or 0)
    elev_max = cache.get('elev_p98', game_map.max_elevation_precise or game_map.max_elevation or 0)

    ocean_pct = cache.get('ocean_percent', 0.0)
    if ocean_pct == 0.0 and game_map.has_ocean and 'ocean_percent' not in cache:
        height_grid_raw = game_map.height_grid_data
        if height_grid_raw:
            import numpy as np
            if isinstance(height_grid_raw, dict) and 'grid' in height_grid_raw:
                height_grid_raw = height_grid_raw['grid']
            height_np = np.array(height_grid_raw, dtype=np.float32)
            height_res = game_map.height_grid_resolution or 100
            from backend.app.map.service.military_renderer import _build_ocean_mask, _compute_adaptive_breaks
            ocean_mask = _build_ocean_mask(height_np, height_res, game_map.size_x, game_map.size_z)
            ocean_pct = round(100.0 * float(ocean_mask.sum()) / max(ocean_mask.size, 1), 1)
            breaks = _compute_adaptive_breaks(height_np, ocean_mask)
            elev_min = round(float(breaks[0]), 1)
            elev_max = round(float(breaks[-1]), 1)
            cache.update({'ocean_percent': ocean_pct, 'elev_p2': elev_min, 'elev_p98': elev_max})
            game_map.stats_cache = cache
            await db.commit()

    map_area_km2 = (game_map.size_x * game_map.size_z) / 1_000_000
    land_area_km2 = round(map_area_km2 * (1 - ocean_pct / 100), 2)
    road_total_km = round(road_total_length_m / 1000, 1)
    road_density = round(road_total_km / land_area_km2, 1) if land_area_km2 > 0 else 0.0

    return response_base.success(data={
        'map_name': game_map.name,
        'size_x': game_map.size_x,
        'size_z': game_map.size_z,
        'area_km2': round(map_area_km2, 2),
        'land_area_km2': land_area_km2,
        'elevation_min': elev_min,
        'elevation_max': elev_max,
        'has_ocean': game_map.has_ocean,
        'ocean_percent': ocean_pct,
        'avg_slope': avg_slope,
        'max_slope': max_slope_global,
        'total_entities': total_entities,
        'vegetation_count': vegetation_count,
        'vegetation_coverage_pct': vegetation_coverage_pct,
        'urban_coverage_pct': urban_coverage_pct,
        'building_count': building_count,
        'landmark_count': landmark_count,
        'road_count': road_count,
        'road_total_km': road_total_km,
        'road_density_km_per_km2': road_density,
        'zone_count': zone_count,
        'hex_cell_count': hex_count,
        'terrain_distribution': terrain_distribution,
        'cover_distribution': cover_distribution,
        'trafficability_distribution': trafficability_distribution,
        'entity_by_category': entity_by_category,
    })
