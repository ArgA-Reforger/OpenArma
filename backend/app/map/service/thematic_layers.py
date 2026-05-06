"""Thematic layer generation — ADR-040 dual-mode (Human + LLM).

Each layer generator returns a dict with:
  - human: data suitable for frontend rendering (GeoJSON, grid images, etc.)
  - llm:   structured JSON for AI agent consumption

Performance optimizations (v2):
  - P0: Single DB query per map, grouped by category
  - P1: NumPy vectorized hillshade/slope/trafficability
  - P4: Contour line simplification (Douglas-Peucker)
"""

from __future__ import annotations

import hashlib
import math
import time
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.map.model.map import GameMap, MapEntity

SWIM_DEPTH_THRESHOLD = 1.5

# ---------------------------------------------------------------------------
# Layer cache — in-memory with TTL (avoids recomputing expensive layers)
# ---------------------------------------------------------------------------

_layer_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 600


def _cache_key(map_id: int, layer: str, **params: Any) -> str:
    raw = f'{map_id}:{layer}:{sorted(params.items())}'
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(key: str) -> dict | None:
    entry = _layer_cache.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.monotonic() - ts > CACHE_TTL_SECONDS:
        del _layer_cache[key]
        return None
    return data


def _cache_set(key: str, data: dict) -> None:
    if len(_layer_cache) > 200:
        oldest_key = min(_layer_cache, key=lambda k: _layer_cache[k][0])
        del _layer_cache[oldest_key]
    _layer_cache[key] = (time.monotonic(), data)


# ---------------------------------------------------------------------------
# P0: Grouped entity query — single DB round-trip
# ---------------------------------------------------------------------------

_entity_group_cache: dict[str, tuple[float, dict[str, list[tuple[float, float]]]]] = {}
_ENTITY_GROUP_TTL = 300


async def _entity_positions_grouped(
    db: AsyncSession, map_id: int,
) -> dict[str, list[tuple[float, float]]]:
    """Fetch ALL entity positions for a map in one query, grouped by category."""
    ck = f'epg:{map_id}'
    entry = _entity_group_cache.get(ck)
    if entry:
        ts, data = entry
        if time.monotonic() - ts < _ENTITY_GROUP_TTL:
            return data

    stmt = select(
        MapEntity.category, MapEntity.position_x, MapEntity.position_z
    ).where(MapEntity.map_id == map_id)
    result = await db.execute(stmt)

    grouped: dict[str, list[tuple[float, float]]] = {}
    for cat, px, pz in result.all():
        grouped.setdefault(cat, []).append((px, pz))

    _entity_group_cache[ck] = (time.monotonic(), grouped)
    return grouped


def _positions_for_categories(
    grouped: dict[str, list[tuple[float, float]]],
    categories: list[str],
) -> list[tuple[float, float]]:
    """Extract positions for given categories from grouped data."""
    result: list[tuple[float, float]] = []
    for cat in categories:
        result.extend(grouped.get(cat, []))
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _grid_coords(
    size_x: float, size_z: float, cell_size: float
) -> tuple[int, int]:
    cols = max(1, math.ceil(size_x / cell_size))
    rows = max(1, math.ceil(size_z / cell_size))
    return cols, rows


def _density_grid_np(
    positions: list[tuple[float, float]],
    size_x: float, size_z: float, cell_size: float,
) -> tuple[np.ndarray, int, int]:
    """Build density grid using NumPy for speed."""
    cols, rows = _grid_coords(size_x, size_z, cell_size)
    if not positions:
        return np.zeros((rows, cols), dtype=np.float32), cols, rows

    arr = np.array(positions, dtype=np.float32)
    ci = np.clip((arr[:, 0] / cell_size).astype(np.int32), 0, cols - 1)
    ri = np.clip((arr[:, 1] / cell_size).astype(np.int32), 0, rows - 1)
    grid = np.zeros((rows, cols), dtype=np.float32)
    np.add.at(grid, (ri, ci), 1)
    return grid, cols, rows


def _normalize_grid_np(grid: np.ndarray) -> np.ndarray:
    mx = grid.max()
    if mx == 0:
        return grid
    return grid / mx


def _grid_to_list(grid: np.ndarray, decimals: int = 3) -> list[list[float]]:
    """Convert numpy grid to nested list with rounding."""
    return np.round(grid, decimals).tolist()


def _find_hotspots(
    grid: np.ndarray, cell_size: float, threshold: float = 0.7, top_n: int = 10
) -> list[dict]:
    rs, cs = np.where(grid >= threshold)
    if len(rs) == 0:
        return []
    vals = grid[rs, cs]
    order = np.argsort(-vals)[:top_n]
    return [
        {
            'center': [round(float(cs[i]) * cell_size + cell_size / 2, 1),
                       round(float(rs[i]) * cell_size + cell_size / 2, 1)],
            'density': round(float(vals[i]), 3),
        }
        for i in order
    ]


ZONE_NAMES_3X3 = ['NW', 'N', 'NE', 'W', 'C', 'E', 'SW', 'S', 'SE']


def _zone_summary(
    grid: np.ndarray,
    cell_size: float,
    size_x: float,
    size_z: float,
    grid_divisions: int = 3,
    label: str = 'density',
) -> list[dict]:
    rows, cols = grid.shape
    if rows == 0 or cols == 0:
        return []

    zone_rows = max(1, rows // grid_divisions)
    zone_cols = max(1, cols // grid_divisions)
    names = ZONE_NAMES_3X3 if grid_divisions == 3 else [
        f'Z{i}' for i in range(grid_divisions * grid_divisions)
    ]

    zones = []
    idx = 0
    for zr in range(grid_divisions):
        for zc in range(grid_divisions):
            r_start = zr * zone_rows
            r_end = min(r_start + zone_rows, rows)
            c_start = zc * zone_cols
            c_end = min(c_start + zone_cols, cols)

            block = grid[r_start:r_end, c_start:c_end]
            if block.size == 0:
                idx += 1
                continue

            avg = float(block.mean())
            mx = float(block.max())

            cx = round((c_start + c_end) / 2 * cell_size, 0)
            cz = round((r_start + r_end) / 2 * cell_size, 0)

            if avg > 0.7:
                level = 'very_high'
            elif avg > 0.4:
                level = 'high'
            elif avg > 0.15:
                level = 'moderate'
            elif avg > 0.02:
                level = 'low'
            else:
                level = 'none'

            name = names[idx] if idx < len(names) else f'Z{idx}'
            zones.append({
                'zone': name,
                'center': [cx, cz],
                'area_m': [
                    round(c_start * cell_size), round(r_start * cell_size),
                    round(c_end * cell_size), round(r_end * cell_size),
                ],
                f'avg_{label}': round(avg, 3),
                f'max_{label}': round(mx, 3),
                'level': level,
            })
            idx += 1

    return zones


def _find_corridors(
    grid: np.ndarray,
    cell_size: float,
    low_threshold: float = 0.1,
    min_length: int = 3,
    *,
    above: bool = False,
) -> list[dict]:
    rows, cols = grid.shape
    corridors = []

    for r in range(rows):
        row = grid[r]
        mask = row >= low_threshold if above else row <= low_threshold
        run_start = None
        for c in range(cols + 1):
            val = bool(mask[c]) if c < cols else False
            if val:
                if run_start is None:
                    run_start = c
            else:
                if run_start is not None and (c - run_start) >= min_length:
                    corridors.append({
                        'direction': 'east-west',
                        'from': [round(run_start * cell_size), round(r * cell_size + cell_size / 2)],
                        'to': [round(c * cell_size), round(r * cell_size + cell_size / 2)],
                        'length_m': round((c - run_start) * cell_size),
                    })
                run_start = None

    for c in range(cols):
        col = grid[:, c]
        mask = col >= low_threshold if above else col <= low_threshold
        run_start = None
        for r in range(rows + 1):
            val = bool(mask[r]) if r < rows else False
            if val:
                if run_start is None:
                    run_start = r
            else:
                if run_start is not None and (r - run_start) >= min_length:
                    corridors.append({
                        'direction': 'north-south',
                        'from': [round(c * cell_size + cell_size / 2), round(run_start * cell_size)],
                        'to': [round(c * cell_size + cell_size / 2), round(r * cell_size)],
                        'length_m': round((r - run_start) * cell_size),
                    })
                run_start = None

    corridors.sort(key=lambda x: x['length_m'], reverse=True)
    return corridors[:10]


def _find_terrain_features(
    hg_np: np.ndarray, res: float
) -> dict:
    rows, cols = hg_np.shape
    if rows < 3 or cols < 3:
        return {'peaks': [], 'valleys': [], 'passes': []}

    center = hg_np[1:-1, 1:-1]
    neighbors = [
        hg_np[:-2, :-2], hg_np[:-2, 1:-1], hg_np[:-2, 2:],
        hg_np[1:-1, :-2], hg_np[1:-1, 2:],
        hg_np[2:, :-2], hg_np[2:, 1:-1], hg_np[2:, 2:],
    ]

    is_peak = np.ones(center.shape, dtype=bool)
    is_valley = np.ones(center.shape, dtype=bool)
    for n in neighbors:
        is_peak &= center > n
        is_valley &= center < n

    peaks = []
    prs, pcs = np.where(is_peak)
    for i in range(min(len(prs), 50)):
        r, c = int(prs[i]) + 1, int(pcs[i]) + 1
        peaks.append({'pos': [round(c * res), round(r * res)], 'elevation': round(float(hg_np[r, c]), 1)})
    peaks.sort(key=lambda x: x['elevation'], reverse=True)

    valleys = []
    vrs, vcs = np.where(is_valley)
    for i in range(min(len(vrs), 50)):
        r, c = int(vrs[i]) + 1, int(vcs[i]) + 1
        valleys.append({'pos': [round(c * res), round(r * res)], 'elevation': round(float(hg_np[r, c]), 1)})
    valleys.sort(key=lambda x: x['elevation'])

    passes = []
    for v in valleys[:20]:
        vr = int(v['pos'][1] / res)
        vc = int(v['pos'][0] / res)
        if 1 <= vr < rows - 1 and 1 <= vc < cols - 1:
            ns_diff = min(float(hg_np[vr - 1, vc]), float(hg_np[vr + 1, vc])) - float(hg_np[vr, vc])
            ew_diff = min(float(hg_np[vr, vc - 1]), float(hg_np[vr, vc + 1])) - float(hg_np[vr, vc])
            if (ns_diff > 10 and ew_diff < 5) or (ew_diff > 10 and ns_diff < 5):
                passes.append({
                    'pos': v['pos'],
                    'elevation': v['elevation'],
                    'note': 'mountain pass / saddle point',
                })

    return {
        'peaks': peaks[:10],
        'valleys': valleys[:10],
        'passes': passes[:5],
    }


# ---------------------------------------------------------------------------
# P4: Douglas-Peucker line simplification
# ---------------------------------------------------------------------------

def _simplify_line(points: list[list[float]], epsilon: float = 5.0) -> list[list[float]]:
    """Simplify a polyline using the Ramer-Douglas-Peucker algorithm."""
    if len(points) <= 2:
        return points

    def _perp_dist(p: list[float], a: list[float], b: list[float]) -> float:
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx == 0 and dy == 0:
            return math.sqrt((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
        t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        proj_x = a[0] + t * dx
        proj_y = a[1] + t * dy
        return math.sqrt((p[0] - proj_x) ** 2 + (p[1] - proj_y) ** 2)

    max_dist = 0.0
    max_idx = 0
    for i in range(1, len(points) - 1):
        d = _perp_dist(points[i], points[0], points[-1])
        if d > max_dist:
            max_dist = d
            max_idx = i

    if max_dist > epsilon:
        left = _simplify_line(points[:max_idx + 1], epsilon)
        right = _simplify_line(points[max_idx:], epsilon)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]


# ---------------------------------------------------------------------------
# P1: Vegetation Density Layer
# ---------------------------------------------------------------------------

async def vegetation_density(
    db: AsyncSession, game_map: GameMap, cell_size: float = 100
) -> dict[str, Any]:
    ck = _cache_key(game_map.id, 'vegetation', cell_size=cell_size)
    cached = _cache_get(ck)
    if cached:
        return cached

    grouped = await _entity_positions_grouped(db, game_map.id)
    categories = ['tree', 'bush', 'grass', 'vegetation']
    positions = _positions_for_categories(grouped, categories)

    grid, cols, rows = _density_grid_np(positions, game_map.size_x, game_map.size_z, cell_size)
    norm_grid = _normalize_grid_np(grid)
    hotspots = _find_hotspots(norm_grid, cell_size)

    total = len(positions)
    area = game_map.size_x * game_map.size_z
    avg_density = total / (area / 1_000_000) if area > 0 else 0

    result = {
        'layer_type': 'vegetation_density',
        'human': {
            'grid': _grid_to_list(norm_grid),
            'grid_size_m': cell_size,
            'cols': cols,
            'rows': rows,
            'color_scale': ['#f7fcf5', '#c7e9c0', '#74c476', '#238b45', '#00441b'],
            'legend': 'Vegetation density (0=bare, 1=dense)',
        },
        'llm': {
            'layer_type': 'vegetation_density',
            'grid_size_m': cell_size,
            'map_size': [game_map.size_x, game_map.size_z],
            'total_entities': total,
            'breakdown': {
                cat: len(grouped.get(cat, [])) for cat in categories
            },
            'avg_density_per_km2': round(avg_density, 1),
            'zones': _zone_summary(norm_grid, cell_size, game_map.size_x, game_map.size_z, label='vegetation'),
            'hotspots': hotspots,
            'open_corridors': _find_corridors(norm_grid, cell_size, low_threshold=0.1, min_length=3),
        },
    }
    _cache_set(ck, result)
    return result


# ---------------------------------------------------------------------------
# P1: Built-up Area Layer
# ---------------------------------------------------------------------------

async def builtup_area(
    db: AsyncSession, game_map: GameMap, cell_size: float = 100
) -> dict[str, Any]:
    ck = _cache_key(game_map.id, 'builtup', cell_size=cell_size)
    cached = _cache_get(ck)
    if cached:
        return cached

    grouped = await _entity_positions_grouped(db, game_map.id)
    categories = [
        'building', 'building_residential', 'building_commercial',
        'building_industrial', 'building_public', 'building_military',
    ]
    positions = _positions_for_categories(grouped, categories)

    grid, cols, rows = _density_grid_np(positions, game_map.size_x, game_map.size_z, cell_size)
    norm_grid = _normalize_grid_np(grid)
    hotspots = _find_hotspots(norm_grid, cell_size, threshold=0.5)

    cat_counts = {cat: len(grouped.get(cat, [])) for cat in categories if grouped.get(cat)}

    result = {
        'layer_type': 'builtup_area',
        'human': {
            'grid': _grid_to_list(norm_grid),
            'grid_size_m': cell_size,
            'cols': cols,
            'rows': rows,
            'color_scale': ['#fff5f0', '#fcbba1', '#fb6a4a', '#cb181d', '#67000d'],
            'legend': 'Built-up density (0=open, 1=dense urban)',
        },
        'llm': {
            'layer_type': 'builtup_area',
            'grid_size_m': cell_size,
            'map_size': [game_map.size_x, game_map.size_z],
            'total_buildings': len(positions),
            'breakdown': cat_counts,
            'zones': _zone_summary(norm_grid, cell_size, game_map.size_x, game_map.size_z, label='builtup'),
            'hotspots': hotspots,
            'open_corridors': _find_corridors(norm_grid, cell_size, low_threshold=0.1, min_length=3),
        },
    }
    _cache_set(ck, result)
    return result


# ---------------------------------------------------------------------------
# P2: Contour Lines Layer (with simplification)
# ---------------------------------------------------------------------------

def contour_lines(
    game_map: GameMap, interval: float = 20
) -> dict[str, Any]:
    hg = game_map.height_grid_data
    if not hg:
        return {'layer_type': 'contour_lines', 'human': None, 'llm': None}

    res = game_map.height_grid_resolution or 100
    hg_np = np.array(hg, dtype=np.float32)
    rows_count, cols_count = hg_np.shape

    min_h = float(hg_np.min())
    max_h = float(hg_np.max())

    contour_levels = []
    level = math.ceil(min_h / interval) * interval
    while level <= max_h:
        contour_levels.append(level)
        level += interval

    contours: list[dict] = []
    simplify_eps = res * 0.3

    for level_h in contour_levels:
        segments: list[list[list[float]]] = []
        for r in range(rows_count - 1):
            for c in range(cols_count - 1):
                tl = float(hg_np[r, c])
                tr = float(hg_np[r, c + 1])
                bl = float(hg_np[r + 1, c])
                br = float(hg_np[r + 1, c + 1])

                cell_x = c * res
                cell_z = r * res

                edges = _marching_square_edges(tl, tr, bl, br, level_h, cell_x, cell_z, res)
                if edges:
                    segments.extend(edges)

        if segments:
            merged = _merge_contour_segments(segments)
            simplified = [_simplify_line(seg, simplify_eps) for seg in merged if len(seg) >= 2]
            if simplified:
                contours.append({'elevation': level_h, 'segments': simplified})

    key_elevations = [lv for lv in contour_levels if lv % (interval * 5) == 0]

    return {
        'layer_type': 'contour_lines',
        'human': {
            'contours': contours,
            'interval': interval,
            'color': '#8B4513',
            'major_interval': interval * 5,
            'major_color': '#5C3317',
        },
        'llm': {
            'layer_type': 'contour_lines',
            'interval_m': interval,
            'elevation_range': [round(min_h, 1), round(max_h, 1)],
            'num_contours': len(contours),
            'key_elevations': key_elevations,
            'grid_resolution_m': res,
            'height_grid_size': [cols_count, rows_count],
            'terrain_features': _find_terrain_features(hg_np, res),
        },
    }


def _merge_contour_segments(
    segments: list[list[list[float]]], tolerance: float = 0.5
) -> list[list[list[float]]]:
    """Merge short 2-point segments into longer polylines where endpoints match."""
    if not segments:
        return []

    chains: list[list[list[float]]] = [list(segments[0])]

    for seg in segments[1:]:
        merged = False
        p0, p1 = seg[0], seg[-1]
        for chain in chains:
            head, tail = chain[0], chain[-1]
            if _pts_close(p0, tail, tolerance):
                chain.extend(seg[1:])
                merged = True
                break
            if _pts_close(p1, head, tolerance):
                chain[:0] = seg[:-1]
                merged = True
                break
        if not merged:
            chains.append(list(seg))

    return chains


def _pts_close(a: list[float], b: list[float], tol: float) -> bool:
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def _marching_square_edges(
    tl: float, tr: float, bl: float, br: float,
    level: float, x: float, z: float, res: float
) -> list[list[list[float]]]:
    def interp(v1: float, v2: float, x1: float, x2: float) -> float:
        if abs(v2 - v1) < 1e-9:
            return (x1 + x2) / 2
        return x1 + (level - v1) / (v2 - v1) * (x2 - x1)

    case = 0
    if tl >= level:
        case |= 8
    if tr >= level:
        case |= 4
    if br >= level:
        case |= 2
    if bl >= level:
        case |= 1

    if case == 0 or case == 15:
        return []

    top = [interp(tl, tr, x, x + res), z]
    right = [x + res, interp(tr, br, z, z + res)]
    bottom = [interp(bl, br, x, x + res), z + res]
    left = [x, interp(tl, bl, z, z + res)]

    lookup = {
        1: [(left, bottom)],
        2: [(bottom, right)],
        3: [(left, right)],
        4: [(top, right)],
        5: [(left, top), (bottom, right)],
        6: [(top, bottom)],
        7: [(left, top)],
        8: [(left, top)],
        9: [(top, bottom)],
        10: [(left, bottom), (top, right)],
        11: [(top, right)],
        12: [(left, right)],
        13: [(bottom, right)],
        14: [(left, bottom)],
    }

    segments: list[list[list[float]]] = []
    for pair in lookup.get(case, []):
        segments.append([[round(pair[0][0], 1), round(pair[0][1], 1)],
                         [round(pair[1][0], 1), round(pair[1][1], 1)]])
    return segments


# ---------------------------------------------------------------------------
# P1: Slope Map Layer (NumPy vectorized)
# ---------------------------------------------------------------------------

def slope_map(
    game_map: GameMap, cell_size: float | None = None
) -> dict[str, Any]:
    hg = game_map.height_grid_data
    if not hg:
        return {'layer_type': 'slope_map', 'human': None, 'llm': None}

    res = game_map.height_grid_resolution or 100
    if cell_size is None:
        cell_size = res

    hg_np = np.array(hg, dtype=np.float32)
    rows_count, cols_count = hg_np.shape

    dzdx = np.zeros_like(hg_np)
    dzdy = np.zeros_like(hg_np)
    dzdx[:, 1:-1] = (hg_np[:, 2:] - hg_np[:, :-2]) / (2 * res)
    dzdx[:, 0] = (hg_np[:, 1] - hg_np[:, 0]) / res
    dzdx[:, -1] = (hg_np[:, -1] - hg_np[:, -2]) / res
    dzdy[1:-1, :] = (hg_np[2:, :] - hg_np[:-2, :]) / (2 * res)
    dzdy[0, :] = (hg_np[1, :] - hg_np[0, :]) / res
    dzdy[-1, :] = (hg_np[-1, :] - hg_np[-2, :]) / res

    slope_rad = np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2))
    slope_deg = np.degrees(slope_rad)

    max_slope = float(slope_deg.max())
    avg_slope = float(slope_deg.mean())

    flat_count = int(np.sum(slope_deg <= 15))
    moderate_count = int(np.sum((slope_deg > 15) & (slope_deg <= 30)))
    steep_count = int(np.sum(slope_deg > 30))
    total = slope_deg.size

    return {
        'layer_type': 'slope_map',
        'human': {
            'grid': _grid_to_list(slope_deg, 1),
            'grid_size_m': res,
            'cols': cols_count,
            'rows': rows_count,
            'color_scale': ['#2b8c2b', '#ffe135', '#ff8c00', '#ff0000'],
            'color_breaks': [0, 15, 30, 45],
            'legend': 'Slope (degrees): green=flat, red=steep',
        },
        'llm': {
            'layer_type': 'slope_map',
            'grid_size_m': res,
            'map_size': [game_map.size_x, game_map.size_z],
            'max_slope_deg': round(max_slope, 1),
            'avg_slope_deg': round(avg_slope, 1),
            'terrain_breakdown': {
                'gentle_pct': round(flat_count / total * 100, 1) if total else 0,
                'moderate_pct': round(moderate_count / total * 100, 1) if total else 0,
                'steep_pct': round(steep_count / total * 100, 1) if total else 0,
            },
            'zones': _zone_summary(slope_deg, res, game_map.size_x, game_map.size_z, label='slope_deg'),
            'terrain_features': _find_terrain_features(np.array(hg, dtype=np.float32), res),
        },
    }


# ---------------------------------------------------------------------------
# P3: Water Bodies Layer
# ---------------------------------------------------------------------------

def water_bodies(
    game_map: GameMap,
) -> dict[str, Any]:
    wg = game_map.water_grid_data
    if not wg:
        return {'layer_type': 'water_bodies', 'human': None, 'llm': None}

    res = game_map.water_grid_resolution or 200
    rows_count = len(wg)
    cols_count = len(wg[0]) if wg else 0

    type_grid: list[list[int]] = []
    depth_grid: list[list[float]] = []
    ford_grid: list[list[int]] = []

    ocean_cells = 0
    pond_cells = 0
    river_cells = 0
    total_water = 0
    fordable_cells = 0
    swim_cells = 0
    max_depth = 0.0

    for row in wg:
        type_row: list[int] = []
        depth_row: list[float] = []
        ford_row: list[int] = []
        for cell in row:
            if not cell or not isinstance(cell, list):
                type_row.append(0)
                depth_row.append(0)
                ford_row.append(0)
                continue

            if len(cell) >= 3:
                wt, depth = cell[0], cell[1]
            elif len(cell) == 2:
                is_water, depth = cell[0], cell[1]
                wt = 1 if is_water else 0
            else:
                type_row.append(0)
                depth_row.append(0)
                ford_row.append(0)
                continue

            type_row.append(int(wt))
            depth_row.append(float(depth))

            if wt > 0:
                total_water += 1
                if depth > max_depth:
                    max_depth = depth
                if depth < SWIM_DEPTH_THRESHOLD:
                    ford_row.append(1)
                    fordable_cells += 1
                else:
                    ford_row.append(2)
                    swim_cells += 1

                if wt == 1:
                    ocean_cells += 1
                elif wt == 2:
                    pond_cells += 1
                elif wt == 3:
                    river_cells += 1
            else:
                ford_row.append(0)

        type_grid.append(type_row)
        depth_grid.append(depth_row)
        ford_grid.append(ford_row)

    total_cells = rows_count * cols_count
    cell_area_km2 = (res * res) / 1_000_000

    return {
        'layer_type': 'water_bodies',
        'human': {
            'type_grid': type_grid,
            'depth_grid': depth_grid,
            'ford_grid': ford_grid,
            'grid_size_m': res,
            'cols': cols_count,
            'rows': rows_count,
            'type_colors': {0: 'transparent', 1: '#1565C0', 2: '#42A5F5', 3: '#29B6F6'},
            'depth_color_scale': ['#B3E5FC', '#0288D1', '#01579B'],
            'ford_colors': {0: 'transparent', 1: '#81D4FA', 2: '#0D47A1'},
            'legend': 'Water: blue=ocean, light blue=pond/lake, cyan=river. Ford: light=wadeable, dark=swim',
        },
        'llm': {
            'layer_type': 'water_bodies',
            'grid_size_m': res,
            'map_size': [game_map.size_x, game_map.size_z],
            'swim_depth_threshold_m': SWIM_DEPTH_THRESHOLD,
            'max_depth_m': round(max_depth, 2),
            'water_coverage_pct': round(total_water / total_cells * 100, 2) if total_cells else 0,
            'water_area_km2': round(total_water * cell_area_km2, 2),
            'breakdown': {
                'ocean_cells': ocean_cells,
                'pond_cells': pond_cells,
                'river_cells': river_cells,
            },
            'fordability': {
                'fordable_cells': fordable_cells,
                'swim_cells': swim_cells,
                'fordable_area_km2': round(fordable_cells * cell_area_km2, 2),
                'swim_area_km2': round(swim_cells * cell_area_km2, 2),
            },
            'zones': _zone_summary(
                np.array([[1.0 if t > 0 else 0.0 for t in row] for row in type_grid], dtype=np.float32),
                res, game_map.size_x, game_map.size_z, label='water',
            ),
        },
    }


# ---------------------------------------------------------------------------
# P4: Viewshed Analysis Layer
# ---------------------------------------------------------------------------

def viewshed(
    game_map: GameMap,
    observer_x: float,
    observer_z: float,
    observer_height: float = 1.8,
    max_range: float = 2000,
) -> dict[str, Any]:
    hg = game_map.height_grid_data
    if not hg:
        return {'layer_type': 'viewshed', 'human': None, 'llm': None}

    res = game_map.height_grid_resolution or 100
    hg_np = np.array(hg, dtype=np.float32)
    rows_count, cols_count = hg_np.shape

    obs_c = int(observer_x / res)
    obs_r = int(observer_z / res)
    if not (0 <= obs_c < cols_count and 0 <= obs_r < rows_count):
        return {'layer_type': 'viewshed', 'human': None, 'llm': {'error': 'observer out of bounds'}}

    obs_elev = float(hg_np[obs_r, obs_c]) + observer_height
    range_cells = int(max_range / res)

    min_r = max(0, obs_r - range_cells)
    max_r = min(rows_count - 1, obs_r + range_cells)
    min_c = max(0, obs_c - range_cells)
    max_c = min(cols_count - 1, obs_c + range_cells)

    vis_width = max_c - min_c + 1
    vis_height = max_r - min_r + 1
    vis_grid = np.zeros((vis_height, vis_width), dtype=np.int8)

    visible_count = 0
    total_checked = 0

    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            dx = (c - obs_c) * res
            dz = (r - obs_r) * res
            dist = math.sqrt(dx * dx + dz * dz)
            if dist > max_range:
                continue
            if dist < 1:
                vis_grid[r - min_r, c - min_c] = 1
                visible_count += 1
                total_checked += 1
                continue

            total_checked += 1
            if _is_visible_np(hg_np, obs_r, obs_c, obs_elev, r, c, res, cols_count, rows_count):
                vis_grid[r - min_r, c - min_c] = 1
                visible_count += 1

    coverage = visible_count / total_checked * 100 if total_checked else 0

    return {
        'layer_type': 'viewshed',
        'human': {
            'grid': vis_grid.tolist(),
            'grid_size_m': res,
            'cols': vis_width,
            'rows': vis_height,
            'origin': [min_c * res, min_r * res],
            'observer': [observer_x, observer_z],
            'colors': {0: 'rgba(255,0,0,0.3)', 1: 'rgba(0,255,0,0.3)'},
            'legend': 'Green=visible, Red=not visible',
        },
        'llm': {
            'layer_type': 'viewshed',
            'observer': [observer_x, observer_z],
            'observer_height_m': observer_height,
            'max_range_m': max_range,
            'coverage_pct': round(coverage, 1),
            'visible_cells': visible_count,
            'total_cells': total_checked,
            'grid_data': vis_grid.tolist(),
        },
    }


def _is_visible_np(
    hg_np: np.ndarray,
    obs_r: int, obs_c: int, obs_elev: float,
    tgt_r: int, tgt_c: int,
    res: float, cols: int, rows: int
) -> bool:
    dr = tgt_r - obs_r
    dc = tgt_c - obs_c
    steps = max(abs(dr), abs(dc))
    if steps == 0:
        return True

    r_step = dr / steps
    c_step = dc / steps

    dist_total = math.sqrt((dr * res) ** 2 + (dc * res) ** 2)
    tgt_elev = float(hg_np[tgt_r, tgt_c])
    slope_to_target = (tgt_elev - obs_elev) / dist_total if dist_total > 0 else 0

    max_slope = -float('inf')
    for i in range(1, steps):
        cr = int(round(obs_r + r_step * i))
        cc = int(round(obs_c + c_step * i))
        if not (0 <= cr < rows and 0 <= cc < cols):
            continue
        cell_elev = float(hg_np[cr, cc])
        dist = math.sqrt(((cr - obs_r) * res) ** 2 + ((cc - obs_c) * res) ** 2)
        if dist < 1:
            continue
        slope = (cell_elev - obs_elev) / dist
        if slope > max_slope:
            max_slope = slope

    return slope_to_target >= max_slope


# ---------------------------------------------------------------------------
# P4: Line of Sight Layer
# ---------------------------------------------------------------------------

def line_of_sight(
    game_map: GameMap,
    from_x: float, from_z: float,
    to_x: float, to_z: float,
    observer_height: float = 1.8,
) -> dict[str, Any]:
    hg = game_map.height_grid_data
    if not hg:
        return {'layer_type': 'line_of_sight', 'human': None, 'llm': None}

    res = game_map.height_grid_resolution or 100
    hg_np = np.array(hg, dtype=np.float32)
    rows_count, cols_count = hg_np.shape

    from_c, from_r = int(from_x / res), int(from_z / res)
    to_c, to_r = int(to_x / res), int(to_z / res)

    if not (0 <= from_c < cols_count and 0 <= from_r < rows_count):
        return {'layer_type': 'line_of_sight', 'human': None, 'llm': {'error': 'from point out of bounds'}}
    if not (0 <= to_c < cols_count and 0 <= to_r < rows_count):
        return {'layer_type': 'line_of_sight', 'human': None, 'llm': {'error': 'to point out of bounds'}}

    obs_elev = float(hg_np[from_r, from_c]) + observer_height
    tgt_elev = float(hg_np[to_r, to_c])

    dr = to_r - from_r
    dc = to_c - from_c
    steps = max(abs(dr), abs(dc))
    if steps == 0:
        return {
            'layer_type': 'line_of_sight',
            'human': {'visible': True, 'profile': [], 'from': [from_x, from_z], 'to': [to_x, to_z]},
            'llm': {'visible': True, 'distance_m': 0},
        }

    r_step = dr / steps
    c_step = dc / steps

    profile: list[dict] = []
    obstruction = None
    total_dist = math.sqrt((dr * res) ** 2 + (dc * res) ** 2)
    max_slope = -float('inf')

    for i in range(steps + 1):
        cr = int(round(from_r + r_step * i))
        cc = int(round(from_c + c_step * i))
        if not (0 <= cr < rows_count and 0 <= cc < cols_count):
            continue
        cell_elev = float(hg_np[cr, cc])
        dist = math.sqrt(((cr - from_r) * res) ** 2 + ((cc - from_c) * res) ** 2)

        los_height = obs_elev + (tgt_elev - obs_elev) * (dist / total_dist) if total_dist > 0 else obs_elev

        profile.append({
            'distance_m': round(dist, 1),
            'terrain_elev': round(cell_elev, 1),
            'los_height': round(los_height, 1),
            'world_pos': [round(cc * res, 1), round(cr * res, 1)],
        })

        if i > 0 and dist > 1:
            slope = (cell_elev - obs_elev) / dist
            if slope > max_slope:
                max_slope = slope
                if cell_elev > los_height and not obstruction:
                    obstruction = {
                        'world_pos': [round(cc * res, 1), round(cr * res, 1)],
                        'distance_m': round(dist, 1),
                        'terrain_elev': round(cell_elev, 1),
                        'los_height': round(los_height, 1),
                    }

    visible = obstruction is None

    return {
        'layer_type': 'line_of_sight',
        'human': {
            'visible': visible,
            'profile': profile,
            'from': [from_x, from_z],
            'to': [to_x, to_z],
            'obstruction': obstruction,
            'color': '#00C853' if visible else '#FF1744',
        },
        'llm': {
            'layer_type': 'line_of_sight',
            'from': [from_x, from_z],
            'to': [to_x, to_z],
            'distance_m': round(total_dist, 1),
            'visible': visible,
            'obstruction': obstruction,
            'observer_height_m': observer_height,
        },
    }


# ---------------------------------------------------------------------------
# P1: Trafficability Layer (NumPy vectorized)
# ---------------------------------------------------------------------------

async def trafficability(
    db: AsyncSession, game_map: GameMap, cell_size: float = 100
) -> dict[str, Any]:
    ck = _cache_key(game_map.id, 'trafficability', cell_size=cell_size)
    cached = _cache_get(ck)
    if cached:
        return cached

    hg = game_map.height_grid_data
    wg = game_map.water_grid_data
    hg_res = game_map.height_grid_resolution or 100

    cols, rows = _grid_coords(game_map.size_x, game_map.size_z, cell_size)
    score = np.ones((rows, cols), dtype=np.float32)

    if hg:
        hg_np = np.array(hg, dtype=np.float32)
        hg_rows, hg_cols = hg_np.shape

        ri = np.arange(rows)
        ci = np.arange(cols)
        ci_grid, ri_grid = np.meshgrid(ci, ri)
        hg_ci = np.clip((ci_grid * cell_size / hg_res).astype(np.int32), 0, hg_cols - 1)
        hg_ri = np.clip((ri_grid * cell_size / hg_res).astype(np.int32), 0, hg_rows - 1)

        dzdx = np.zeros_like(hg_np)
        dzdy = np.zeros_like(hg_np)
        dzdx[:, 1:-1] = (hg_np[:, 2:] - hg_np[:, :-2]) / (2 * hg_res)
        dzdy[1:-1, :] = (hg_np[2:, :] - hg_np[:-2, :]) / (2 * hg_res)

        slope_full = np.degrees(np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2)))
        slope_sampled = slope_full[hg_ri, hg_ci]

        slope_factor = np.ones_like(slope_sampled)
        slope_factor[slope_sampled > 45] = 0.0
        slope_factor[(slope_sampled > 30) & (slope_sampled <= 45)] = 0.2
        slope_factor[(slope_sampled > 15) & (slope_sampled <= 30)] = 0.6
        score *= slope_factor

    if wg:
        wg_res = game_map.water_grid_resolution or 200
        wg_np = np.array(wg, dtype=np.float32) if isinstance(wg[0][0], (int, float)) else None
        if wg_np is None:
            for r in range(rows):
                for c in range(cols):
                    wg_c = min(int(c * cell_size / wg_res), len(wg[0]) - 1)
                    wg_r = min(int(r * cell_size / wg_res), len(wg) - 1)
                    cell = wg[wg_r][wg_c]
                    if cell and isinstance(cell, list) and len(cell) >= 2:
                        depth = cell[1]
                        is_water = cell[0] > 0 if len(cell) >= 3 else cell[0]
                        if is_water:
                            if depth >= SWIM_DEPTH_THRESHOLD:
                                score[r, c] *= 0.05
                            elif depth >= 1.0:
                                score[r, c] *= 0.3
                            elif depth >= 0.5:
                                score[r, c] *= 0.6

    grouped = await _entity_positions_grouped(db, game_map.id)
    veg_positions = _positions_for_categories(grouped, ['tree', 'bush', 'vegetation'])
    veg_grid, _, _ = _density_grid_np(veg_positions, game_map.size_x, game_map.size_z, cell_size)
    veg_norm = _normalize_grid_np(veg_grid)

    veg_factor = np.ones_like(score)
    veg_factor[veg_norm > 0.8] = 0.4
    veg_factor[(veg_norm > 0.5) & (veg_norm <= 0.8)] = 0.7
    score *= veg_factor

    score = np.round(score, 3)

    easy = int(np.sum(score > 0.7))
    moderate = int(np.sum((score > 0.3) & (score <= 0.7)))
    difficult = int(np.sum((score > 0) & (score <= 0.3)))
    impassable = int(np.sum(score == 0))
    total = score.size

    result = {
        'layer_type': 'trafficability',
        'human': {
            'grid': _grid_to_list(score),
            'grid_size_m': cell_size,
            'cols': cols,
            'rows': rows,
            'color_scale': ['#B71C1C', '#FF6F00', '#FDD835', '#4CAF50'],
            'color_breaks': [0, 0.3, 0.7, 1.0],
            'legend': 'Trafficability: red=impassable, green=easy',
        },
        'llm': {
            'layer_type': 'trafficability',
            'grid_size_m': cell_size,
            'map_size': [game_map.size_x, game_map.size_z],
            'terrain_breakdown_pct': {
                'easy': round(easy / total * 100, 1) if total else 0,
                'moderate': round(moderate / total * 100, 1) if total else 0,
                'difficult': round(difficult / total * 100, 1) if total else 0,
                'impassable': round(impassable / total * 100, 1) if total else 0,
            },
            'zones': _zone_summary(score, cell_size, game_map.size_x, game_map.size_z, label='trafficability'),
            'easy_corridors': _find_corridors(score, cell_size, low_threshold=0.7, min_length=3, above=True),
        },
    }
    _cache_set(ck, result)
    return result


# ---------------------------------------------------------------------------
# P5: Cover & Concealment Layer
# ---------------------------------------------------------------------------

async def cover_concealment(
    db: AsyncSession, game_map: GameMap, cell_size: float = 100
) -> dict[str, Any]:
    ck = _cache_key(game_map.id, 'cover', cell_size=cell_size)
    cached = _cache_get(ck)
    if cached:
        return cached

    cols, rows = _grid_coords(game_map.size_x, game_map.size_z, cell_size)
    score_grid = np.zeros((rows, cols), dtype=np.float32)

    cover_categories = {
        'building': 1.0, 'building_residential': 1.0, 'building_commercial': 1.0,
        'building_industrial': 1.0, 'building_public': 1.0, 'building_military': 1.0,
        'fortification': 1.0, 'ruin': 0.7,
        'fence': 0.3, 'structure': 0.5,
        'rock': 0.6, 'cliff': 0.8,
        'tree': 0.5, 'bush': 0.4, 'vegetation': 0.2,
    }

    grouped = await _entity_positions_grouped(db, game_map.id)

    for cat, weight in cover_categories.items():
        positions = grouped.get(cat, [])
        if not positions:
            continue
        arr = np.array(positions, dtype=np.float32)
        ci = np.clip((arr[:, 0] / cell_size).astype(np.int32), 0, cols - 1)
        ri = np.clip((arr[:, 1] / cell_size).astype(np.int32), 0, rows - 1)
        np.add.at(score_grid, (ri, ci), weight)

    norm_grid = _normalize_grid_np(score_grid)

    good_cover = int(np.sum(norm_grid > 0.6))
    partial = int(np.sum((norm_grid > 0.2) & (norm_grid <= 0.6)))
    exposed = int(np.sum(norm_grid <= 0.2))
    total = norm_grid.size

    result = {
        'layer_type': 'cover_concealment',
        'human': {
            'grid': _grid_to_list(norm_grid),
            'grid_size_m': cell_size,
            'cols': cols,
            'rows': rows,
            'color_scale': ['#FFEBEE', '#A5D6A7', '#2E7D32', '#1B5E20'],
            'legend': 'Cover: light=exposed, dark green=good cover',
        },
        'llm': {
            'layer_type': 'cover_concealment',
            'grid_size_m': cell_size,
            'map_size': [game_map.size_x, game_map.size_z],
            'terrain_breakdown_pct': {
                'good_cover': round(good_cover / total * 100, 1) if total else 0,
                'partial_cover': round(partial / total * 100, 1) if total else 0,
                'exposed': round(exposed / total * 100, 1) if total else 0,
            },
            'zones': _zone_summary(norm_grid, cell_size, game_map.size_x, game_map.size_z, label='cover'),
            'cover_corridors': _find_corridors(norm_grid, cell_size, low_threshold=0.6, min_length=3, above=True),
            'exposed_corridors': _find_corridors(norm_grid, cell_size, low_threshold=0.1, min_length=3),
        },
    }
    _cache_set(ck, result)
    return result


# ---------------------------------------------------------------------------
# P1: Hillshade Layer (NumPy vectorized)
# ---------------------------------------------------------------------------

def hillshade(
    game_map: GameMap,
    azimuth: float = 315,
    altitude: float = 45,
) -> dict[str, Any]:
    hg = game_map.height_grid_data
    if not hg:
        return {'layer_type': 'hillshade', 'human': None, 'llm': None}

    res = game_map.height_grid_resolution or 100
    hg_np = np.array(hg, dtype=np.float32)
    rows_count, cols_count = hg_np.shape
    if rows_count < 3 or cols_count < 3:
        return {'layer_type': 'hillshade', 'human': None, 'llm': None}

    az_rad = np.radians(360 - azimuth + 90)
    alt_rad = np.radians(altitude)

    padded = np.pad(hg_np, 1, mode='edge')

    dzdx = (
        (padded[:-2, 2:] + 2 * padded[1:-1, 2:] + padded[2:, 2:])
        - (padded[:-2, :-2] + 2 * padded[1:-1, :-2] + padded[2:, :-2])
    ) / (8 * res)

    dzdy = (
        (padded[2:, :-2] + 2 * padded[2:, 1:-1] + padded[2:, 2:])
        - (padded[:-2, :-2] + 2 * padded[:-2, 1:-1] + padded[:-2, 2:])
    ) / (8 * res)

    slope = np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2))
    aspect = np.arctan2(-dzdy, dzdx)

    shade = (
        np.cos(alt_rad) * np.cos(slope)
        + np.sin(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    )
    shade = np.clip(shade, 0, 1)

    return {
        'layer_type': 'hillshade',
        'human': {
            'grid': _grid_to_list(shade),
            'grid_size_m': res,
            'cols': cols_count,
            'rows': rows_count,
            'color_scale': ['#000000', '#ffffff'],
            'legend': 'Hillshade: dark=shadow, bright=sunlit',
        },
        'llm': {
            'layer_type': 'hillshade',
            'azimuth_deg': azimuth,
            'altitude_deg': altitude,
            'resolution_m': res,
        },
    }


# ---------------------------------------------------------------------------
# P7: MCOO (Modified Combined Obstacle Overlay)
# ---------------------------------------------------------------------------

async def mcoo(
    db: AsyncSession,
    game_map: GameMap,
    cell_size: float = 100,
) -> dict[str, Any]:
    traffic_data = await trafficability(db, game_map, cell_size)
    cover_data = await cover_concealment(db, game_map, cell_size)
    slope_data = slope_map(game_map)

    cols, rows = _grid_coords(game_map.size_x, game_map.size_z, cell_size)

    t_human = traffic_data.get('human')
    c_human = cover_data.get('human')
    s_human = slope_data.get('human')

    t_grid = np.array(t_human['grid'], dtype=np.float32) if t_human and t_human.get('grid') else np.full((rows, cols), 0.5, dtype=np.float32)
    c_grid = np.array(c_human['grid'], dtype=np.float32) if c_human and c_human.get('grid') else np.zeros((rows, cols), dtype=np.float32)

    hg_res = game_map.height_grid_resolution or 100
    if s_human and s_human.get('grid'):
        s_np = np.array(s_human['grid'], dtype=np.float32)
        s_rows, s_cols = s_np.shape
        ri = np.arange(rows)
        ci = np.arange(cols)
        ci_g, ri_g = np.meshgrid(ci, ri)
        sri = np.clip((ri_g * cell_size / hg_res).astype(np.int32), 0, s_rows - 1)
        sci = np.clip((ci_g * cell_size / hg_res).astype(np.int32), 0, s_cols - 1)
        s_sampled = 1.0 - np.clip(s_np[sri, sci] / 45.0, 0, 1)
    else:
        s_sampled = np.zeros((rows, cols), dtype=np.float32)

    composite = t_grid * 0.5 + s_sampled * 0.3 + (1.0 - c_grid) * 0.2

    mcoo_grid = np.where(composite >= 0.7, 0, np.where(composite >= 0.3, 1, 2)).astype(np.float32)

    total = mcoo_grid.size or 1
    unrestricted = int(np.sum(mcoo_grid == 0))
    restricted = int(np.sum(mcoo_grid == 1))
    severely = int(np.sum(mcoo_grid == 2))

    return {
        'layer_type': 'mcoo',
        'human': {
            'grid': _grid_to_list(mcoo_grid, 0),
            'grid_size_m': cell_size,
            'cols': cols,
            'rows': rows,
            'color_scale': ['#4CAF50', '#FFC107', '#F44336'],
            'color_breaks': [0, 1, 2],
            'legend': 'MCOO: green=unrestricted, yellow=restricted, red=severely restricted',
        },
        'llm': {
            'layer_type': 'mcoo',
            'grid_size_m': cell_size,
            'map_size': [game_map.size_x, game_map.size_z],
            'terrain_pct': {
                'unrestricted': round(unrestricted / total * 100, 1),
                'restricted': round(restricted / total * 100, 1),
                'severely_restricted': round(severely / total * 100, 1),
            },
            'zones': _zone_summary(
                2.0 - mcoo_grid,
                cell_size, game_map.size_x, game_map.size_z, label='mobility',
            ),
        },
    }
