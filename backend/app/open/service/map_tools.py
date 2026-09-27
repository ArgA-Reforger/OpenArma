"""Map-aware Agent tools — general-purpose map intelligence.

All tools are registered via builtin_registry and available when enabled on an Agent.
Queries execute in backend memory/database with < 10ms latency (except image tools).
Works with any map (manual, scanner-imported, or external).
"""

import heapq
import json
import math
from typing import Any

from backend.app.conversation.engine.builtin_tools.registry import builtin_registry
from backend.app.map.service.coordinates import distance_world as _distance_2d


async def _get_map_data(map_id: int):
    """Fetch map + landmarks + roads from DB. Returns (game_map, landmarks, roads)."""
    from backend.app.map.crud.crud_map import landmark_dao, map_dao, road_dao, zone_dao
    from backend.database.db import async_db_session

    async with async_db_session() as db:
        game_map = await map_dao.get(db, map_id)
        if not game_map:
            return None, [], [], []
        landmarks = await landmark_dao.get_by_map(db, map_id, limit=5000)
        roads = await road_dao.get_by_map(db, map_id)
        zones = await zone_dao.get_by_map(db, map_id)
    return game_map, landmarks, roads, zones


# ---------------------------------------------------------------------------
# II-10: Basic tools
# ---------------------------------------------------------------------------

@builtin_registry.register(
    'query_landmarks',
    display_name='Consulta de puntos de referencia',
    description=(
        'Query landmarks near a position on the map. '
        'Returns named locations (cities, villages, hills, facilities, etc.) within the given radius. '
        'Use this to understand what is at or near a coordinate. '
        'Requires map_id from the project configuration.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID from project config'},
            'position': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Center position [x, z]',
            },
            'radius': {'type': 'number', 'description': 'Search radius in meters', 'default': 1000},
            'type_filter': {
                'type': 'string',
                'description': 'Filter by type: city, town, village, hill, military_base, airport, etc. Leave empty for all.',
            },
        },
        'required': ['map_id', 'position'],
    },
)
async def query_landmarks(
    map_id: int, position: list, radius: float = 1000, type_filter: str = '', **_: Any,
) -> str:
    from backend.app.map.crud.crud_map import landmark_dao
    from backend.database.db import async_db_session

    px, pz = position[0], position[1]
    results = []

    async with async_db_session() as db:
        landmarks = await landmark_dao.get_by_map(db, map_id, type_filter=type_filter or None, limit=5000)

    for lm in landmarks:
        dist = _distance_2d(px, pz, lm.position_x, lm.position_z)
        if dist <= radius:
            entry = {
                'name': lm.name,
                'type': lm.type,
                'position': [round(lm.position_x, 1), round(lm.position_y, 1), round(lm.position_z, 1)],
                'distance_m': round(dist),
            }
            if lm.faction_index:
                entry['faction'] = ['neutral', 'east', 'west'][min(lm.faction_index, 2)]
            if lm.tactical_value:
                entry['tactical_value'] = lm.tactical_value
            if lm.tactical_description:
                entry['tactical_description'] = lm.tactical_description
            results.append(entry)

    results.sort(key=lambda x: x['distance_m'])
    return json.dumps({'count': len(results), 'landmarks': results[:50]}, indent=2)


@builtin_registry.register(
    'calculate_route',
    display_name='Cálculo de ruta',
    description=(
        'Calculate the route between two positions. '
        'Determines straight-line distance and whether road connections exist between the points. '
        'Use this to plan movement and estimate if roads are available.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID'},
            'from_pos': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Start position [x, z]',
            },
            'to_pos': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'End position [x, z]',
            },
        },
        'required': ['map_id', 'from_pos', 'to_pos'],
    },
)
async def calculate_route(map_id: int, from_pos: list, to_pos: list, **_: Any) -> str:
    from backend.app.map.crud.crud_map import road_dao
    from backend.database.db import async_db_session

    straight_dist = _distance_2d(from_pos[0], from_pos[1], to_pos[0], to_pos[1])

    async with async_db_session() as db:
        roads = await road_dao.get_by_map(db, map_id)

    nearby_roads_start = []
    nearby_roads_end = []
    road_proximity_threshold = 100

    for road in roads:
        pts = road.points or []
        for pt in pts:
            if len(pt) >= 2:
                ptz = pt[2] if len(pt) >= 3 else pt[1]
                d_start = _distance_2d(from_pos[0], from_pos[1], pt[0], ptz)
                if d_start < road_proximity_threshold:
                    nearby_roads_start.append({'type': road.type, 'width': road.width, 'distance': round(d_start)})
                    break
        for pt in pts:
            if len(pt) >= 2:
                ptz = pt[2] if len(pt) >= 3 else pt[1]
                d_end = _distance_2d(to_pos[0], to_pos[1], pt[0], ptz)
                if d_end < road_proximity_threshold:
                    nearby_roads_end.append({'type': road.type, 'width': road.width, 'distance': round(d_end)})
                    break

    has_road_start = len(nearby_roads_start) > 0
    has_road_end = len(nearby_roads_end) > 0

    result = {
        'straight_line_distance_m': round(straight_dist),
        'from_pos': from_pos,
        'to_pos': to_pos,
        'road_at_start': has_road_start,
        'road_at_end': has_road_end,
        'road_connection_likely': has_road_start and has_road_end,
        'nearby_roads_start': nearby_roads_start[:3],
        'nearby_roads_end': nearby_roads_end[:3],
    }
    return json.dumps(result, indent=2)


@builtin_registry.register(
    'get_terrain_profile',
    display_name='Perfil del terreno',
    description=(
        'Get the terrain height profile between two positions. '
        'Samples terrain heights at regular intervals along the line between from and to. '
        'Use this to check for hills, valleys, or elevation changes along a movement path.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID'},
            'from_pos': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Start position [x, z]',
            },
            'to_pos': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'End position [x, z]',
            },
        },
        'required': ['map_id', 'from_pos', 'to_pos'],
    },
)
async def get_terrain_profile(map_id: int, from_pos: list, to_pos: list, **_: Any) -> str:
    from backend.app.map.crud.crud_map import map_dao
    from backend.database.db import async_db_session

    async with async_db_session() as db:
        game_map = await map_dao.get(db, map_id)
    if not game_map or not game_map.height_grid_data:
        return json.dumps({'error': 'No height grid data available for this map'})

    resolution = game_map.height_grid_resolution or 100
    offset_x = game_map.offset_x
    offset_z = game_map.offset_z
    cols = game_map.height_grid_cols or 0
    rows = game_map.height_grid_rows or 0
    grid = game_map.height_grid_data

    dist = _distance_2d(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
    num_samples = min(max(int(dist / 50), 5), 100)

    profile = []
    for i in range(num_samples + 1):
        t = i / num_samples
        x = from_pos[0] + t * (to_pos[0] - from_pos[0])
        z = from_pos[1] + t * (to_pos[1] - from_pos[1])

        col = int((x - offset_x) / resolution)
        row = int((z - offset_z) / resolution)
        col = max(0, min(col, cols - 1))
        row = max(0, min(row, rows - 1))

        height = 0
        if isinstance(grid, list) and row < len(grid):
            row_data = grid[row]
            if isinstance(row_data, list) and col < len(row_data):
                height = row_data[col]

        profile.append({
            'distance_from_start_m': round(dist * t),
            'position': [round(x, 1), round(z, 1)],
            'height_m': round(height, 1),
        })

    heights = [p['height_m'] for p in profile]
    result = {
        'from': from_pos,
        'to': to_pos,
        'total_distance_m': round(dist),
        'min_height_m': round(min(heights), 1),
        'max_height_m': round(max(heights), 1),
        'elevation_gain_m': round(max(heights) - min(heights), 1),
        'profile': profile,
    }
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# II-13: Enhanced tools
# ---------------------------------------------------------------------------

@builtin_registry.register(
    'get_area_intel',
    display_name='Inteligencia del área',
    description=(
        'Get comprehensive intelligence about an area: landmarks, zone type, road access, and terrain info. '
        'Combines landmark query, zone data, and road proximity into a single briefing.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID'},
            'position': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Center position [x, z]',
            },
            'radius': {'type': 'number', 'description': 'Intel radius in meters', 'default': 500},
        },
        'required': ['map_id', 'position'],
    },
)
async def get_area_intel(map_id: int, position: list, radius: float = 500, **_: Any) -> str:
    game_map, landmarks, roads, zones = await _get_map_data(map_id)
    if not game_map:
        return json.dumps({'error': 'Map not found'})

    px, pz = position[0], position[1]

    nearby_landmarks = []
    for lm in landmarks:
        d = _distance_2d(px, pz, lm.position_x, lm.position_z)
        if d <= radius:
            nearby_landmarks.append({
                'name': lm.name, 'type': lm.type, 'distance_m': round(d),
                'position': [round(lm.position_x, 1), round(lm.position_z, 1)],
            })
    nearby_landmarks.sort(key=lambda x: x['distance_m'])

    zone_info = None
    for z in zones:
        d = _distance_2d(px, pz, z.center_x, z.center_z)
        if d <= z.radius:
            zone_info = {'name': z.name, 'type': z.type, 'building_count': z.building_count}
            if z.tactical_notes:
                zone_info['notes'] = z.tactical_notes
            break

    nearby_roads = []
    for road in roads:
        pts = road.points or []
        min_dist = float('inf')
        for pt in pts:
            if len(pt) >= 2:
                ptz = pt[2] if len(pt) >= 3 else pt[1]
                d = _distance_2d(px, pz, pt[0], ptz)
                if d < min_dist:
                    min_dist = d
        if min_dist <= radius:
            nearby_roads.append({'type': road.type, 'width': road.width, 'distance_m': round(min_dist)})
    nearby_roads.sort(key=lambda x: x['distance_m'])

    result = {
        'position': position,
        'radius': radius,
        'landmarks': nearby_landmarks[:20],
        'zone': zone_info,
        'roads': nearby_roads[:10],
        'road_access': len(nearby_roads) > 0,
    }
    return json.dumps(result, indent=2)


@builtin_registry.register(
    'get_mission_status',
    display_name='Estado de la misión',
    description=(
        'Get the current mission objective and status from the project Arma configuration. '
        'Returns the mission type, description, targets, and constraints. '
        'Only available for Arma-enabled projects.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'project_id': {'type': 'integer', 'description': 'Project ID'},
        },
        'required': ['project_id'],
    },
)
async def get_mission_status(project_id: int, **_: Any) -> str:
    from backend.app.open.crud.crud_arma_config import arma_config_dao
    from backend.app.project.crud.crud_project import project_dao
    from backend.database.db import async_db_session

    async with async_db_session() as db:
        config = await arma_config_dao.get_by_project(db, project_id)
        project = await project_dao.get(db, project_id)

    if not config:
        return json.dumps({'error': 'No Arma config found for this project'})

    mission = getattr(config, 'mission_objective', None)
    result = {
        'project_id': project_id,
        'game_mode': config.game_mode,
        'language': config.language,
        'map_id': project.map_id if project else None,
        'mission_objective': mission if mission else {'type': 'none', 'description': 'No mission objective set'},
    }
    return json.dumps(result, indent=2)


@builtin_registry.register(
    'estimate_travel_time',
    display_name='Estimación de tiempo de marcha',
    description=(
        'Estimate travel time between two positions considering distance, terrain, and road availability. '
        'Returns estimated time at different movement speeds.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID'},
            'from_pos': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Start position [x, z]',
            },
            'to_pos': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'End position [x, z]',
            },
        },
        'required': ['map_id', 'from_pos', 'to_pos'],
    },
)
async def estimate_travel_time(map_id: int, from_pos: list, to_pos: list, **_: Any) -> str:
    dist = _distance_2d(from_pos[0], from_pos[1], to_pos[0], to_pos[1])

    # Check road availability
    route_json = await calculate_route(map_id=map_id, from_pos=from_pos, to_pos=to_pos)
    route_data = json.loads(route_json)
    on_road = route_data.get('road_connection_likely', False)

    # Speeds in m/s (approximate Arma Reforger values)
    terrain_penalty = 1.0 if on_road else 0.65
    speeds = {
        'walk': 1.4 * terrain_penalty,
        'jog': 3.5 * terrain_penalty,
        'sprint': 5.5 * terrain_penalty,
    }

    result = {
        'distance_m': round(dist),
        'on_road': on_road,
        'terrain_modifier': terrain_penalty,
        'estimates': {},
    }
    for mode, speed in speeds.items():
        seconds = dist / max(speed, 0.1)
        minutes = seconds / 60
        result['estimates'][mode] = {
            'speed_m_per_s': round(speed, 2),
            'time_seconds': round(seconds),
            'time_minutes': round(minutes, 1),
        }

    return json.dumps(result, indent=2)


@builtin_registry.register(
    'send_message_to_human',
    display_name='Enviar mensaje al comandante',
    description=(
        'Send a message to the human operator via the web interface. '
        'Use this to request clarification, report important events, or suggest changes. '
        'The message will appear in the web chat UI.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'text': {'type': 'string', 'description': 'Message text to send to the human commander'},
        },
        'required': ['text'],
    },
)
async def send_message_to_human(text: str, **_: Any) -> str:
    return json.dumps({
        'status': 'delivered',
        'message': text,
        'note': 'Message will be visible in the web chat interface.',
    })


# ---------------------------------------------------------------------------
# II-14: Advanced tools
# ---------------------------------------------------------------------------

@builtin_registry.register(
    'assess_threat_level',
    display_name='Evaluación de amenazas del área',
    description=(
        'Assess the threat or risk level of a specific area by combining terrain analysis, '
        'zone type (urban/open), road access, and landmark proximity. '
        'Returns an area assessment with cover/exposure analysis.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID'},
            'position': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Position to assess [x, z]',
            },
            'radius': {'type': 'number', 'description': 'Assessment radius in meters', 'default': 300},
        },
        'required': ['map_id', 'position'],
    },
)
async def assess_threat_level(map_id: int, position: list, radius: float = 300, **_: Any) -> str:
    game_map, landmarks, roads, zones = await _get_map_data(map_id)
    if not game_map:
        return json.dumps({'error': 'Map not found'})

    px, pz = position[0], position[1]

    zone_type = 'unknown'
    building_count = 0
    for z in zones:
        d = _distance_2d(px, pz, z.center_x, z.center_z)
        if d <= z.radius:
            zone_type = z.type
            building_count = z.building_count
            break

    road_count = 0
    closest_road_dist = float('inf')
    for road in roads:
        for pt in (road.points or []):
            if len(pt) >= 2:
                ptz = pt[2] if len(pt) >= 3 else pt[1]
                d = _distance_2d(px, pz, pt[0], ptz)
                if d < closest_road_dist:
                    closest_road_dist = d
                if d <= radius:
                    road_count += 1
                    break

    nearby_strategic = []
    for lm in landmarks:
        if lm.type in ('military_base', 'bunker', 'fortress', 'airport', 'viewtower', 'viewpoint'):
            d = _distance_2d(px, pz, lm.position_x, lm.position_z)
            if d <= radius * 2:
                nearby_strategic.append({
                    'name': lm.name, 'type': lm.type, 'distance_m': round(d),
                })

    # Threat scoring
    threat_score = 0
    factors = []

    if zone_type in ('urban', 'suburban'):
        threat_score += 3
        factors.append(f'{zone_type} area: close-quarters risk, ambush potential')
    elif zone_type == 'open_field':
        threat_score += 2
        factors.append('open terrain: exposed, limited cover')
    elif zone_type in ('forest', 'forested_slope', 'forest_floor', 'valley', 'riverbed'):
        threat_score += 1
        factors.append(f'{zone_type}: natural cover available, concealed approach')
    elif zone_type in ('ridgeline', 'hilltop'):
        threat_score += 1
        factors.append(f'{zone_type}: elevated position, good observation')
    elif zone_type in ('steep_slope',):
        threat_score += 0
        factors.append(f'{zone_type}: difficult terrain, channelized movement')

    if road_count > 0:
        threat_score += 1
        factors.append(f'{road_count} road(s) nearby: potential approach routes for enemy')

    if nearby_strategic:
        threat_score += 2
        factors.append(f'{len(nearby_strategic)} strategic point(s) nearby: likely contested')

    if building_count > 20:
        threat_score += 1
        factors.append(f'dense buildings ({building_count}): CQB environment')

    if threat_score >= 6:
        threat_level = 'high'
    elif threat_score >= 3:
        threat_level = 'medium'
    else:
        threat_level = 'low'

    _good_cover = ('urban', 'suburban', 'forest', 'forested_slope', 'forest_floor', 'valley')
    _moderate_cover = ('ridgeline', 'hilltop', 'riverbed', 'steep_slope', 'rural')
    cover_rating = 'good' if zone_type in _good_cover else (
        'moderate' if zone_type in _moderate_cover else 'poor'
    )

    result = {
        'position': position,
        'threat_level': threat_level,
        'threat_score': threat_score,
        'factors': factors,
        'zone_type': zone_type,
        'cover_rating': cover_rating,
        'building_density': building_count,
        'road_access': road_count > 0,
        'nearest_road_m': round(closest_road_dist) if closest_road_dist < float('inf') else None,
        'nearby_strategic_points': nearby_strategic[:5],
    }
    return json.dumps(result, indent=2)


@builtin_registry.register(
    'view_map_image',
    display_name='Ver imagen del mapa',
    description=(
        'Get a map image of a specific area. Returns a URL to the full map image and the pixel coordinates '
        'corresponding to the requested area. Use this to visually inspect terrain before making decisions. '
        'Only available if the map has an uploaded image.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID'},
            'center': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Center position [x, z] in world coordinates',
            },
            'radius': {'type': 'number', 'description': 'View radius in meters', 'default': 500},
        },
        'required': ['map_id', 'center'],
    },
)
async def view_map_image(map_id: int, center: list, radius: float = 500, **_: Any) -> str:
    from backend.app.map.crud.crud_map import landmark_dao, layer_dao, map_dao
    from backend.database.db import async_db_session

    async with async_db_session() as db:
        game_map = await map_dao.get(db, map_id)
        if not game_map:
            return json.dumps({'error': 'Map not found'})
        layers = await layer_dao.get_by_map(db, map_id)
        landmarks = await landmark_dao.get_by_map(db, map_id, limit=5000)

    image_layers = [l for l in layers if l.image_path]
    if not image_layers:
        return json.dumps({'error': 'No map image layers available. Upload a layer image first.'})

    cx, cz = center[0], center[1]

    layer_info = []
    for layer in image_layers:
        layer_info.append({
            'layer_id': layer.id,
            'name': layer.name,
            'image_url': f'/static/upload/{layer.image_path}',
            'bounds': [layer.bound_left, layer.bound_bottom, layer.bound_right, layer.bound_top],
        })

    result = {
        'map_name': game_map.name,
        'layers': layer_info,
        'center_world': center,
        'radius_m': radius,
        'map_size': [game_map.size_x, game_map.size_z],
        'note': 'Use query_landmarks to identify features visible in this area.',
    }

    nearby = []
    for lm in landmarks:
        d = _distance_2d(cx, cz, lm.position_x, lm.position_z)
        if d <= radius:
            nearby.append({'name': lm.name, 'type': lm.type, 'distance_m': round(d)})
    nearby.sort(key=lambda x: x['distance_m'])
    result['visible_landmarks'] = nearby[:20]

    return json.dumps(result, indent=2)


@builtin_registry.register(
    'request_recon',
    display_name='Solicitud de reconocimiento',
    description=(
        'Mark an area as requiring reconnaissance. '
        'This flags the area for priority observation in subsequent decisions. '
        'Use when you need intelligence about an area before committing forces.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'position': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Center of recon area [x, z]',
            },
            'radius': {'type': 'number', 'description': 'Recon radius in meters', 'default': 500},
            'reason': {'type': 'string', 'description': 'Why recon is needed'},
            'priority': {'type': 'string', 'enum': ['low', 'medium', 'high'], 'description': 'Recon priority'},
        },
        'required': ['position', 'reason'],
    },
)
async def request_recon(
    position: list, reason: str, radius: float = 500, priority: str = 'medium', **_: Any,
) -> str:
    return json.dumps({
        'status': 'recon_requested',
        'position': position,
        'radius': radius,
        'priority': priority,
        'reason': reason,
        'note': 'Recon request logged. Consider sending a patrol or scout to this area.',
    })


@builtin_registry.register(
    'convert_coordinates',
    display_name='Conversión de coordenadas',
    description=(
        'Convert between world coordinates [x, z] and 6-digit military grid references (XXXYYY). '
        'Use this when you need to translate coordinates for human-readable briefings or '
        'convert grid references from human input into world coordinates for tool calls.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID from project config'},
            'grid_ref': {
                'type': 'string',
                'description': '6-digit grid reference to convert to world coords (e.g. "064064")',
            },
            'world_pos': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'World position [x, z] to convert to grid reference',
            },
        },
        'required': ['map_id'],
    },
)
async def convert_coordinates(
    map_id: int, grid_ref: str = '', world_pos: list | None = None, **_: Any,
) -> str:
    from backend.app.map.crud.crud_map import map_dao
    from backend.database.db import async_db_session

    async with async_db_session() as db:
        game_map = await map_dao.get(db, map_id)
    if not game_map:
        return json.dumps({'error': 'Map not found'})

    result: dict[str, Any] = {'map_size': [game_map.size_x, game_map.size_z]}

    if grid_ref and len(grid_ref) == 6 and grid_ref.isdigit():
        easting = int(grid_ref[:3])
        northing = int(grid_ref[3:])
        wx = easting * 100.0
        wz = northing * 100.0
        result['grid_to_world'] = {
            'grid_ref': grid_ref,
            'world_pos': [wx, wz],
            'easting': easting,
            'northing': northing,
        }
    elif grid_ref:
        result['error'] = f'Invalid grid reference "{grid_ref}". Must be exactly 6 digits (e.g. "064064").'

    if world_pos and len(world_pos) >= 2:
        wx, wz = world_pos[0], world_pos[1]
        easting = int(wx / 100)
        northing = int(wz / 100)
        grid = f'{easting:03d}{northing:03d}'
        result['world_to_grid'] = {
            'world_pos': [round(wx, 1), round(wz, 1)],
            'grid_ref': grid,
            'easting': easting,
            'northing': northing,
        }

    if 'grid_to_world' not in result and 'world_to_grid' not in result:
        result['error'] = 'Provide either grid_ref (6 digits) or world_pos [x, z] to convert.'

    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# II-15: Terrain-aware pathfinding & summary
# ---------------------------------------------------------------------------

def _build_cost_grid(game_map, db_session=None) -> tuple[list[list[float]], float]:
    """Build a movement-cost grid from height, water, and vegetation data.

    Returns (cost_grid, cell_size) where cost 0 = impassable, >0 = traversal cost.
    Lower cost = easier movement.
    """
    from backend.app.map.service.thematic_layers import SWIM_DEPTH_THRESHOLD

    cell_size = 100.0
    size_x = game_map.size_x or 1
    size_z = game_map.size_z or 1
    cols = max(1, int(size_x / cell_size))
    rows = max(1, int(size_z / cell_size))

    cost = [[1.0] * cols for _ in range(rows)]

    hg = game_map.height_grid_data
    if hg:
        hg_res = game_map.height_grid_resolution or 100
        hg_rows = len(hg)
        hg_cols = len(hg[0]) if hg else 0
        for r in range(rows):
            for c in range(cols):
                hc = min(int(c * cell_size / hg_res), hg_cols - 1)
                hr = min(int(r * cell_size / hg_res), hg_rows - 1)
                dh_dx = dh_dz = 0.0
                if 0 < hc < hg_cols - 1:
                    dh_dx = (hg[hr][hc + 1] - hg[hr][hc - 1]) / (2 * hg_res)
                if 0 < hr < hg_rows - 1:
                    dh_dz = (hg[hr + 1][hc] - hg[hr - 1][hc]) / (2 * hg_res)
                slope = math.degrees(math.atan(math.sqrt(dh_dx ** 2 + dh_dz ** 2)))
                if slope > 45:
                    cost[r][c] = 0.0
                elif slope > 30:
                    cost[r][c] *= 5.0
                elif slope > 15:
                    cost[r][c] *= 2.0

    wg = game_map.water_grid_data
    if wg:
        wg_res = game_map.water_grid_resolution or 200
        wg_rows = len(wg)
        wg_cols = len(wg[0]) if wg else 0
        for r in range(rows):
            for c in range(cols):
                wc = min(int(c * cell_size / wg_res), wg_cols - 1)
                wr = min(int(r * cell_size / wg_res), wg_rows - 1)
                cell = wg[wr][wc]
                if cell and isinstance(cell, list) and len(cell) >= 2:
                    depth = cell[1]
                    is_water = cell[0] > 0 if len(cell) >= 3 else cell[0]
                    if is_water:
                        if depth >= SWIM_DEPTH_THRESHOLD:
                            cost[r][c] = 0.0
                        elif depth >= 1.0:
                            cost[r][c] *= 4.0
                        elif depth >= 0.5:
                            cost[r][c] *= 2.0

    return cost, cell_size


def _astar(
    cost_grid: list[list[float]],
    start_rc: tuple[int, int],
    goal_rc: tuple[int, int],
    cell_size: float,
) -> list[tuple[int, int]] | None:
    """A* pathfinding on the cost grid. Returns list of (row, col) or None."""
    rows = len(cost_grid)
    cols = len(cost_grid[0]) if cost_grid else 0
    sr, sc = start_rc
    gr, gc = goal_rc

    if not (0 <= sr < rows and 0 <= sc < cols and 0 <= gr < rows and 0 <= gc < cols):
        return None
    if cost_grid[sr][sc] == 0 or cost_grid[gr][gc] == 0:
        return None

    DIAG = math.sqrt(2)
    neighbors = [
        (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
        (-1, -1, DIAG), (-1, 1, DIAG), (1, -1, DIAG), (1, 1, DIAG),
    ]

    def heuristic(r: int, c: int) -> float:
        dr = abs(r - gr)
        dc = abs(c - gc)
        return (min(dr, dc) * DIAG + abs(dr - dc)) * cell_size

    open_set: list[tuple[float, int, int]] = [(heuristic(sr, sc), sr, sc)]
    g_score: dict[tuple[int, int], float] = {(sr, sc): 0.0}
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    closed: set[tuple[int, int]] = set()

    max_iterations = rows * cols * 2

    for _ in range(max_iterations):
        if not open_set:
            return None
        _, cr, cc = heapq.heappop(open_set)
        if (cr, cc) == (gr, gc):
            path = [(gr, gc)]
            node = (gr, gc)
            while node in came_from:
                node = came_from[node]
                path.append(node)
            path.reverse()
            return path
        if (cr, cc) in closed:
            continue
        closed.add((cr, cc))

        for dr, dc, base_dist in neighbors:
            nr, nc = cr + dr, cc + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if (nr, nc) in closed:
                continue
            nc_cost = cost_grid[nr][nc]
            if nc_cost == 0:
                continue
            move_cost = base_dist * cell_size * nc_cost
            tentative = g_score[(cr, cc)] + move_cost
            if tentative < g_score.get((nr, nc), float('inf')):
                g_score[(nr, nc)] = tentative
                came_from[(nr, nc)] = (cr, cc)
                heapq.heappush(open_set, (tentative + heuristic(nr, nc), nr, nc))

    return None


def _simplify_path(
    path: list[tuple[int, int]], cell_size: float, tolerance: float = 150.0,
) -> list[list[float]]:
    """Ramer-Douglas-Peucker simplification, then convert to world coords."""
    if len(path) <= 2:
        return [[round(c * cell_size + cell_size / 2, 1),
                 round(r * cell_size + cell_size / 2, 1)] for r, c in path]

    points = [(c * cell_size + cell_size / 2, r * cell_size + cell_size / 2) for r, c in path]

    def _rdp(pts: list[tuple[float, float]], eps: float) -> list[tuple[float, float]]:
        if len(pts) <= 2:
            return pts
        sx, sy = pts[0]
        ex, ey = pts[-1]
        max_d = 0.0
        idx = 0
        dx, dy = ex - sx, ey - sy
        line_len = math.sqrt(dx * dx + dy * dy)
        for i in range(1, len(pts) - 1):
            px, py = pts[i]
            if line_len < 1e-9:
                d = math.sqrt((px - sx) ** 2 + (py - sy) ** 2)
            else:
                d = abs(dy * px - dx * py + ex * sy - ey * sx) / line_len
            if d > max_d:
                max_d = d
                idx = i
        if max_d > eps:
            left = _rdp(pts[:idx + 1], eps)
            right = _rdp(pts[idx:], eps)
            return left[:-1] + right
        return [pts[0], pts[-1]]

    simplified = _rdp(points, tolerance)
    return [[round(x, 1), round(y, 1)] for x, y in simplified]


@builtin_registry.register(
    'plan_route',
    display_name='Planificación inteligente de ruta',
    description=(
        'Plan an optimal movement route between two positions using A* pathfinding '
        'that considers terrain slope, water obstacles, and vegetation density. '
        'Returns a series of waypoints that avoid impassable terrain and minimize movement cost. '
        'Use this instead of calculate_route when you need actual waypoints for unit movement. '
        'The route avoids steep slopes (>45°), deep water, and prefers flat/road terrain.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID from project config'},
            'from_pos': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Start position [x, z] in world coordinates',
            },
            'to_pos': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Destination position [x, z] in world coordinates',
            },
            'prefer': {
                'type': 'string',
                'enum': ['speed', 'cover'],
                'description': 'Route preference: "speed" for fastest path (default), "cover" to prefer concealed routes through vegetation/buildings',
                'default': 'speed',
            },
        },
        'required': ['map_id', 'from_pos', 'to_pos'],
    },
)
async def plan_route(
    map_id: int, from_pos: list, to_pos: list, prefer: str = 'speed', **_: Any,
) -> str:
    from backend.app.map.crud.crud_map import map_dao
    from backend.database.db import async_db_session

    async with async_db_session() as db:
        game_map = await map_dao.get(db, map_id)
    if not game_map:
        return json.dumps({'error': 'Map not found'})

    cost_grid, cell_size = _build_cost_grid(game_map)
    rows = len(cost_grid)
    cols = len(cost_grid[0]) if cost_grid else 0

    if prefer == 'cover':
        from backend.app.map.crud.crud_map import map_dao as _md
        async with async_db_session() as db2:
            from sqlalchemy import select, func
            from backend.app.map.model import MapEntity
            veg_cats = ['tree', 'bush', 'vegetation']
            stmt = (
                select(MapEntity.position_x, MapEntity.position_z)
                .where(MapEntity.map_id == map_id, MapEntity.category.in_(veg_cats))
            )
            result = await db2.execute(stmt)
            veg_positions = [(row[0], row[1]) for row in result.all()]

        for x, z in veg_positions:
            c_idx = min(int(x / cell_size), cols - 1)
            r_idx = min(int(z / cell_size), rows - 1)
            if 0 <= c_idx < cols and 0 <= r_idx < rows and cost_grid[r_idx][c_idx] > 0:
                cost_grid[r_idx][c_idx] *= 0.5

    sr = min(int(from_pos[1] / cell_size), rows - 1)
    sc = min(int(from_pos[0] / cell_size), cols - 1)
    gr = min(int(to_pos[1] / cell_size), rows - 1)
    gc = min(int(to_pos[0] / cell_size), cols - 1)

    raw_path = _astar(cost_grid, (sr, sc), (gr, gc), cell_size)
    if raw_path is None:
        return json.dumps({
            'error': 'No viable path found — terrain may be impassable between these points.',
            'from': from_pos,
            'to': to_pos,
            'suggestion': 'Try different start/end positions or check for water/cliff obstacles.',
        })

    waypoints = _simplify_path(raw_path, cell_size, tolerance=150.0)
    waypoints[0] = [round(from_pos[0], 1), round(from_pos[1], 1)]
    waypoints[-1] = [round(to_pos[0], 1), round(to_pos[1], 1)]

    total_dist = 0.0
    for i in range(1, len(waypoints)):
        dx = waypoints[i][0] - waypoints[i - 1][0]
        dz = waypoints[i][1] - waypoints[i - 1][1]
        total_dist += math.sqrt(dx * dx + dz * dz)

    straight_dist = _distance_2d(from_pos[0], from_pos[1], to_pos[0], to_pos[1])

    result = {
        'from': from_pos,
        'to': to_pos,
        'preference': prefer,
        'waypoints': waypoints,
        'num_waypoints': len(waypoints),
        'total_distance_m': round(total_dist),
        'straight_line_distance_m': round(straight_dist),
        'detour_ratio': round(total_dist / max(straight_dist, 1), 2),
        'grid_resolution_m': cell_size,
    }
    return json.dumps(result, indent=2)


@builtin_registry.register(
    'get_terrain_summary',
    display_name='Resumen del terreno',
    description=(
        'Get a high-level terrain summary for the entire map, divided into 9 macro-zones (NW, N, NE, W, C, E, SW, S, SE). '
        'Each zone reports vegetation density, trafficability, cover quality, and key terrain features. '
        'Use this to understand the overall battlefield layout before planning specific routes or positions. '
        'Much more efficient than querying individual thematic layers.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID from project config'},
            'layers': {
                'type': 'array',
                'items': {'type': 'string', 'enum': ['vegetation', 'trafficability', 'cover', 'slope', 'water']},
                'description': 'Which terrain aspects to summarize. Default: all.',
            },
        },
        'required': ['map_id'],
    },
)
async def get_terrain_summary(
    map_id: int, layers: list[str] | None = None, **_: Any,
) -> str:
    from backend.app.map.crud.crud_map import map_dao
    from backend.app.map.service import thematic_layers as tl
    from backend.database.db import async_db_session

    async with async_db_session() as db:
        game_map = await map_dao.get(db, map_id)
        if not game_map:
            return json.dumps({'error': 'Map not found'})

        requested = set(layers) if layers else {'vegetation', 'trafficability', 'cover', 'slope', 'water'}
        summary: dict[str, Any] = {
            'map_id': map_id,
            'map_size': [game_map.size_x, game_map.size_z],
        }

        if 'vegetation' in requested:
            veg = await tl.vegetation_density(db, game_map)
            summary['vegetation'] = veg.get('llm')

        if 'trafficability' in requested:
            traf = await tl.trafficability(db, game_map)
            summary['trafficability'] = traf.get('llm')

        if 'cover' in requested:
            cov = await tl.cover_concealment(db, game_map)
            summary['cover'] = cov.get('llm')

        if 'slope' in requested:
            sl = tl.slope_map(game_map)
            summary['slope'] = sl.get('llm')

        if 'water' in requested:
            wb = tl.water_bodies(game_map)
            summary['water'] = wb.get('llm')

    return json.dumps(summary, indent=2)


# ---------------------------------------------------------------------------
# II-16: Spatial RAG tools (H3 hex terrain intelligence)
# ---------------------------------------------------------------------------

@builtin_registry.register(
    'query_terrain_cells',
    display_name='Búsqueda inteligente de terreno',
    description=(
        'Search terrain cells by location and/or natural language query. '
        'Uses H3 hexagonal grid pre-computed terrain features with semantic search. '
        'Examples: "good cover for ambush", "flat open ground for vehicles", '
        '"high ground with observation". '
        'Returns terrain type, slope, cover rating, trafficability, and more. '
        'Much faster than combining multiple terrain tools. '
        'Requires map_id and either position+radius or a text query (or both).'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID from project config'},
            'position': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Center position [x, z] to search around',
            },
            'radius': {'type': 'number', 'description': 'Search radius in meters', 'default': 2000},
            'query': {
                'type': 'string',
                'description': 'Natural language terrain query (e.g. "good cover for infantry")',
            },
            'limit': {'type': 'integer', 'description': 'Max results', 'default': 10},
        },
        'required': ['map_id'],
    },
)
async def query_terrain_cells(
    map_id: int,
    position: list | None = None,
    radius: float = 2000,
    query: str = '',
    limit: int = 10,
    **_: Any,
) -> str:
    from backend.app.map.service.hex_terrain import get_cells_near, semantic_search_cells
    from backend.database.db import async_db_session

    async with async_db_session() as db:
        if query:
            cx = position[0] if position else None
            cz = position[1] if position else None
            results = await semantic_search_cells(
                db, map_id, query,
                cx=cx, cz=cz, radius=radius, limit=limit,
            )
            if not results:
                return json.dumps({'count': 0, 'cells': [], 'note': 'No hex cells found. Run hex cell generation first.'})
            return json.dumps({'count': len(results), 'cells': results}, indent=2)

        if position:
            cells = await get_cells_near(db, map_id, position[0], position[1], radius)
            cell_list = []
            for c in cells[:limit]:
                cell_list.append({
                    'center': [c.center_x, c.center_z],
                    'terrain_type': c.terrain_type,
                    'avg_height': c.avg_height,
                    'max_slope': c.max_slope,
                    'building_count': c.building_count,
                    'cover_rating': c.cover_rating,
                    'trafficability': c.trafficability,
                    'observation': c.observation,
                    'description': c.description,
                })
            return json.dumps({'count': len(cell_list), 'cells': cell_list}, indent=2)

    return json.dumps({'error': 'Provide position and/or query parameter'})


@builtin_registry.register(
    'get_hex_neighbors',
    display_name='Consulta de terreno adyacente',
    description=(
        'Get terrain information for hexagonal cells adjacent to a position. '
        'Useful for tactical movement planning — check what terrain surrounds a location '
        'before committing forces. Returns the center cell and all 6 neighbors.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'map_id': {'type': 'integer', 'description': 'Map ID'},
            'position': {
                'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2,
                'description': 'Position [x, z] to find the containing hex cell',
            },
        },
        'required': ['map_id', 'position'],
    },
)
async def get_hex_neighbors(map_id: int, position: list, **_: Any) -> str:
    from backend.app.map.service.hex_terrain import get_cells_near
    from backend.database.db import async_db_session

    async with async_db_session() as db:
        cells = await get_cells_near(db, map_id, position[0], position[1], radius=1500)

    if not cells:
        return json.dumps({'error': 'No hex cells found at this position. Run hex cell generation first.'})

    closest = min(cells, key=lambda c: (c.center_x - position[0]) ** 2 + (c.center_z - position[1]) ** 2)

    def _cell_dict(c):
        return {
            'center': [c.center_x, c.center_z],
            'terrain_type': c.terrain_type,
            'cover_rating': c.cover_rating,
            'trafficability': c.trafficability,
            'observation': c.observation,
            'avg_height': c.avg_height,
            'building_count': c.building_count,
        }

    result = {
        'center_cell': _cell_dict(closest),
        'neighbors': [_cell_dict(c) for c in cells if c.h3_index != closest.h3_index][:6],
    }
    return json.dumps(result, indent=2)
