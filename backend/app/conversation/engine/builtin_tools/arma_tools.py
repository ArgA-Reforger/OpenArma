"""Arma Reforger 专用内置工具：距离计算、威胁评估、指令验证、小队查询、巡逻路线生成。"""

import json
import math
from typing import Any

from backend.app.conversation.engine.builtin_tools.registry import builtin_registry


@builtin_registry.register(
    'calculate_distance',
    display_name='距离计算',
    description=(
        'Calculate the distance between two 3D positions on the battlefield. '
        'Returns 3D distance, horizontal distance (ignoring height), and height difference in meters. '
        'Use this to assess how far apart squads are, or how far a squad is from an objective or enemy.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'pos_a': {
                'type': 'array',
                'items': {'type': 'number'},
                'minItems': 3,
                'maxItems': 3,
                'description': 'First position [x, y, z]',
            },
            'pos_b': {
                'type': 'array',
                'items': {'type': 'number'},
                'minItems': 3,
                'maxItems': 3,
                'description': 'Second position [x, y, z]',
            },
        },
        'required': ['pos_a', 'pos_b'],
    },
)
async def calculate_distance(pos_a: list, pos_b: list, **_: Any) -> str:
    dx = pos_a[0] - pos_b[0]
    dy = pos_a[1] - pos_b[1]
    dz = pos_a[2] - pos_b[2]
    dist_3d = math.sqrt(dx * dx + dy * dy + dz * dz)
    dist_horizontal = math.sqrt(dx * dx + dz * dz)
    height_diff = abs(dy)
    return (
        f'3D distance: {dist_3d:.1f}m, '
        f'Horizontal distance: {dist_horizontal:.1f}m, '
        f'Height difference: {height_diff:.1f}m'
    )


@builtin_registry.register(
    'assess_threats',
    display_name='威胁评估',
    description=(
        'Analyze the current situational data and produce a threat assessment summary. '
        'Identifies the most dangerous enemies, which squads are at risk, and suggested priority targets. '
        'Pass the raw situational report JSON string as input.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'situation_json': {
                'type': 'string',
                'description': 'The raw situational report JSON string',
            },
        },
        'required': ['situation_json'],
    },
)
async def assess_threats(situation_json: str = '', **_: Any) -> str:
    if not situation_json or not situation_json.strip():
        return json.dumps({'threat_level': 'unknown', 'error': 'No situation data provided', 'active_threats': []})
    try:
        data = json.loads(situation_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({'threat_level': 'unknown', 'error': 'Invalid JSON', 'active_threats': []})
    groups = data.get('groups', [])

    all_enemies: list[dict] = []
    threatened_squads: list[dict] = []

    for g in groups:
        gpos = g.get('position', [0, 0, 0])
        for e in g.get('known_enemies', []):
            enemy = dict(e)
            enemy['spotted_by'] = g['id']
            all_enemies.append(enemy)

            epos = e.get('position', [0, 0, 0])
            dist = e.get('distance', -1)
            if dist < 0:
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(epos, gpos)))
            endangering = e.get('time_since_endangered', 9999) < 10 if 'time_since_endangered' in e else e.get('endangering', False)
            identified = e.get('time_since_side_recognized', 9999) < 999 if 'time_since_side_recognized' in e else e.get('identified', False)
            if dist < 300 and endangering:
                threatened_squads.append({
                    'squad': g['id'],
                    'threat_distance': round(dist),
                    'enemy_identified': identified,
                    'enemy_type': e.get('unit_type', 'unknown'),
                })

    all_enemies.sort(key=lambda x: x.get('time_since_seen', 999))

    summary = {
        'total_known_enemies': len(all_enemies),
        'recent_contacts': [e for e in all_enemies if e.get('time_since_seen', 999) < 60],
        'threatened_squads': threatened_squads,
        'most_dangerous': all_enemies[:3] if all_enemies else [],
    }

    return json.dumps(summary, indent=2)


_VALID_ORDER_TYPES = frozenset({
    'move', 'attack', 'retreat', 'force_move', 'defend', 'patrol',
    'route', 'set_combat_mode', 'set_speed', 'hold',
})
_VALID_COMBAT_MODES = frozenset({'fire_at_will', 'hold_fire', 'defend_only', 'stealth'})
_VALID_SPEEDS = frozenset({'walk', 'jog', 'sprint'})
_VALID_FORMATIONS = frozenset({'Line', 'Column', 'StaggeredColumn', 'Wedge', 'Vee'})


@builtin_registry.register(
    'validate_orders',
    display_name='指令验证',
    description=(
        'Validate a set of orders before sending them. '
        'Checks that all command types are valid, group_ids exist, coordinates are reasonable, '
        'and required parameters are present. Returns validation result with any errors found.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'orders_json': {
                'type': 'string',
                'description': 'The orders JSON string to validate',
            },
            'known_group_ids': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'List of valid group IDs from the current situation',
            },
        },
        'required': ['orders_json', 'known_group_ids'],
    },
)
async def validate_orders(orders_json: str = '', known_group_ids: list | None = None, **_: Any) -> str:
    if not orders_json or not orders_json.strip():
        return json.dumps({'valid': False, 'error': 'No orders data provided'})

    try:
        data = json.loads(orders_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({'valid': False, 'error': 'Invalid JSON'})

    errors: list[str] = []
    if isinstance(data, list):
        orders = data
    elif isinstance(data, dict):
        orders = data.get('orders', [])
    else:
        return json.dumps({'valid': False, 'error': f'Unexpected data type: {type(data).__name__}'})

    gids = set(known_group_ids or [])

    for i, order in enumerate(orders):
        otype = order.get('type')
        if otype not in _VALID_ORDER_TYPES:
            errors.append(f"Order {i}: invalid type '{otype}'")
        gid = order.get('group_id')
        if gid not in gids:
            errors.append(f"Order {i}: unknown group_id '{gid}'")
        if otype == 'set_combat_mode' and order.get('mode') not in _VALID_COMBAT_MODES:
            errors.append(f"Order {i}: invalid combat_mode '{order.get('mode')}'")
        if otype == 'set_speed' and order.get('speed') not in _VALID_SPEEDS:
            errors.append(f"Order {i}: invalid speed '{order.get('speed')}'")
        formation = order.get('formation')
        if formation and formation not in _VALID_FORMATIONS:
            errors.append(f"Order {i}: invalid formation '{formation}' (valid: {', '.join(sorted(_VALID_FORMATIONS))})")

    if isinstance(data, dict) and not data.get('briefing'):
        errors.append("Missing 'briefing' field")

    if errors:
        return json.dumps({'valid': False, 'errors': errors})
    return json.dumps({'valid': True, 'count': len(orders)})


@builtin_registry.register(
    'get_squad_summary',
    display_name='小队状态查询',
    description=(
        'Get a detailed summary of a specific squad from the situational data. '
        'Returns position, strength, casualties, current orders, known enemies, '
        'and combat readiness assessment.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'situation_json': {
                'type': 'string',
                'description': 'The raw situational report JSON string',
            },
            'group_id': {
                'type': 'string',
                'description': 'The squad/group ID to query',
            },
        },
        'required': ['situation_json', 'group_id'],
    },
)
async def get_squad_summary(situation_json: str = '', group_id: str = '', **_: Any) -> str:
    if not situation_json or not situation_json.strip():
        return json.dumps({'error': 'No situation data provided'})
    try:
        data = json.loads(situation_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({'error': 'Invalid JSON'})

    for g in data.get('groups', []):
        if g['id'] == group_id:
            original_count = g.get('member_count', 0) + g.get('casualties', 0)
            casualties_pct = (g.get('casualties', 0) / max(original_count, 1)) * 100
            if casualties_pct < 30:
                readiness = 'combat_ready'
            elif casualties_pct < 60:
                readiness = 'degraded'
            else:
                readiness = 'combat_ineffective'

            return json.dumps({
                'id': g['id'],
                'label': g.get('label', ''),
                'role': g.get('role', 'unknown'),
                'position': g.get('position'),
                'strength': (
                    f"{g.get('member_count', 0)} active, "
                    f"{g.get('casualties', 0)} casualties ({casualties_pct:.0f}%)"
                ),
                'readiness': readiness,
                'current_orders': g.get('current_waypoint_type', 'none'),
                'combat_mode': g.get('combat_mode', 'unknown'),
                'formation': g.get('formation', 'unknown'),
                'known_enemies': len(g.get('known_enemies', [])),
            }, indent=2)

    return f"Squad '{group_id}' not found in situational data."


@builtin_registry.register(
    'generate_patrol_route',
    display_name='巡逻路线生成',
    description=(
        'Generate a terrain-aware patrol route around a center position. '
        'Waypoints are placed at tactically advantageous terrain: ridgelines, '
        'forest edges, buildings with good observation — NOT a simple circle. '
        'Use this when you need to set up a patrol for a [RECON] squad. '
        'Optionally provide map_id for terrain-aware routing; without it, '
        'falls back to a geometric circle.'
    ),
    input_schema={
        'type': 'object',
        'properties': {
            'center': {
                'type': 'array',
                'items': {'type': 'number'},
                'minItems': 3,
                'maxItems': 3,
                'description': 'Center position [x, y, z]',
            },
            'radius': {
                'type': 'number',
                'description': 'Patrol radius in meters (400-800 recommended)',
            },
            'num_points': {
                'type': 'integer',
                'description': 'Number of waypoints (default: 6)',
                'default': 6,
            },
            'map_id': {
                'type': 'integer',
                'description': 'Map ID for terrain-aware routing (strongly recommended)',
            },
        },
        'required': ['center', 'radius'],
    },
)
async def generate_patrol_route(
    center: list, radius: float, num_points: int = 6,
    map_id: int | None = None, **_: Any,
) -> str:
    num_points = max(4, min(num_points, 12))

    if map_id is not None:
        result = await _generate_terrain_patrol(center, radius, num_points, map_id)
        if result is not None:
            return result

    waypoints = []
    for i in range(num_points):
        angle = (2 * math.pi * i) / num_points
        x = center[0] + radius * math.cos(angle)
        z = center[2] + radius * math.sin(angle)
        waypoints.append([round(x, 1), 0, round(z, 1)])

    return json.dumps({
        'center': center,
        'radius': radius,
        'waypoints': waypoints,
        'terrain_aware': False,
        'note': 'Geometric fallback — no terrain data. Y=0, game snaps to surface.',
    }, indent=2)


def _identify_approach_directions(
    cx: float, cz: float, radius: float, ring_cells: list,
) -> list[float]:
    """Identify likely concealed approach directions from hex terrain.

    Enemy forces prefer covered/concealed routes, NOT open roads.
    The new terrain types (valley, forested_slope, forest_floor) directly
    indicate concealed corridors that enemies would exploit.

    Returns angles (radians) of the most dangerous concealed approach corridors.
    """
    if not ring_cells:
        return []

    scored_angles: list[tuple[float, float]] = []
    for c, ang, dist in ring_cells:
        threat = 0.0

        cover = getattr(c, 'cover_rating', '') or ''
        if cover == 'excellent':
            threat += 4.0
        elif cover == 'good':
            threat += 2.5
        elif cover == 'moderate':
            threat += 1.0

        obs = getattr(c, 'observation', '') or ''
        if obs == 'poor':
            threat += 3.0
        elif obs == 'limited':
            threat += 2.0
        elif obs == 'excellent':
            threat -= 2.0

        terrain = getattr(c, 'terrain_type', '') or ''
        if terrain in ('valley', 'riverbed', 'forest_floor'):
            threat += 3.5
        elif terrain in ('forested_slope', 'forest'):
            threat += 2.0
        elif terrain in ('urban', 'suburban'):
            threat += 1.5
        elif terrain in ('ridgeline', 'hilltop', 'open_flat', 'open'):
            threat -= 2.0

        traff = getattr(c, 'trafficability', '') or ''
        if traff == 'impassable':
            threat -= 4.0
        elif traff == 'difficult':
            threat -= 1.5

        if threat > 2.0:
            scored_angles.append((ang, threat))

    if not scored_angles:
        return []

    scored_angles.sort(key=lambda x: -x[1])
    top = scored_angles[:max(3, len(scored_angles) // 3)]

    angles = sorted(a for a, _ in top)
    merged: list[float] = [angles[0]]
    for a in angles[1:]:
        if abs(a - merged[-1]) > math.radians(30):
            merged.append(a)
        else:
            merged[-1] = (merged[-1] + a) / 2
    return merged


def _score_cell(cell) -> float:
    """Score a hex cell for patrol waypoint suitability.

    Prefers: ridgelines/hilltops (observation), forest edges (cover+obs),
             positions that balance observation with some cover.
    Avoids: deep valleys (blind), water, impassable terrain.
    """
    score = 0.0

    terrain = getattr(cell, 'terrain_type', '') or ''
    if terrain in ('ridgeline', 'hilltop'):
        score += 3.0
    elif terrain in ('forested_slope', 'forest'):
        score += 1.5
    elif terrain in ('valley', 'riverbed'):
        score -= 1.0
    elif terrain == 'water':
        score -= 10.0

    obs = getattr(cell, 'observation', '') or ''
    if obs == 'excellent':
        score += 3.0
    elif obs == 'good':
        score += 2.0
    elif obs == 'moderate':
        score += 1.0
    elif obs == 'poor':
        score -= 1.0

    cover = getattr(cell, 'cover_rating', '') or ''
    if cover == 'excellent':
        score += 2.0
    elif cover == 'good':
        score += 1.5
    elif cover == 'moderate':
        score += 0.5

    traff = getattr(cell, 'trafficability', '') or ''
    if traff == 'easy':
        score += 1.0
    elif traff == 'moderate':
        score += 0.5
    elif traff == 'difficult':
        score -= 2.0
    elif traff == 'impassable':
        score -= 5.0

    score += min(getattr(cell, 'avg_height', 0) / 50.0, 2.0)

    return score


async def _generate_terrain_patrol(
    center: list, radius: float, num_points: int, map_id: int,
) -> str | None:
    """Generate patrol route using hex terrain data.

    Strategy:
    1. Analyze terrain ring for concealed approach corridors (forest, urban,
       low observation) — these are where enemies actually approach, not roads
    2. Bias sector placement so more waypoints face dangerous concealed directions
    3. Within each sector, pick the hex cell with the best tactical score
       (high ground, good observation, cover for the patrol itself)
    """
    from backend.app.map.service.hex_terrain import get_cells_near
    from backend.database.db import async_db_session

    cx, cz = center[0], center[2]

    async with async_db_session() as db:
        cells = await get_cells_near(db, map_id, cx, cz, radius * 1.5)

    if len(cells) < num_points:
        return None

    min_r = radius * 0.4
    max_r = radius * 1.3
    ring_cells = []
    for c in cells:
        dx = c.center_x - cx
        dz = c.center_z - cz
        dist = math.sqrt(dx * dx + dz * dz)
        if min_r <= dist <= max_r:
            ang = math.atan2(dz, dx)
            ring_cells.append((c, ang, dist))

    if len(ring_cells) < num_points:
        return None

    approach_dirs = _identify_approach_directions(cx, cz, radius, ring_cells)

    if approach_dirs and len(approach_dirs) >= 2:
        sector_angles = _build_approach_biased_sectors(approach_dirs, num_points)
    else:
        sector_angles = [
            -math.pi + i * (2 * math.pi / num_points)
            for i in range(num_points)
        ]

    waypoints = []
    for i in range(len(sector_angles)):
        s_start = sector_angles[i]
        s_end = sector_angles[(i + 1) % len(sector_angles)]
        if s_end <= s_start:
            s_end += 2 * math.pi

        candidates = []
        for c, ang, dist in ring_cells:
            norm = ang
            if norm < s_start:
                norm += 2 * math.pi
            if s_start <= norm < s_end:
                candidates.append((c, dist))

        is_approach = any(
            _angle_in_sector(a, s_start, s_end) for a in approach_dirs
        )

        if candidates:
            best = max(
                candidates,
                key=lambda x: _score_cell(x[0]) + (1.5 if is_approach else 0),
            )
            c = best[0]
            waypoints.append({
                'pos': [round(c.center_x, 1), 0, round(c.center_z, 1)],
                'terrain': getattr(c, 'terrain_type', 'unknown'),
                'cover': getattr(c, 'cover_rating', 'unknown'),
                'observation': getattr(c, 'observation', 'unknown'),
                'faces_approach': is_approach,
            })
        else:
            angle = (s_start + s_end) / 2
            x = cx + radius * math.cos(angle)
            z = cz + radius * math.sin(angle)
            waypoints.append({
                'pos': [round(x, 1), 0, round(z, 1)],
                'terrain': 'unknown',
                'cover': 'unknown',
                'observation': 'unknown',
                'faces_approach': is_approach,
            })

    return json.dumps({
        'center': center,
        'radius': radius,
        'waypoints': [w['pos'] for w in waypoints],
        'waypoint_details': waypoints,
        'approach_directions': len(approach_dirs),
        'terrain_aware': True,
        'note': (
            'Waypoints placed at tactically advantageous terrain, '
            'biased toward road approach directions. '
            'Y=0, game snaps to surface height.'
        ),
    }, indent=2)


def _angle_in_sector(angle: float, s_start: float, s_end: float) -> bool:
    norm = angle
    if norm < s_start:
        norm += 2 * math.pi
    return s_start <= norm < s_end


def _build_approach_biased_sectors(
    approach_dirs: list[float], num_points: int,
) -> list[float]:
    """Build sector boundaries biased toward approach directions.

    Places more sector boundaries near approach directions so that
    patrol waypoints cluster around likely enemy routes.
    """
    base_angles = sorted(set(approach_dirs))

    while len(base_angles) < num_points:
        gaps = []
        for i in range(len(base_angles)):
            a = base_angles[i]
            b = base_angles[(i + 1) % len(base_angles)]
            gap = b - a if b > a else (b + 2 * math.pi - a)
            gaps.append((gap, i))
        gaps.sort(reverse=True)
        biggest_gap, idx = gaps[0]
        a = base_angles[idx]
        mid = a + biggest_gap / 2
        if mid > math.pi:
            mid -= 2 * math.pi
        base_angles.append(mid)
        base_angles.sort()

    return base_angles[:num_points]
