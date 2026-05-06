import json
import math

from fastapi import APIRouter, UploadFile
from sqlalchemy import insert

from backend.utils.timezone import timezone

from backend.app.map.crud.crud_map import (
    entity_dao,
    landmark_dao,
    layer_dao,
    map_dao,
    road_dao,
    zone_dao,
)
from backend.app.map.model.map import MapEntity, MapLandmark, MapRoad, MapZone
from backend.app.map.schema.map import GetMapDetail
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth, DependsSuperUser
from backend.database.db import CurrentSession

router = APIRouter(dependencies=[DependsJwtAuth])

ENTITY_BATCH_SIZE = 5000


def _calc_road_length(points: list[list[float]]) -> float:
    """Calculate 2D road length from [x,z] points."""
    total = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dz = points[i][-1] - points[i - 1][-1]
        total += math.sqrt(dx * dx + dz * dz)
    return round(total, 2)


def _detect_source(body: dict) -> str:
    """Detect data source: 'workbench' (OA_MapExporter) or 'scanner' (OA_MapScanner)."""
    if body.get('tool') == 'OA_MapScanner':
        return 'scanner'
    sv = body.get('scanner_version', '')
    if sv.startswith('WB_'):
        return 'workbench'
    fv = body.get('format_version', '')
    if fv == '2.0':
        return 'scanner'
    return 'workbench'


def _parse_vec3_string(val) -> list[float] | None:
    """Parse '0 10 0' string or [0, 10, 0] list into [float, float, float]."""
    if val is None:
        return None
    if isinstance(val, list):
        return [float(v) for v in val]
    if isinstance(val, str):
        parts = val.strip().split()
        if len(parts) >= 3:
            return [float(p) for p in parts[:3]]
    return None


def _normalize_exporter_body(body: dict) -> dict:
    """Normalize OA_MapExporter flat format into the nested format the import pipeline expects.

    OA_MapExporter outputs: map_name, map_size_x, map_size_z, map_offset_x, map_offset_z, ...
    Backend expects: map: {name, size: [x,z], offset: [x,z], ...}

    Also normalizes: world_bounds from string 'x y z' to array [x,y,z],
    landmarks from {position:[x,y,z]} to {pos:[x,y,z]},
    and moves root-level min_elevation/max_elevation_precise into the map block.
    """
    if 'map' in body and isinstance(body['map'], dict):
        return body

    map_info: dict = {}
    map_info['name'] = body.get('map_name', 'Unknown')
    map_info['size'] = [
        body.get('map_size_x', 0),
        body.get('map_size_z', 0),
    ]
    map_info['offset'] = [
        body.get('map_offset_x', 0),
        body.get('map_offset_z', 0),
    ]
    map_info['max_elevation'] = body.get('max_elevation', 0)
    map_info['min_elevation'] = body.get('min_elevation', 0)
    map_info['max_elevation_precise'] = body.get('max_elevation_precise', 0)
    map_info['terrain_unit_scale'] = body.get('terrain_unit_scale', 1.0)
    map_info['has_ocean'] = body.get('has_ocean', False)
    map_info['ocean_base_height'] = body.get('ocean_base_height', 0)
    map_info['total_entity_count'] = body.get('total_entity_count', 0)

    wb_min = _parse_vec3_string(body.get('world_bounds_min'))
    wb_max = _parse_vec3_string(body.get('world_bounds_max'))
    if wb_min:
        map_info['world_bounds_min'] = wb_min
    if wb_max:
        map_info['world_bounds_max'] = wb_max

    body['map'] = map_info

    landmarks = body.get('landmarks', [])
    for lm in landmarks:
        if 'position' in lm and 'pos' not in lm:
            lm['pos'] = lm.pop('position')

    return body


def _classify_zone(building_count: int) -> str:
    if building_count >= 20:
        return 'urban'
    if building_count >= 8:
        return 'suburban'
    if building_count >= 2:
        return 'rural'
    return 'open_field'


_VEHICLE_FALSE_POSITIVES = frozenset([
    'cardboard', 'carpet', 'caravan', 'carrier', 'cartwheel', 'scarecrow',
    'sacktruck', 'watertank', 'pedalboat', 'vehicleparts', 'signnoentry',
])


def _build_i18n(lm: dict) -> dict | None:
    """Merge name_en/name_zh from Scanner JSON into a single i18n dict."""
    i18n = {}
    if lm.get('name_en'):
        i18n['en'] = lm['name_en']
    if lm.get('name_zh'):
        i18n['zh'] = lm['name_zh']
    return i18n if i18n else None


_BUILDING_NAME_KEYWORDS = frozenset([
    'house', 'apartment', 'residential', 'cottage', 'villa',
    'shop', 'hotel', 'commercial', 'restaurant', 'store', 'market', 'pub',
    'factory', 'warehouse', 'silo', 'mill',
    'church', 'hospital', 'school', 'office', 'municipal',
    'library', 'museum', 'police', 'fire_station', 'fuelstation',
    'barracks', 'armory', 'camp',
    'building', 'barn', 'shed', 'garage', 'farmhouse', 'cowshed',
])
_PROP_KEYWORDS = frozenset([
    'barrel', 'pallet', 'crate', 'cratestack', 'shellcontainer',
    'antenna', 'duckboard', 'concretepanel', 'obstacle',
    'haypile', 'garbagestack', 'marsbox', 'hydrauliccarjack',
    'tabletool', 'tableworkshop', 'generatorportable', 'mobiletank',
    'mobilewatertank', 'palletfuel', 'shelving', 'toolbox',
    'doorstep', 'concretestair', 'brickpile', 'brickwall',
    'cultivatorwreck', 'plowwreck', 'wreck', 'debris',
    'woodpile', 'logpile', 'sandbag', 'concreteslab',
    'doorframe', 'windowframe', 'entryblock', 'entrydirect', 'entryslope',
])


def _classify_entity(prefab_path: str) -> str:
    """Classify an entity by its prefab path into fine-grained categories (~20).

    Categories:
      Vegetation: tree, bush, grass, vegetation
      Rock/Terrain: rock, cliff
      Building: building_residential, building_commercial, building_industrial,
                building_public, building_military, building
      Structure: fence, bridge, fortification, ruin, structure
      Vehicle: vehicle_ground, vehicle_air, vehicle_water
      Other: infrastructure, other
    """
    if not prefab_path:
        return 'other'
    s = prefab_path.lower()

    # --- Vehicles (fine-grained) ---
    if 'prefabs/vehicles/' in s:
        if any(k in s for k in ('helicopter', 'aircraft', 'plane')):
            return 'vehicle_air'
        if any(k in s for k in ('boat', 'ship', 'raft')):
            return 'vehicle_water'
        return 'vehicle_ground'

    if not any(fp in s for fp in _VEHICLE_FALSE_POSITIVES):
        if any(k in s for k in ('helicopter', 'aircraft', 'plane')):
            return 'vehicle_air'
        if 'boat' in s:
            return 'vehicle_water'
        if any(k in s for k in ('vehicle', 'car_', '/car/', 'truck', 'tank', 'apc', 'humvee')):
            return 'vehicle_ground'

    # --- Non-building structures ---
    if 'wreck' in s or 'ruin' in s:
        return 'ruin'
    if 'bridge' in s:
        return 'bridge'
    if any(k in s for k in ('bunker', 'fortification', 'pillbox', 'trench')):
        return 'fortification'
    if any(k in s for k in ('fence', 'wall', 'gate', 'barrier')):
        return 'fence'
    if 'tower' in s:
        return 'fortification'

    # --- Buildings: check BEFORE the generic 'structures/' catch-all.
    #     Arma puts houses/shops/etc under Prefabs/Structures/ so we must
    #     match building keywords first. ---
    s_no_sep = s.replace('_', '').replace('/', '')
    if any(k in s_no_sep for k in _PROP_KEYWORDS):
        return 'other'

    if any(k in s for k in ('house', 'apartment', 'residential', 'cottage', 'villa')):
        return 'building_residential'
    if any(k in s for k in ('shop', 'hotel', 'commercial', 'restaurant', 'store', 'market', 'pub')):
        return 'building_commercial'
    if any(k in s for k in ('factory', 'warehouse', 'silo', 'mill')):
        return 'building_industrial'
    if any(k in s for k in ('church', 'hospital', 'school', 'office', 'station', 'municipal',
                             'library', 'museum', 'police', 'fire_station', 'fuelstation')):
        return 'building_public'
    if any(k in s for k in ('barracks', 'armory', 'military', 'camp', 'hq')):
        return 'building_military'
    if any(k in s for k in ('building', 'barn', 'shed', 'garage', 'farmhouse', 'cowshed')):
        return 'building'

    # --- Generic structure catch-all (things under Prefabs/Structures/ that
    #     didn't match any building keyword above) ---
    if 'prefabs/structures/' in s:
        return 'structure'

    # --- Vegetation (fine-grained) ---
    if any(k in s for k in ('tree', 'bush', 'shrub', 'plant', 'grass', 'flower',
                             'moss', 'ivy', 'fern', 'forest', 'vegetation')):
        if any(k in s for k in ('/trees/', 'tree_', '_tree', '/tree/')):
            return 'tree'
        if any(k in s for k in ('/bushes/', 'bush_', '_bush', '/bush/', 'shrub')):
            return 'bush'
        if any(k in s for k in ('/grass/', 'grass_', '_grass')):
            return 'grass'
        return 'vegetation'

    # --- Rock/Terrain (fine-grained) ---
    if 'cliff' in s:
        return 'cliff'
    if any(k in s for k in ('rock', 'stone', 'boulder', 'mineral')):
        return 'rock'

    # --- Infrastructure ---
    if any(k in s for k in ('road', 'rail', 'power', 'electric', 'pipe', 'pole',
                             'wire', 'light', 'lamp', 'sign', 'bench', 'hydrant')):
        return 'infrastructure'

    return 'other'


@router.post('/maps/import', dependencies=[DependsSuperUser])
async def import_map_file(
    db: CurrentSession,
    file: UploadFile,
) -> ResponseSchemaModel:
    """Import a mapdata.json file via multipart upload.
    Auto-detects source (Workbench / Scanner) and merges intelligently."""
    raw = await file.read()
    try:
        body = json.loads(raw.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise errors.RequestError(msg=f'Invalid JSON file: {e}')

    source = _detect_source(body)
    if source == 'workbench':
        body = _normalize_exporter_body(body)

    map_info = body.get('map', {})
    map_name = map_info.get('name')
    if not map_name:
        raise errors.RequestError(msg='map.name is required in the JSON')

    existing = await map_dao.get_by_name(db, map_name)

    if source == 'scanner' and existing:
        return await _merge_scanner_data(db, existing, body)

    if existing:
        await entity_dao.delete_by_map(db, existing.id)
        await layer_dao.delete_by_map(db, existing.id)
        await landmark_dao.delete_by_map(db, existing.id)
        await road_dao.delete_by_map(db, existing.id)
        await zone_dao.delete_by_map(db, existing.id)
        await map_dao.delete(db, existing.id)
        await db.flush()

    return await _full_import(db, body, map_info, source)


async def _full_import(db, body: dict, map_info: dict, source: str) -> ResponseSchemaModel:
    """Full import: create map + all data."""
    map_name = map_info['name']
    size = map_info.get('size', [0, 0])
    offset = map_info.get('offset', [0, 0])

    hg = body.get('height_grid')
    hg_kwargs = {}
    if hg:
        hg_kwargs = {
            'height_grid_resolution': hg.get('resolution'),
            'height_grid_rows': hg.get('rows'),
            'height_grid_cols': hg.get('cols'),
            'height_grid_data': hg.get('data'),
        }

    wg = body.get('water_grid')
    wg_kwargs = {}
    if wg:
        wg_kwargs = {
            'water_grid_resolution': wg.get('resolution'),
            'water_grid_rows': wg.get('rows'),
            'water_grid_cols': wg.get('cols'),
            'water_grid_data': wg.get('data'),
        }

    game_map = await map_dao.create(
        db,
        name=map_name,
        size_x=size[0] if len(size) > 0 else 0,
        size_z=size[1] if len(size) > 1 else 0,
        max_elevation=map_info.get('max_elevation', 0),
        offset_x=offset[0] if len(offset) > 0 else 0,
        offset_z=offset[1] if len(offset) > 1 else 0,
        description=map_info.get('description'),
        source=source,
        min_elevation=map_info.get('min_elevation', body.get('min_elevation', 0)),
        max_elevation_precise=map_info.get('max_elevation_precise', body.get('max_elevation_precise', 0)),
        terrain_unit_scale=map_info.get('terrain_unit_scale', 1.0),
        has_ocean=map_info.get('has_ocean', False),
        ocean_base_height=map_info.get('ocean_base_height', 0),
        world_bounds_min=_parse_vec3_string(map_info.get('world_bounds_min')),
        world_bounds_max=_parse_vec3_string(map_info.get('world_bounds_max')),
        total_entity_count=map_info.get('total_entity_count', 0),
        format_version=body.get('format_version', ''),
        scanner_version=body.get('scanner_version', ''),
        scan_date=body.get('scan_date', ''),
        status='draft',
        **hg_kwargs,
        **wg_kwargs,
    )

    image_info = map_info.get('image')
    if image_info:
        await layer_dao.create(
            db,
            map_id=game_map.id,
            name=f'{map_name} satellite',
            layer_type='satellite',
            image_path=image_info.get('path'),
            image_width_px=image_info.get('width_px'),
            image_height_px=image_info.get('height_px'),
            bound_left=0,
            bound_bottom=0,
            bound_right=size[0] if len(size) > 0 else 0,
            bound_top=size[1] if len(size) > 1 else 0,
        )

    await _import_landmarks(db, game_map.id, body.get('landmarks', []))
    await _import_roads(db, game_map.id, body.get('roads', []))

    zones = body.get('zones', [])
    if zones:
        zone_models = []
        for z in zones:
            zone_models.append(MapZone(
                map_id=game_map.id,
                name=z.get('name', ''),
                type=z.get('type', 'unknown'),
                center_x=z.get('center_x', 0),
                center_z=z.get('center_z', 0),
                radius=z.get('radius', 500),
                building_count=z.get('building_count', 0),
                tree_count=z.get('tree_count', 0),
                rock_count=z.get('rock_count', 0),
                structure_count=z.get('structure_count', 0),
                vehicle_count=z.get('vehicle_count', 0),
                infrastructure_count=z.get('infrastructure_count', 0),
                other_count=z.get('other_count', 0),
                total_entities=z.get('total_entities', 0),
                boundary=z.get('boundary'),
                tactical_notes=z.get('tactical_notes'),
            ))
        await zone_dao.bulk_create(db, zone_models)

    await db.commit()
    await db.refresh(game_map)

    return response_base.success(data=GetMapDetail.model_validate(game_map).model_dump())


async def _merge_scanner_data(db, existing_map, body: dict) -> ResponseSchemaModel:
    """Merge Scanner data into existing map: only import landmarks + roads (skip entities)."""
    map_id = existing_map.id
    merged_landmarks = 0
    merged_roads = 0

    landmarks = body.get('landmarks', [])
    if landmarks:
        await landmark_dao.delete_by_map(db, map_id)
        await _import_landmarks(db, map_id, landmarks)
        merged_landmarks = len(landmarks)

    roads = body.get('roads', [])
    if roads:
        await road_dao.delete_by_map(db, map_id)
        await _import_roads(db, map_id, roads)
        merged_roads = len(roads)

    await db.commit()

    return response_base.success(data={
        'mode': 'merge',
        'map_id': map_id,
        'map_name': existing_map.name,
        'landmarks_imported': merged_landmarks,
        'roads_imported': merged_roads,
        'entities_skipped': True,
        'message': f'Scanner data merged: {merged_landmarks} landmarks, {merged_roads} roads. '
                   'Entities/terrain/water from Workbench data preserved.',
    })


async def _import_landmarks(db, map_id: int, landmarks: list[dict]):
    if not landmarks:
        return
    landmark_models = []
    for lm in landmarks:
        pos = lm.get('pos', [0, 0, 0])
        landmark_models.append(MapLandmark(
            map_id=map_id,
            name=lm.get('name', ''),
            type=lm.get('type', 'unknown'),
            descriptor_type_raw=lm.get('descriptor_type_raw'),
            position_x=pos[0] if len(pos) > 0 else 0,
            position_y=pos[1] if len(pos) > 1 else 0,
            position_z=pos[2] if len(pos) > 2 else 0,
            faction_index=lm.get('faction_index', 0),
            info_text=lm.get('info_text'),
            group_type=lm.get('group_type'),
            image_def=lm.get('image_def'),
            base_type=lm.get('base_type'),
            angle=lm.get('angle', 0),
            range=lm.get('range', 0),
            priority=lm.get('priority', 0),
            links=lm.get('links'),
            name_raw=lm.get('name_raw'),
            name_i18n=_build_i18n(lm),
        ))
    await landmark_dao.bulk_create(db, landmark_models)


def _normalize_road_points(pts: list[list[float]]) -> list[list[float]]:
    """Normalize 3D [x,y,z] road points to 2D [x,z] for consistent storage."""
    normalized = []
    for p in pts:
        if len(p) >= 3:
            normalized.append([p[0], p[2]])
        elif len(p) >= 2:
            normalized.append([p[0], p[1]])
        else:
            continue
    return normalized


async def _import_roads(db, map_id: int, roads: list[dict]):
    if not roads:
        return
    road_models = []
    for r in roads:
        pts = _normalize_road_points(r.get('points', []))
        road_models.append(MapRoad(
            map_id=map_id,
            name=r.get('name'),
            type=r.get('type', 'road'),
            width=r.get('width', 4.0),
            points=pts,
            length=r.get('length') or _calc_road_length(pts),
        ))
    await road_dao.bulk_create(db, road_models)


def _parse_chunk_entities(text: str, map_id: int, fallback_chunk_name: str) -> tuple[str, list[dict]]:
    """Parse a JSONL chunk file into a list of raw dicts for bulk INSERT."""
    lines = text.strip().split('\n')
    if not lines:
        return fallback_chunk_name, []

    chunk_name = fallback_chunk_name
    try:
        header = json.loads(lines[0])
        chunk_name = header.get('chunk', fallback_chunk_name)
    except json.JSONDecodeError:
        pass

    rows: list[dict] = []
    for line in lines[1:]:
        line = line.strip()
        if not line or not line.startswith('{'):
            continue
        try:
            ent = json.loads(line)
        except json.JSONDecodeError:
            continue

        is_wb = 'pfb' in ent or 'cat' in ent
        if is_wb:
            pos = ent.get('pos', [0, 0, 0])
            sz = ent.get('sz', [0, 0, 0])
            pfb = ent.get('pfb', '')
            category = ent.get('cat') or _classify_entity(pfb)
            rows.append({
                'map_id': map_id,
                'category': category,
                'position_x': pos[0] if len(pos) > 0 else 0,
                'position_y': pos[1] if len(pos) > 1 else 0,
                'position_z': pos[2] if len(pos) > 2 else 0,
                'size_x': sz[0] if len(sz) > 0 else 0,
                'size_y': sz[1] if len(sz) > 1 else 0,
                'size_z': sz[2] if len(sz) > 2 else 0,
                'rotation': ent.get('rot', 0),
                'corners': ent.get('corners'),
                'name': ent.get('n'),
                'prefab_path': pfb,
                'chunk_name': chunk_name,
                'source': 'workbench',
            })
        else:
            pos = ent.get('p', [0, 0, 0])
            sz = ent.get('s', [0, 0, 0])
            pf = ent.get('pf', '')
            category = ent.get('c') or _classify_entity(pf)
            rows.append({
                'map_id': map_id,
                'category': category,
                'position_x': pos[0] if len(pos) > 0 else 0,
                'position_y': pos[1] if len(pos) > 1 else 0,
                'position_z': pos[2] if len(pos) > 2 else 0,
                'size_x': sz[0] if len(sz) > 0 else 0,
                'size_y': sz[1] if len(sz) > 1 else 0,
                'size_z': sz[2] if len(sz) > 2 else 0,
                'rotation': ent.get('rot', 0),
                'corners': ent.get('corners'),
                'name': ent.get('n'),
                'prefab_path': pf,
                'chunk_name': chunk_name,
                'source': 'scanner',
            })

    return chunk_name, rows


@router.post('/maps/{map_id}/import-chunks', dependencies=[DependsSuperUser])
async def import_entity_chunks(
    db: CurrentSession,
    map_id: int,
    files: list[UploadFile],
) -> ResponseSchemaModel:
    """Import entity chunk JSONL files for an existing map.
    Each file is a chunk with header line + entity detail lines.
    Auto-detects source format (Exporter uses 'cat'/'pfb'/'pos'/'sz'/'n', Scanner uses 'c'/'p'/'s'/'pf').
    Zone analysis is no longer done at export time; use the /zones/recalculate endpoint instead.

    Optimized: reads all files first, then bulk-inserts using Core INSERT (bypasses ORM overhead)."""
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.RequestError(msg=f'Map {map_id} not found')

    all_rows: list[dict] = []
    total_chunks = 0
    now = timezone.now()

    for upload_file in files:
        raw = await upload_file.read()
        text = raw.decode('utf-8', errors='replace')
        _, rows = _parse_chunk_entities(text, map_id, upload_file.filename or f'chunk_{total_chunks}')
        all_rows.extend(rows)
        total_chunks += 1

    for row in all_rows:
        row['created_time'] = now

    total_entities = len(all_rows)
    for i in range(0, total_entities, ENTITY_BATCH_SIZE):
        batch = all_rows[i:i + ENTITY_BATCH_SIZE]
        await db.execute(insert(MapEntity), batch)

    await db.commit()

    return response_base.success(data={
        'map_id': map_id,
        'chunks_imported': total_chunks,
        'entities_imported': total_entities,
    })
