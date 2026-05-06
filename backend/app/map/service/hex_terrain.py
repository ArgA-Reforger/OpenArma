"""H3 hexagonal terrain intelligence — pre-computed spatial features for LLM RAG.

Generates hex cells (H3 resolution 9, ~174m edge) for a map, computing terrain
features from height grid, water grid, entity data, roads, and zones.
Each cell gets a natural-language description and an embedding vector for
semantic search via pgvector.
"""

import asyncio
import logging
import math
import time
from typing import Any

import h3
import litellm
import numpy as np
from scipy.spatial import cKDTree
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.map.model.map import (
    GameMap,
    HexCell,
    MapEntity,
    MapLandmark,
    MapRoad,
    MapZone,
)

log = logging.getLogger(__name__)

H3_RESOLUTION = 9
CELL_EDGE_M = 174.375  # approx edge length at res-9


def _world_to_latlng(x: float, z: float, size_x: float, size_z: float) -> tuple[float, float]:
    """Convert game world coords to pseudo lat/lng for H3.

    Maps [0, size_x] → [0°, size_x/111320°] longitude
    Maps [0, size_z] → [0°, size_z/111320°] latitude
    111320m ≈ 1 degree at equator.
    """
    lat = z / 111320.0
    lng = x / 111320.0
    return lat, lng


def _latlng_to_world(lat: float, lng: float) -> tuple[float, float]:
    """Convert pseudo lat/lng back to game world coords."""
    x = lng * 111320.0
    z = lat * 111320.0
    return x, z


def get_map_h3_cells(size_x: float, size_z: float) -> list[str]:
    """Get all H3 cells covering a map rectangle."""
    corners = [
        _world_to_latlng(0, 0, size_x, size_z),
        _world_to_latlng(size_x, 0, size_x, size_z),
        _world_to_latlng(size_x, size_z, size_x, size_z),
        _world_to_latlng(0, size_z, size_x, size_z),
    ]
    polygon = h3.LatLngPoly(corners)
    cells = h3.polygon_to_cells(polygon, H3_RESOLUTION)
    return list(cells)


def _sample_height_grid(
    game_map: GameMap, cx: float, cz: float, radius: float = 250.0,
) -> tuple[float, float]:
    """Sample avg height and max slope from height grid around a point."""
    hg = game_map.height_grid_data
    if not hg:
        return 0.0, 0.0

    resolution = game_map.height_grid_resolution or 100
    offset_x = game_map.offset_x
    offset_z = game_map.offset_z
    cols = game_map.height_grid_cols or 0
    rows = game_map.height_grid_rows or 0

    heights = []
    slopes = []
    steps = max(1, int(radius / resolution))

    for dr in range(-steps, steps + 1):
        for dc in range(-steps, steps + 1):
            x = cx + dc * resolution
            z = cz + dr * resolution
            col = int((x - offset_x) / resolution)
            row = int((z - offset_z) / resolution)
            if 0 <= col < cols and 0 <= row < rows:
                h = hg[row][col] if isinstance(hg[row], list) else 0
                heights.append(h)

                dh_dx = dh_dz = 0.0
                if 0 < col < cols - 1:
                    dh_dx = (hg[row][col + 1] - hg[row][col - 1]) / (2 * resolution)
                if 0 < row < rows - 1:
                    dh_dz = (hg[row + 1][col] - hg[row - 1][col]) / (2 * resolution)
                slope = math.degrees(math.atan(math.sqrt(dh_dx ** 2 + dh_dz ** 2)))
                slopes.append(slope)

    avg_h = sum(heights) / len(heights) if heights else 0.0
    max_s = max(slopes) if slopes else 0.0
    return avg_h, max_s


def _sample_water_grid(
    game_map: GameMap, cx: float, cz: float, radius: float = 250.0,
) -> float:
    """Calculate water coverage ratio around a point."""
    wg = game_map.water_grid_data
    if not wg:
        return 0.0

    resolution = game_map.water_grid_resolution or 200
    offset_x = game_map.offset_x
    offset_z = game_map.offset_z
    cols = game_map.water_grid_cols or 0
    rows = game_map.water_grid_rows or 0

    total = 0
    water = 0
    steps = max(1, int(radius / resolution))

    for dr in range(-steps, steps + 1):
        for dc in range(-steps, steps + 1):
            x = cx + dc * resolution
            z = cz + dr * resolution
            col = int((x - offset_x) / resolution)
            row = int((z - offset_z) / resolution)
            if 0 <= col < cols and 0 <= row < rows:
                total += 1
                cell = wg[row][col] if isinstance(wg[row], list) else None
                if cell and isinstance(cell, list) and len(cell) >= 1 and cell[0] > 0:
                    water += 1

    return water / total if total > 0 else 0.0


def _classify_terrain(
    building_count: int,
    tree_density: float,
    water_coverage: float,
    max_slope: float,
    avg_height: float,
    height_diff: float = 0.0,
) -> str:
    """Classify terrain with landform awareness.

    ``height_diff`` = (this cell avg_height) − (mean of neighbor avg_heights).
    Positive → higher than surroundings; negative → lower.
    """
    if water_coverage > 0.5:
        return 'water'
    if building_count > 10:
        return 'urban'
    if building_count > 3:
        return 'suburban'

    if height_diff > 15:
        if max_slope > 20:
            return 'ridgeline'
        return 'hilltop'
    if height_diff < -15:
        if water_coverage > 0.1:
            return 'riverbed'
        return 'valley'

    if abs(height_diff) <= 5 and max_slope < 10:
        if tree_density < 0.2:
            return 'open_flat'
        return 'forest_floor'

    if max_slope > 30:
        if tree_density > 0.5:
            return 'forested_slope'
        return 'steep_slope'

    if tree_density > 0.4:
        return 'forest'
    return 'open'


def _rate_cover(terrain_type: str, tree_density: float, building_count: int) -> str:
    if terrain_type in ('urban', 'forest', 'forested_slope', 'forest_floor'):
        return 'excellent'
    if terrain_type in ('suburban', 'valley') or building_count > 5:
        return 'good'
    if tree_density > 0.3 or building_count > 0:
        return 'good'
    if tree_density > 0.1:
        return 'moderate'
    if terrain_type in ('ridgeline', 'hilltop', 'open_flat', 'steep_slope'):
        return 'poor'
    return 'poor'


def _rate_trafficability(
    max_slope: float, water_coverage: float, tree_density: float, terrain_type: str,
) -> str:
    """Rate trafficability. max_slope is the PEAK slope within the hex cell,
    not the average. Thresholds are therefore raised to avoid over-penalizing
    cells that are mostly flat but contain a single steep feature."""
    if water_coverage > 0.7 or (max_slope > 55 and water_coverage > 0.3):
        return 'impassable'
    if max_slope > 50 or water_coverage > 0.5:
        return 'difficult'
    if max_slope > 35 or tree_density > 0.7 or terrain_type == 'steep_slope':
        return 'moderate'
    if terrain_type in ('open_flat', 'open', 'hilltop', 'suburban', 'urban'):
        return 'easy'
    if max_slope < 20 and tree_density < 0.5:
        return 'easy'
    return 'easy'


def _rate_observation(
    terrain_type: str, avg_height: float, tree_density: float, max_slope: float,
    height_diff: float = 0.0,
) -> str:
    if terrain_type in ('ridgeline', 'hilltop'):
        return 'excellent'
    if terrain_type in ('valley', 'riverbed', 'forest_floor'):
        return 'poor'
    if terrain_type in ('urban', 'forest', 'forested_slope') or tree_density > 0.5:
        return 'limited'
    if height_diff > 10 and tree_density < 0.3:
        return 'good'
    if terrain_type in ('open_flat', 'open') and tree_density < 0.2:
        return 'good'
    return 'moderate'


_TERRAIN_TACTICAL_DESC: dict[str, str] = {
    'ridgeline': 'Ridge line — excellent observation post with wide sightlines, but exposed to fire',
    'hilltop': 'Elevated position — good observation, but limited cover on approach',
    'valley': 'Valley/depression — concealed approach route for enemy infiltration',
    'riverbed': 'Low-lying riverbed — concealed movement corridor, limited observation',
    'open_flat': 'Open flat terrain — fast vehicle movement but fully exposed',
    'forest_floor': 'Dense forest interior — concealed positions, very limited visibility',
    'forested_slope': 'Forested slope — concealed movement with elevation change',
    'steep_slope': 'Exposed steep slope — slow movement, poor cover, channelizes movement',
    'forest': 'Forested area — good concealment, moderate observation',
    'urban': 'Urban area — excellent cover, complex sightlines, close-quarters',
    'suburban': 'Suburban area — scattered buildings provide cover and concealment',
    'water': 'Water body — impassable to ground forces',
    'open': 'Open terrain — moderate movement speed, limited natural cover',
}


def _build_description(
    cell_data: dict[str, Any],
    landmarks: list[str],
    height_diff: float = 0.0,
) -> str:
    """Generate a tactical terrain description for LLM consumption."""
    parts = []

    tt = cell_data['terrain_type']
    h = cell_data['avg_height']
    parts.append(f"{_TERRAIN_TACTICAL_DESC.get(tt, tt.capitalize() + ' terrain')} ({h:.0f}m)")

    if height_diff > 20:
        parts.append(f"dominates surroundings (+{height_diff:.0f}m above neighbors)")
    elif height_diff > 8:
        parts.append(f"slightly elevated (+{height_diff:.0f}m)")
    elif height_diff < -20:
        parts.append(f"terrain depression ({-height_diff:.0f}m below surroundings)")
    elif height_diff < -8:
        parts.append(f"slightly lower ({-height_diff:.0f}m below neighbors)")

    slope = cell_data['max_slope']
    if slope > 30:
        parts.append(f"steep slopes ({slope:.0f}°)")
    elif slope > 15:
        parts.append(f"moderate slopes ({slope:.0f}°)")

    bc = cell_data['building_count']
    if bc > 10:
        parts.append(f"dense buildings ({bc})")
    elif bc > 0:
        parts.append(f"some buildings ({bc})")

    td = cell_data['tree_density']
    if td > 0.6:
        parts.append("heavy forest cover")
    elif td > 0.3:
        parts.append("moderate vegetation")
    elif td > 0.1:
        parts.append("sparse vegetation")

    wc = cell_data['water_coverage']
    if wc > 0.5:
        parts.append("significant water bodies")
    elif wc > 0.1:
        parts.append("some water nearby")

    rd = cell_data['road_density']
    if rd > 0.5:
        parts.append("well-connected by roads")
    elif rd > 0.1:
        parts.append("road access available")

    parts.append(f"cover: {cell_data['cover_rating']}")
    parts.append(f"trafficability: {cell_data['trafficability']}")
    parts.append(f"observation: {cell_data['observation']}")

    if landmarks:
        parts.append(f"near: {', '.join(landmarks[:5])}")

    return ". ".join(parts) + "."


def _build_kdtree(positions: list[tuple[float, float]]) -> cKDTree | None:
    """Build a cKDTree from (x, z) positions. Returns None if empty."""
    if not positions:
        return None
    return cKDTree(np.array(positions))


def _count_within_radius(tree: cKDTree | None, cx: float, cz: float, radius: float) -> int:
    """Count points within Chebyshev (L-inf) radius using cKDTree."""
    if tree is None:
        return 0
    return len(tree.query_ball_point([cx, cz], radius, p=float('inf')))


def _build_road_kdtree(roads: list) -> tuple[cKDTree | None, int]:
    """Build a cKDTree from all road points. Returns (tree, total_point_count)."""
    pts = []
    for road in roads:
        for pt in (road.points or []):
            if len(pt) >= 3:
                pts.append((pt[0], pt[2]))
            elif len(pt) >= 2:
                pts.append((pt[0], pt[1]))
    if not pts:
        return None, 0
    return cKDTree(np.array(pts)), len(pts)


async def _embed_concurrent(
    descriptions: list[str],
    embedding_model: str,
    embedding_kwargs: dict[str, Any],
    rpm_limit: int | None = None,
    batch_size: int = 20,
    progress_cb: Any | None = None,
) -> list[list[float] | None]:
    """Generate embeddings concurrently, respecting RPM limit.

    Uses litellm.aembedding (native async) for compatibility with
    OpenAI-compatible providers like new-api.

    *progress_cb*: optional ``(done, total) -> None`` called after each batch.
    """
    embeddings: list[list[float] | None] = [None] * len(descriptions)
    if not descriptions:
        return embeddings

    batches = []
    for i in range(0, len(descriptions), batch_size):
        batches.append((i, descriptions[i:i + batch_size]))

    max_concurrent = max(1, (rpm_limit // 2)) if rpm_limit else 10
    log.info('Embedding %d descriptions in %d batches (batch_size=%d, rpm=%s, concurrency=%d)',
             len(descriptions), len(batches), batch_size, rpm_limit, max_concurrent)

    semaphore = asyncio.Semaphore(max_concurrent)
    call_times: list[float] = []
    completed_count = 0

    async def _embed_batch(start_idx: int, batch: list[str]):
        nonlocal completed_count
        async with semaphore:
            if rpm_limit and call_times:
                now = time.monotonic()
                window_start = now - 60.0
                recent = [t for t in call_times if t > window_start]
                if len(recent) >= rpm_limit:
                    wait = recent[0] - window_start + 0.1
                    await asyncio.sleep(wait)

            call_times.append(time.monotonic())
            try:
                response = await litellm.aembedding(
                    model=embedding_model,
                    input=batch,
                    **embedding_kwargs,
                )
                for j, item in enumerate(response.data):
                    embeddings[start_idx + j] = item['embedding']
                completed_count += len(batch)
                if progress_cb:
                    progress_cb(completed_count, len(descriptions))
            except Exception as exc:
                total_chars = sum(len(s) for s in batch)
                log.error(
                    'Embedding batch offset=%d failed: model=%s, api_base=%s, '
                    'batch_len=%d, total_chars=%d, sample=%r, error=%s',
                    start_idx, embedding_model,
                    embedding_kwargs.get('api_base', 'N/A'),
                    len(batch), total_chars, batch[0][:80] if batch else '',
                    exc,
                )

    tasks = [_embed_batch(start, batch) for start, batch in batches]
    await asyncio.gather(*tasks)
    return embeddings


async def generate_hex_cells(
    db: AsyncSession,
    game_map: GameMap,
    *,
    embedding_model: str = 'text-embedding-3-small',
    embedding_kwargs: dict[str, Any] | None = None,
    rpm_limit: int | None = None,
    batch_size: int = 20,
) -> int:
    """Generate or regenerate all hex cells for a map.

    Uses cKDTree spatial indexing for fast entity lookups and concurrent
    embedding generation with RPM throttling.

    Returns the number of cells created.
    """
    map_id = game_map.id
    size_x = game_map.size_x
    size_z = game_map.size_z

    await db.execute(delete(HexCell).where(HexCell.map_id == map_id))

    h3_cells = get_map_h3_cells(size_x, size_z)
    log.info('Generating %d hex cells for map %d (%s)', len(h3_cells), map_id, game_map.name)

    t0 = time.monotonic()

    entity_cats = ['tree', 'bush', 'vegetation']
    tree_stmt = (
        select(MapEntity.position_x, MapEntity.position_z)
        .where(MapEntity.map_id == map_id, MapEntity.category.in_(entity_cats))
    )
    tree_result = await db.execute(tree_stmt)
    tree_positions = [(r[0], r[1]) for r in tree_result.all()]

    building_cats = ['building', 'building_residential', 'building_commercial',
                     'building_industrial', 'building_military']
    bld_stmt = (
        select(MapEntity.position_x, MapEntity.position_z)
        .where(MapEntity.map_id == map_id, MapEntity.category.in_(building_cats))
    )
    bld_result = await db.execute(bld_stmt)
    building_positions = [(r[0], r[1]) for r in bld_result.all()]

    road_stmt = select(MapRoad).where(MapRoad.map_id == map_id)
    road_result = await db.execute(road_stmt)
    roads = list(road_result.scalars().all())

    landmark_stmt = select(MapLandmark).where(MapLandmark.map_id == map_id)
    landmark_result = await db.execute(landmark_stmt)
    all_landmarks = list(landmark_result.scalars().all())

    tree_kd = _build_kdtree(tree_positions)
    bld_kd = _build_kdtree(building_positions)
    road_kd, total_road_pts = _build_road_kdtree(roads)
    lm_kd = _build_kdtree([(lm.position_x, lm.position_z) for lm in all_landmarks]) if all_landmarks else None

    log.info(
        'Spatial indexes built: trees=%d, buildings=%d, road_pts=%d, landmarks=%d (%.1fs)',
        len(tree_positions), len(building_positions), total_road_pts, len(all_landmarks),
        time.monotonic() - t0,
    )

    cell_radius = CELL_EDGE_M

    # ---- Pass 1: collect raw metrics for each cell ----
    raw_cells: list[dict[str, Any]] = []
    h3_to_height: dict[str, float] = {}

    for h3_idx in h3_cells:
        lat, lng = h3.cell_to_latlng(h3_idx)
        cx, cz = _latlng_to_world(lat, lng)

        if cx < 0 or cx > size_x or cz < 0 or cz > size_z:
            continue

        avg_height, max_slope = _sample_height_grid(game_map, cx, cz, cell_radius)
        water_cov = _sample_water_grid(game_map, cx, cz, cell_radius)

        tree_count = _count_within_radius(tree_kd, cx, cz, cell_radius)
        area_cells = max(1, (2 * cell_radius / 100) ** 2)
        tree_dens = min(1.0, tree_count / (area_cells * 5))

        bld_count = _count_within_radius(bld_kd, cx, cz, cell_radius)

        road_pts_nearby = _count_within_radius(road_kd, cx, cz, cell_radius)
        road_dens = min(1.0, road_pts_nearby / max(1, total_road_pts) * 10)

        nearby_lm_names = []
        if lm_kd is not None:
            lm_radius = cell_radius * 1.5
            indices = lm_kd.query_ball_point([cx, cz], lm_radius, p=2)
            for idx in indices:
                lm_obj = all_landmarks[idx]
                if lm_obj.name:
                    nearby_lm_names.append(f"{lm_obj.name} ({lm_obj.type})")

        h3_to_height[h3_idx] = avg_height
        raw_cells.append({
            'h3_index': h3_idx,
            'center_x': round(cx, 1),
            'center_z': round(cz, 1),
            'avg_height': avg_height,
            'max_slope': max_slope,
            'building_count': bld_count,
            'tree_density': tree_dens,
            'road_density': road_dens,
            'water_coverage': water_cov,
            'landmarks': nearby_lm_names,
        })

    # ---- Pass 2: classify with neighbor context ----
    cells_data: list[dict[str, Any]] = []
    valid_h3 = set(h3_to_height.keys())

    for raw in raw_cells:
        h3_idx = raw['h3_index']
        neighbors = h3.grid_disk(h3_idx, 1)
        neighbor_heights = [
            h3_to_height[n] for n in neighbors
            if n != h3_idx and n in valid_h3
        ]
        mean_neighbor = (sum(neighbor_heights) / len(neighbor_heights)) if neighbor_heights else raw['avg_height']
        height_diff = raw['avg_height'] - mean_neighbor

        terrain_type = _classify_terrain(
            raw['building_count'], raw['tree_density'], raw['water_coverage'],
            raw['max_slope'], raw['avg_height'], height_diff,
        )
        cover = _rate_cover(terrain_type, raw['tree_density'], raw['building_count'])
        traffic = _rate_trafficability(raw['max_slope'], raw['water_coverage'], raw['tree_density'], terrain_type)
        obs = _rate_observation(terrain_type, raw['avg_height'], raw['tree_density'], raw['max_slope'], height_diff)

        data = {
            'h3_index': h3_idx,
            'center_x': raw['center_x'],
            'center_z': raw['center_z'],
            'avg_height': round(raw['avg_height'], 1),
            'max_slope': round(raw['max_slope'], 1),
            'terrain_type': terrain_type,
            'building_count': raw['building_count'],
            'tree_density': round(raw['tree_density'], 3),
            'road_density': round(raw['road_density'], 3),
            'water_coverage': round(raw['water_coverage'], 3),
            'cover_rating': cover,
            'trafficability': traffic,
            'observation': obs,
            'landmarks': raw['landmarks'],
        }
        data['description'] = _build_description(data, raw['landmarks'], height_diff)
        cells_data.append(data)

    t1 = time.monotonic()
    log.info('Computed %d cell features in %.1fs', len(cells_data), t1 - t0)

    from backend.app.map.service.tile_progress import set_progress
    total_cells = len(cells_data)
    set_progress(map_id, 'hex_cells', 0, total_cells, status='computing')

    descriptions = [c['description'] for c in cells_data]
    embeddings: list[list[float] | None] = [None] * len(descriptions)

    if descriptions and embedding_kwargs:
        set_progress(map_id, 'hex_cells', 0, total_cells, status='embedding')

        def _on_embed_progress(done: int, total: int):
            set_progress(map_id, 'hex_cells', done, total, status='embedding')

        embeddings = await _embed_concurrent(
            descriptions, embedding_model, embedding_kwargs,
            rpm_limit=rpm_limit, batch_size=batch_size,
            progress_cb=_on_embed_progress,
        )
        log.info('Embeddings generated in %.1fs', time.monotonic() - t1)
    elif descriptions:
        log.info('No embedding provider configured — hex cells saved without embeddings (spatial-only queries)')

    from backend.utils.timezone import timezone
    now = timezone.now()

    rows = []
    for cell_data, emb in zip(cells_data, embeddings):
        rows.append({
            'map_id': map_id,
            'h3_index': cell_data['h3_index'],
            'center_x': cell_data['center_x'],
            'center_z': cell_data['center_z'],
            'avg_height': cell_data['avg_height'],
            'max_slope': cell_data['max_slope'],
            'terrain_type': cell_data['terrain_type'],
            'building_count': cell_data['building_count'],
            'tree_density': cell_data['tree_density'],
            'road_density': cell_data['road_density'],
            'water_coverage': cell_data['water_coverage'],
            'cover_rating': cell_data['cover_rating'],
            'trafficability': cell_data['trafficability'],
            'observation': cell_data['observation'],
            'description': cell_data['description'],
            'embedding': emb,
            'created_time': now,
        })

    set_progress(map_id, 'hex_cells', total_cells, total_cells, status='saving')
    db_batch = 2000
    for i in range(0, len(rows), db_batch):
        await db.execute(insert(HexCell), rows[i:i + db_batch])

    await db.flush()
    log.info('Generated %d hex cells for map %d in %.1fs total', len(cells_data), map_id, time.monotonic() - t0)
    return len(cells_data)


async def get_cells_near(
    db: AsyncSession,
    map_id: int,
    cx: float,
    cz: float,
    radius: float = 2000.0,
) -> list[HexCell]:
    """Get hex cells within radius of a world position (simple bbox filter)."""
    stmt = (
        select(HexCell)
        .where(
            HexCell.map_id == map_id,
            HexCell.center_x.between(cx - radius, cx + radius),
            HexCell.center_z.between(cz - radius, cz + radius),
        )
    )
    result = await db.execute(stmt)
    cells = list(result.scalars().all())
    return [
        c for c in cells
        if math.sqrt((c.center_x - cx) ** 2 + (c.center_z - cz) ** 2) <= radius
    ]


async def semantic_search_cells(
    db: AsyncSession,
    map_id: int,
    query: str,
    *,
    cx: float | None = None,
    cz: float | None = None,
    radius: float = 3000.0,
    limit: int = 10,
    embedding_model: str = 'text-embedding-3-small',
    embedding_kwargs: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Semantic search over hex cells: spatial filter + vector similarity.

    If cx/cz provided, filters to cells within radius first.
    Returns cells ranked by embedding similarity to query.
    """
    kwargs = embedding_kwargs or {}
    try:
        response = await litellm.aembedding(model=embedding_model, input=[query], **kwargs)
        query_vector = response.data[0]['embedding']
    except Exception:
        log.exception('Failed to embed query for terrain search')
        return []

    conditions = [HexCell.map_id == map_id, HexCell.embedding.isnot(None)]
    if cx is not None and cz is not None:
        conditions.extend([
            HexCell.center_x.between(cx - radius, cx + radius),
            HexCell.center_z.between(cz - radius, cz + radius),
        ])

    stmt = (
        select(
            HexCell,
            HexCell.embedding.cosine_distance(query_vector).label('distance'),
        )
        .where(*conditions)
        .order_by('distance')
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    output = []
    for cell, dist in rows:
        if cx is not None and cz is not None:
            actual_dist = math.sqrt((cell.center_x - cx) ** 2 + (cell.center_z - cz) ** 2)
            if actual_dist > radius:
                continue

        output.append({
            'h3_index': cell.h3_index,
            'center': [cell.center_x, cell.center_z],
            'terrain_type': cell.terrain_type,
            'avg_height': cell.avg_height,
            'max_slope': cell.max_slope,
            'building_count': cell.building_count,
            'tree_density': cell.tree_density,
            'road_density': cell.road_density,
            'water_coverage': cell.water_coverage,
            'cover_rating': cell.cover_rating,
            'trafficability': cell.trafficability,
            'observation': cell.observation,
            'description': cell.description,
            'similarity': round(1.0 - dist, 4),
        })

    return output
