"""Area of Operations (AO) briefing generator.

Generates a natural-language terrain briefing for the LLM based on:
- Mission focus points and AO boundaries
- Three-layer precision rings (A: 0-1km detailed, B: 1-2km standard, C: 2km+ overview)
- Pre-computed hex cells, landmarks, roads, and zones within the AO

The briefing is cached in Redis and injected into the LLM system prompt.
"""

import json
import logging
import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.map.model.map import (
    GameMap,
    HexCell,
    MapLandmark,
    MapRoad,
    MapZone,
)

log = logging.getLogger(__name__)

ZONE_A_RADIUS = 1000  # detailed
ZONE_B_RADIUS = 2000  # standard
MIN_AO_SIZE = 4000    # minimum 4x4km
BUFFER = 1000         # 1km buffer around focus points


def compute_ao_bounds(focus_points: list[dict]) -> dict[str, float]:
    """Compute AO bounding box from focus points.

    Returns {"min_x", "max_x", "min_z", "max_z", "center_x", "center_z"}.
    """
    if not focus_points:
        return {'min_x': 0, 'max_x': MIN_AO_SIZE, 'min_z': 0, 'max_z': MIN_AO_SIZE,
                'center_x': MIN_AO_SIZE / 2, 'center_z': MIN_AO_SIZE / 2}

    xs = [fp['position'][0] for fp in focus_points]
    zs = [fp['position'][1] for fp in focus_points]

    min_x = min(xs) - BUFFER
    max_x = max(xs) + BUFFER
    min_z = min(zs) - BUFFER
    max_z = max(zs) + BUFFER

    width = max_x - min_x
    height = max_z - min_z
    if width < MIN_AO_SIZE:
        expand = (MIN_AO_SIZE - width) / 2
        min_x -= expand
        max_x += expand
    if height < MIN_AO_SIZE:
        expand = (MIN_AO_SIZE - height) / 2
        min_z -= expand
        max_z += expand

    return {
        'min_x': min_x,
        'max_x': max_x,
        'min_z': min_z,
        'max_z': max_z,
        'center_x': (min_x + max_x) / 2,
        'center_z': (min_z + max_z) / 2,
    }


def _distance(x1: float, z1: float, x2: float, z2: float) -> float:
    return math.sqrt((x1 - x2) ** 2 + (z1 - z2) ** 2)


def _min_distance_to_focus(x: float, z: float, focus_points: list[dict]) -> float:
    if not focus_points:
        return 0.0
    return min(_distance(x, z, fp['position'][0], fp['position'][1]) for fp in focus_points)


async def generate_ao_briefing(
    db: AsyncSession,
    game_map: GameMap,
    ao_config: dict[str, Any],
) -> str:
    """Generate a terrain briefing for the AO.

    ao_config format:
    {
        "center": [x, z],
        "size": [width, height],
        "focus_points": [
            {"position": [x, z], "label": "Morton (Primary)", "radius": 1000}
        ]
    }
    """
    map_id = game_map.id
    focus_points = ao_config.get('focus_points', [])

    if not focus_points and ao_config.get('center'):
        focus_points = [{'position': ao_config['center'], 'label': 'AO Center', 'radius': 1000}]

    bounds = compute_ao_bounds(focus_points)

    hex_stmt = (
        select(HexCell)
        .where(
            HexCell.map_id == map_id,
            HexCell.center_x.between(bounds['min_x'], bounds['max_x']),
            HexCell.center_z.between(bounds['min_z'], bounds['max_z']),
        )
    )
    hex_result = await db.execute(hex_stmt)
    hex_cells = list(hex_result.scalars().all())

    lm_stmt = (
        select(MapLandmark)
        .where(
            MapLandmark.map_id == map_id,
            MapLandmark.position_x.between(bounds['min_x'], bounds['max_x']),
            MapLandmark.position_z.between(bounds['min_z'], bounds['max_z']),
        )
    )
    lm_result = await db.execute(lm_stmt)
    landmarks = list(lm_result.scalars().all())

    road_stmt = select(MapRoad).where(MapRoad.map_id == map_id)
    road_result = await db.execute(road_stmt)
    roads = list(road_result.scalars().all())

    zone_stmt = (
        select(MapZone)
        .where(
            MapZone.map_id == map_id,
            MapZone.center_x.between(bounds['min_x'], bounds['max_x']),
            MapZone.center_z.between(bounds['min_z'], bounds['max_z']),
        )
    )
    zone_result = await db.execute(zone_stmt)
    zones = list(zone_result.scalars().all())

    zone_a_cells = []
    zone_b_cells = []
    zone_c_cells = []

    for cell in hex_cells:
        dist = _min_distance_to_focus(cell.center_x, cell.center_z, focus_points)
        if dist <= ZONE_A_RADIUS:
            zone_a_cells.append(cell)
        elif dist <= ZONE_B_RADIUS:
            zone_b_cells.append(cell)
        else:
            zone_c_cells.append(cell)

    sections: list[str] = []
    ao_width = bounds['max_x'] - bounds['min_x']
    ao_height = bounds['max_z'] - bounds['min_z']
    sections.append(f'== AO TERRAIN BRIEFING (map: {game_map.name}) ==')
    sections.append(f'AO bounds: [{bounds["min_x"]:.0f},{bounds["min_z"]:.0f}] to '
                    f'[{bounds["max_x"]:.0f},{bounds["max_z"]:.0f}] ({ao_width:.0f}x{ao_height:.0f}m)')
    sections.append(f'Focus points: {len(focus_points)}')
    for fp in focus_points:
        sections.append(f'  - {fp.get("label", "unnamed")} at {fp["position"]}')
    sections.append('')

    if zone_a_cells:
        sections.append(f'= ZONE A: IMMEDIATE AREA ({len(zone_a_cells)} sectors, 0-{ZONE_A_RADIUS}m from objectives) =')
        for cell in zone_a_cells:
            sections.append(f'  [{cell.center_x:.0f},{cell.center_z:.0f}] {cell.description}')
        sections.append('')

    if zone_b_cells:
        sections.append(f'= ZONE B: APPROACH AREA ({len(zone_b_cells)} sectors, {ZONE_A_RADIUS}-{ZONE_B_RADIUS}m) =')
        terrain_summary: dict[str, int] = {}
        for cell in zone_b_cells:
            terrain_summary[cell.terrain_type] = terrain_summary.get(cell.terrain_type, 0) + 1
        for tt, count in sorted(terrain_summary.items(), key=lambda x: -x[1]):
            sections.append(f'  {tt}: {count} sector(s)')

        strategic_b = [
            lm for lm in landmarks
            if lm.type in ('military_base', 'airport', 'viewtower', 'viewpoint', 'hill', 'fortress')
            and ZONE_A_RADIUS < _min_distance_to_focus(lm.position_x, lm.position_z, focus_points) <= ZONE_B_RADIUS
        ]
        if strategic_b:
            sections.append('  Key positions:')
            for lm in strategic_b[:10]:
                sections.append(f'    - {lm.name} ({lm.type}) at [{lm.position_x:.0f},{lm.position_z:.0f}]')
        sections.append('')

    if zone_c_cells:
        sections.append(f'= ZONE C: OUTER AREA ({len(zone_c_cells)} sectors, >{ZONE_B_RADIUS}m) =')
        terrain_c: dict[str, int] = {}
        for cell in zone_c_cells:
            terrain_c[cell.terrain_type] = terrain_c.get(cell.terrain_type, 0) + 1
        summary_parts = [f'{tt}({n})' for tt, n in sorted(terrain_c.items(), key=lambda x: -x[1])]
        sections.append(f'  Terrain: {", ".join(summary_parts)}')
        sections.append('')

    strategic_lm = [
        lm for lm in landmarks
        if lm.type in ('city', 'town', 'village', 'military_base', 'airport', 'hill',
                        'fortress', 'viewtower', 'viewpoint', 'bunker')
    ]
    if strategic_lm:
        sections.append(f'= KEY LANDMARKS ({len(strategic_lm)}) =')
        strategic_lm.sort(key=lambda lm: _min_distance_to_focus(lm.position_x, lm.position_z, focus_points))
        for lm in strategic_lm[:20]:
            dist = _min_distance_to_focus(lm.position_x, lm.position_z, focus_points)
            sections.append(f'  {lm.name} ({lm.type}) [{lm.position_x:.0f},{lm.position_z:.0f}] dist={dist:.0f}m')
        sections.append('')

    ao_roads = []
    for road in roads:
        pts = road.points or []
        in_ao = any(
            bounds['min_x'] <= pt[0] <= bounds['max_x']
            and bounds['min_z'] <= (pt[2] if len(pt) >= 3 else pt[1]) <= bounds['max_z']
            for pt in pts if len(pt) >= 2
        )
        if in_ao:
            ao_roads.append(road)

    if ao_roads:
        sections.append(f'= ROAD NETWORK ({len(ao_roads)} segments) =')
        road_types: dict[str, int] = {}
        for road in ao_roads:
            road_types[road.type] = road_types.get(road.type, 0) + 1
        for rt, count in sorted(road_types.items(), key=lambda x: -x[1]):
            sections.append(f'  {rt}: {count}')
        sections.append('')

    if zones:
        sections.append(f'= URBAN ZONES ({len(zones)}) =')
        for z in zones:
            dist = _min_distance_to_focus(z.center_x, z.center_z, focus_points)
            sections.append(f'  {z.name} ({z.type}) buildings={z.building_count} dist={dist:.0f}m')
            if z.tactical_notes:
                sections.append(f'    Notes: {z.tactical_notes}')
        sections.append('')

    return '\n'.join(sections)


async def get_cached_briefing(project_id: int) -> str | None:
    """Get cached AO briefing from Redis."""
    from backend.database.redis import redis_client

    key = f'ao_briefing:{project_id}'
    try:
        data = await redis_client.get(key)
        return data.decode() if data else None
    except Exception:
        return None


async def cache_briefing(project_id: int, briefing: str, ttl: int = 86400) -> None:
    """Cache AO briefing in Redis (default 24h TTL)."""
    from backend.database.redis import redis_client

    key = f'ao_briefing:{project_id}'
    try:
        await redis_client.set(key, briefing, ex=ttl)
    except Exception:
        log.exception('Failed to cache AO briefing for project %d', project_id)


async def invalidate_briefing(project_id: int) -> None:
    """Invalidate cached AO briefing."""
    from backend.database.redis import redis_client

    key = f'ao_briefing:{project_id}'
    try:
        await redis_client.delete(key)
    except Exception:
        pass
