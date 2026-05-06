"""Military-style base map tile renderer (NumPy-accelerated).

Generates topographic base-layer tiles from game data (height grid, water
grid, entity density).  Roads, landmarks, and grid lines are rendered by
the frontend Leaflet layers and are NOT baked into tiles.

Tile output: 256x256 PNG at zoom levels 0..MAX_ZOOM, stored alongside
satellite tiles so the existing Leaflet viewer can consume them.
"""

from __future__ import annotations

import logging
import math
import os
import shutil
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from backend.app.map.model.map import GameMap

log = logging.getLogger(__name__)

TILE_SIZE = 256
MAX_ZOOM = 5
TILE_STEP_SIZE = 100  # game units per tile at the most detailed zoom (matches frontend CRS)

# ── Color palette (military topo style) ─────────────────────────────────────

_ELEV_COLORS = np.array([
    [172, 218, 172],  # lowland green
    [185, 225, 178],  # light green
    [200, 230, 185],  # yellow-green
    [218, 235, 192],  # pale yellow-green
    [232, 235, 195],  # cream
    [240, 230, 190],  # light tan
    [225, 210, 175],  # tan
    [210, 190, 160],  # brown
    [195, 175, 155],  # grey-brown
    [185, 180, 175],  # grey
    [200, 200, 200],  # light grey
    [225, 225, 225],  # near white
], dtype=np.float32)

_ELEV_RATIOS = np.array(
    [0.0, 0.017, 0.033, 0.067, 0.1, 0.133, 0.2, 0.267, 0.4, 0.533, 0.667, 1.0],
    dtype=np.float32,
)


def _compute_adaptive_breaks(
    height_grid: np.ndarray,
    ocean_mask: np.ndarray | None,
) -> np.ndarray:
    """Compute elevation color breaks adaptive to the map's actual terrain range.

    Uses P2/P98 percentiles of non-ocean land pixels so that edge buffer zones
    (often 0m) and extreme peaks don't skew the color distribution.
    """
    land = height_grid.ravel()
    if ocean_mask is not None:
        land = land[~ocean_mask.ravel()]
    if land.size == 0:
        return (_ELEV_RATIOS * 500.0).astype(np.float32)

    elev_low = float(np.percentile(land, 2))
    elev_high = float(np.percentile(land, 98))

    if elev_high - elev_low < 5.0:
        elev_low = max(0.0, elev_low - 2.5)
        elev_high = elev_low + 5.0

    elev_range = elev_high - elev_low
    return (elev_low + _ELEV_RATIOS * elev_range).astype(np.float32)

WATER_COLORS = {
    0: None,
    1: (120, 175, 205),   # ocean — deep blue
    2: (145, 195, 218),   # pond/lake — medium blue
    3: (165, 205, 225),   # river — lighter blue
}
WATER_EDGE_COLOR = np.array([60, 110, 155], dtype=np.float32)

VEGETATION_COLOR_LO = np.array([160, 200, 150], dtype=np.float32)
VEGETATION_COLOR_HI = np.array([100, 160, 100], dtype=np.float32)

BUILDING_COLOR_LO = np.array([220, 210, 205], dtype=np.float32)
BUILDING_COLOR_HI = np.array([195, 180, 175], dtype=np.float32)

BUILDING_CATEGORIES = frozenset([
    'building', 'building_residential', 'building_commercial',
    'building_industrial', 'building_public', 'building_military',
])
VEGETATION_CATEGORIES = frozenset(['tree', 'bush', 'vegetation'])



def _vectorized_elevation_color(
    heights: np.ndarray,
    elev_breaks: np.ndarray,
) -> np.ndarray:
    """Map a 2D height array to RGB colors using adaptive elevation breaks."""
    h = heights.astype(np.float32)
    indices = np.searchsorted(elev_breaks, h, side='right') - 1
    indices = np.clip(indices, 0, len(elev_breaks) - 2)

    lo_e = elev_breaks[indices]
    hi_e = elev_breaks[indices + 1]
    denom = hi_e - lo_e
    denom[denom == 0] = 1
    t = np.clip((h - lo_e) / denom, 0, 1)

    lo_c = _ELEV_COLORS[indices]
    hi_c = _ELEV_COLORS[indices + 1]
    t_3d = t[..., np.newaxis]
    rgb = lo_c * (1 - t_3d) + hi_c * t_3d
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _parse_water_type_grid_mil(wg_raw: list) -> np.ndarray | None:
    """Parse water grid data into a 2D int32 array of water types.

    Handles both 3-element cells [waterType, depth, lakeArea] and
    2-element cells [isWater, depth] from different scanner versions.
    """
    if not wg_raw:
        return None
    rows = len(wg_raw)
    cols = len(wg_raw[0]) if wg_raw else 0
    if rows == 0 or cols == 0:
        return None
    grid = np.zeros((rows, cols), dtype=np.int32)
    for r, row in enumerate(wg_raw):
        for c, cell in enumerate(row):
            if not cell:
                continue
            if isinstance(cell, list):
                if len(cell) >= 3:
                    grid[r, c] = int(cell[0])
                elif len(cell) == 2:
                    grid[r, c] = 1 if cell[0] else 0
                elif len(cell) == 1:
                    grid[r, c] = int(cell[0])
            elif isinstance(cell, (int, float)):
                grid[r, c] = int(cell)
    return grid


def _build_ocean_mask(
    height_grid: np.ndarray, height_res: int,
    size_x: float, size_z: float,
    sea_level: float = 0.5,
) -> np.ndarray:
    """Flood-fill from map edges to find ocean cells in the height grid.

    Returns a boolean array (same shape as height_grid) where True = ocean.
    Ocean is defined as contiguous low-elevation (<=sea_level) cells reachable
    from any edge of the map.
    """
    from collections import deque

    rows, cols = height_grid.shape
    ocean = np.zeros((rows, cols), dtype=bool)
    visited = np.zeros((rows, cols), dtype=bool)

    queue: deque[tuple[int, int]] = deque()

    for r in range(rows):
        for c in [0, cols - 1]:
            if height_grid[r, c] <= sea_level:
                queue.append((r, c))
                visited[r, c] = True
    for c in range(cols):
        for r in [0, rows - 1]:
            if not visited[r, c] and height_grid[r, c] <= sea_level:
                queue.append((r, c))
                visited[r, c] = True

    while queue:
        r, c = queue.popleft()
        ocean[r, c] = True
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc_ = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc_ < cols and not visited[nr, nc_]:
                visited[nr, nc_] = True
                if height_grid[nr, nc_] <= sea_level:
                    queue.append((nr, nc_))

    return ocean


def _render_tile_numpy(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    height_grid: np.ndarray | None, height_res: int,
    water_grid: np.ndarray | None, water_res: int,
    ocean_mask: np.ndarray | None,
    building_density: np.ndarray | None, bld_cell: float,
    vegetation_density: np.ndarray | None, veg_cell: float,
    max_elevation: float,
    elev_breaks: np.ndarray | None = None,
    tile_step_size: int = TILE_STEP_SIZE,
) -> Image.Image:
    """Render a single tile using NumPy vectorized operations."""
    world_per_tile = tile_step_size * (2 ** tile_zoom)
    world_per_tile_x = float(world_per_tile)
    world_per_tile_z = float(world_per_tile)
    tile_world_x0 = tile_x * world_per_tile_x
    tile_world_z0 = tile_y * world_per_tile_z

    # Pixel coordinate grids
    px_range = np.arange(TILE_SIZE, dtype=np.float32)
    py_range = np.arange(TILE_SIZE, dtype=np.float32)
    px_grid, py_grid = np.meshgrid(px_range, py_range)

    wx = tile_world_x0 + (px_grid / TILE_SIZE) * world_per_tile_x
    wz = tile_world_z0 + ((TILE_SIZE - 1 - py_grid) / TILE_SIZE) * world_per_tile_z

    out_of_bounds = (wx < 0) | (wx > size_x) | (wz < 0) | (wz > size_z)

    # 1) Sample height with bilinear interpolation for smooth elevation transitions
    if height_grid is not None:
        h_rows, h_cols = height_grid.shape
        fz = wz / height_res
        fx = wx / height_res
        r0 = np.clip(np.floor(fz).astype(np.int32), 0, h_rows - 1)
        r1 = np.clip(r0 + 1, 0, h_rows - 1)
        c0 = np.clip(np.floor(fx).astype(np.int32), 0, h_cols - 1)
        c1 = np.clip(c0 + 1, 0, h_cols - 1)
        tz = np.clip(fz - np.floor(fz), 0, 1)
        tx = np.clip(fx - np.floor(fx), 0, 1)

        h00 = height_grid[r0, c0]
        h01 = height_grid[r0, c1]
        h10 = height_grid[r1, c0]
        h11 = height_grid[r1, c1]
        heights = h00 * (1 - tz) * (1 - tx) + h01 * (1 - tz) * tx + h10 * tz * (1 - tx) + h11 * tz * tx
    else:
        heights = np.zeros((TILE_SIZE, TILE_SIZE), dtype=np.float32)

    # 2) Elevation color
    breaks = elev_breaks if elev_breaks is not None else (_ELEV_RATIOS * 500.0).astype(np.float32)
    rgb = _vectorized_elevation_color(heights, breaks).astype(np.float32)

    # 3) Hillshade (multi-directional Horn's method) using bilinear-sampled neighbors
    if height_grid is not None:
        fz_p = (wz + height_res) / height_res
        fz_m = (wz - height_res) / height_res
        fx_p = (wx + height_res) / height_res
        fx_m = (wx - height_res) / height_res

        def _bilerp(fzz: np.ndarray, fxx: np.ndarray) -> np.ndarray:
            rr0 = np.clip(np.floor(fzz).astype(np.int32), 0, h_rows - 1)
            rr1 = np.clip(rr0 + 1, 0, h_rows - 1)
            cc0 = np.clip(np.floor(fxx).astype(np.int32), 0, h_cols - 1)
            cc1 = np.clip(cc0 + 1, 0, h_cols - 1)
            ttz = np.clip(fzz - np.floor(fzz), 0, 1)
            ttx = np.clip(fxx - np.floor(fxx), 0, 1)
            return (height_grid[rr0, cc0] * (1 - ttz) * (1 - ttx)
                    + height_grid[rr0, cc1] * (1 - ttz) * ttx
                    + height_grid[rr1, cc0] * ttz * (1 - ttx)
                    + height_grid[rr1, cc1] * ttz * ttx)

        h_right = _bilerp(fz, fx_p)
        h_left = _bilerp(fz, fx_m)
        h_up = _bilerp(fz_p, fx)
        h_down = _bilerp(fz_m, fx)

        dzdx = (h_right - h_left) / (2.0 * height_res)
        dzdy = (h_up - h_down) / (2.0 * height_res)
        slope = np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2))
        aspect = np.arctan2(-dzdy, dzdx)

        lights = [(315, 45, 0.65), (270, 60, 0.25), (0, 70, 0.10)]
        shade_val = np.zeros_like(slope)
        for az_deg, alt_deg, weight in lights:
            az_rad = np.radians(360 - az_deg + 90)
            alt_rad = np.radians(alt_deg)
            s = np.cos(alt_rad) * np.cos(slope) + np.sin(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
            shade_val += np.clip(s, 0, 1) * weight

        shade = 0.55 + 0.45 * np.clip(shade_val, 0, 1)
        shade_3d = shade[..., np.newaxis]
        rgb *= shade_3d

    # 4) Water overlay: ocean (flood-fill from edges) + inland water (from water grid)
    water_mask_global = np.zeros((TILE_SIZE, TILE_SIZE), dtype=bool)

    # 4a) Ocean: sample the pre-computed ocean mask with bilinear interpolation
    #     (reuses fz/fx/r0/r1/c0/c1/tz/tx from height sampling in step 1)
    ocean_color = np.array(WATER_COLORS[1], dtype=np.float32)  # ocean color
    if ocean_mask is not None and height_grid is not None:
        ocean_f = ocean_mask.astype(np.float32)
        v00 = ocean_f[r0, c0]
        v01 = ocean_f[r0, c1]
        v10 = ocean_f[r1, c0]
        v11 = ocean_f[r1, c1]
        ocean_interp = v00 * (1 - tz) * (1 - tx) + v01 * (1 - tz) * tx + v10 * tz * (1 - tx) + v11 * tz * tx

        is_ocean = (ocean_interp > 0.5) & ~out_of_bounds

        # Smooth blend at coastline: pixels with 0.2 < ocean_interp < 0.8
        # get a gradual transition between land and water
        coast_blend = (ocean_interp > 0.2) & (ocean_interp <= 0.5) & ~out_of_bounds
        if np.any(coast_blend):
            blend_t = ((ocean_interp[coast_blend] - 0.2) / 0.3)[..., np.newaxis]
            rgb[coast_blend] = rgb[coast_blend] * (1 - blend_t) + ocean_color * blend_t

        if np.any(is_ocean):
            rgb[is_ocean] = ocean_color
            water_mask_global |= is_ocean

    # 4b) Inland water bodies: use water grid data for non-ocean areas
    if water_grid is not None:
        w_rows, w_cols = water_grid.shape[:2]
        wr = np.clip((wz / water_res).astype(np.int32), 0, w_rows - 1)
        wc = np.clip((wx / water_res).astype(np.int32), 0, w_cols - 1)
        water_type_int = water_grid[wr, wc]

        inland_water = (water_type_int > 0) & ~out_of_bounds & ~water_mask_global
        for wt, color in WATER_COLORS.items():
            if wt == 0 or color is None:
                continue
            mask = (water_type_int == wt) & inland_water
            if np.any(mask):
                rgb[mask] = np.array(color, dtype=np.float32)
        water_mask_global |= inland_water

    # 4c) Water edge detection
    if np.any(water_mask_global):
        edge_h = water_mask_global[:, :-1] != water_mask_global[:, 1:]
        edge_v = water_mask_global[:-1, :] != water_mask_global[1:, :]
        edge = np.zeros_like(water_mask_global)
        edge[:, :-1] |= edge_h
        edge[:, 1:] |= edge_h
        edge[:-1, :] |= edge_v
        edge[1:, :] |= edge_v
        edge &= ~out_of_bounds
        if np.any(edge):
            rgb[edge] = WATER_EDGE_COLOR

    # 5) Vegetation density blend (bilinear interpolation, skip water)
    if vegetation_density is not None:
        vr, vc = vegetation_density.shape
        vfz = wz / veg_cell
        vfx = wx / veg_cell
        vi0 = np.clip(np.floor(vfz).astype(np.int32), 0, vr - 1)
        vi1 = np.clip(vi0 + 1, 0, vr - 1)
        vj0 = np.clip(np.floor(vfx).astype(np.int32), 0, vc - 1)
        vj1 = np.clip(vj0 + 1, 0, vc - 1)
        vtz = np.clip(vfz - np.floor(vfz), 0, 1)
        vtx = np.clip(vfx - np.floor(vfx), 0, 1)
        veg = (vegetation_density[vi0, vj0] * (1 - vtz) * (1 - vtx)
               + vegetation_density[vi0, vj1] * (1 - vtz) * vtx
               + vegetation_density[vi1, vj0] * vtz * (1 - vtx)
               + vegetation_density[vi1, vj1] * vtz * vtx)
        veg_mask = (veg > 0.03) & ~water_mask_global
        if np.any(veg_mask):
            veg_clamped = np.clip(veg, 0, 1)
            veg_color = (VEGETATION_COLOR_LO[np.newaxis, np.newaxis, :] * (1 - veg_clamped[..., np.newaxis])
                         + VEGETATION_COLOR_HI[np.newaxis, np.newaxis, :] * veg_clamped[..., np.newaxis])
            blend_strength = np.clip(veg_clamped * 0.5 + 0.05, 0.05, 0.5)
            t_3d = blend_strength[..., np.newaxis]
            blended = rgb * (1 - t_3d) + veg_color * t_3d
            rgb = np.where(veg_mask[..., np.newaxis], blended, rgb)

    # 6) Building density blend (bilinear interpolation, skip water)
    if building_density is not None:
        br, bc = building_density.shape
        bfz = wz / bld_cell
        bfx = wx / bld_cell
        bi0 = np.clip(np.floor(bfz).astype(np.int32), 0, br - 1)
        bi1 = np.clip(bi0 + 1, 0, br - 1)
        bj0 = np.clip(np.floor(bfx).astype(np.int32), 0, bc - 1)
        bj1 = np.clip(bj0 + 1, 0, bc - 1)
        btz = np.clip(bfz - np.floor(bfz), 0, 1)
        btx = np.clip(bfx - np.floor(bfx), 0, 1)
        bld = (building_density[bi0, bj0] * (1 - btz) * (1 - btx)
               + building_density[bi0, bj1] * (1 - btz) * btx
               + building_density[bi1, bj0] * btz * (1 - btx)
               + building_density[bi1, bj1] * btz * btx)
        bld_mask = (bld > 0.03) & ~water_mask_global
        if np.any(bld_mask):
            bld_clamped = np.clip(bld, 0, 1)
            bld_color = (BUILDING_COLOR_LO[np.newaxis, np.newaxis, :] * (1 - bld_clamped[..., np.newaxis])
                         + BUILDING_COLOR_HI[np.newaxis, np.newaxis, :] * bld_clamped[..., np.newaxis])
            blend_strength = np.clip(bld_clamped * 0.45 + 0.05, 0.05, 0.45)
            t_3d = blend_strength[..., np.newaxis]
            blended = rgb * (1 - t_3d) + bld_color * t_3d
            rgb = np.where(bld_mask[..., np.newaxis], blended, rgb)

    # Out-of-bounds: dark blue-gray gradient with subtle noise
    if np.any(out_of_bounds):
        oob_base = np.array([45, 55, 70], dtype=np.float32)
        noise = np.random.default_rng(42).uniform(-8, 8, size=(TILE_SIZE, TILE_SIZE, 3)).astype(np.float32)
        oob_color = np.clip(oob_base + noise, 0, 255)
        rgb[out_of_bounds] = oob_color[out_of_bounds]

    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB')


def _render_and_save(args: dict) -> str:
    """Worker function for multiprocessing — renders one tile and saves to disk."""
    tile_img = _render_tile_numpy(**{k: v for k, v in args.items() if k != 'output_path'})
    out = args['output_path']
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tile_img.save(out, format='PNG', optimize=True, compress_level=6)
    return out


async def generate_military_tiles(
    db: Any,
    game_map: GameMap,
    output_dir: str,
    max_workers: int = 4,
    progress_callback: Any = None,
) -> dict:
    """Generate all military base map tiles for a GameMap.

    Uses NumPy for vectorized rendering and ThreadPoolExecutor for
    parallel tile generation.
    """
    from sqlalchemy import select
    from backend.app.map.model.map import MapEntity

    log.info('Generating military tiles for map %s (%s)', game_map.id, game_map.name)

    # ── Load height grid as numpy array ──
    height_grid_raw = game_map.height_grid_data
    if isinstance(height_grid_raw, dict) and 'grid' in height_grid_raw:
        height_grid_raw = height_grid_raw['grid']
    height_np = np.array(height_grid_raw, dtype=np.float32) if height_grid_raw else None
    height_res = game_map.height_grid_resolution or 100

    # ── Load water grid as 2D int array of water types ──
    water_grid_raw = game_map.water_grid_data
    if isinstance(water_grid_raw, dict) and 'grid' in water_grid_raw:
        water_grid_raw = water_grid_raw['grid']
    water_np = _parse_water_type_grid_mil(water_grid_raw) if water_grid_raw else None
    water_res = game_map.water_grid_resolution or 200

    if water_np is not None:
        total_cells = water_np.size
        water_cells = int((water_np > 0).sum())
        log.info('Water grid: %d×%d, %d/%d cells are water (%.1f%%)',
                 water_np.shape[0], water_np.shape[1],
                 water_cells, total_cells, 100.0 * water_cells / max(total_cells, 1))

    # ── Build entity density grids ──
    density_cell = 100
    cols = max(1, math.ceil(game_map.size_x / density_cell))
    rows = max(1, math.ceil(game_map.size_z / density_cell))

    building_grid = np.zeros((rows, cols), dtype=np.float32)
    vegetation_grid = np.zeros((rows, cols), dtype=np.float32)

    batch_size = 50000
    offset = 0
    while True:
        stmt = (
            select(MapEntity.category, MapEntity.position_x, MapEntity.position_z)
            .where(MapEntity.map_id == game_map.id)
            .offset(offset)
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        batch = result.all()
        if not batch:
            break

        for cat, ex, ez in batch:
            c = min(int(ex / density_cell), cols - 1)
            r = min(int(ez / density_cell), rows - 1)
            if 0 <= c < cols and 0 <= r < rows:
                if cat in BUILDING_CATEGORIES:
                    building_grid[r, c] += 1
                elif cat in VEGETATION_CATEGORIES:
                    vegetation_grid[r, c] += 1

        offset += batch_size
        if len(batch) < batch_size:
            break

    b_max = building_grid.max() or 1
    v_max = vegetation_grid.max() or 1
    building_grid /= b_max
    vegetation_grid /= v_max

    max_elev = game_map.max_elevation or game_map.max_elevation_precise or 500

    # ── Build ocean mask via flood-fill from map edges ──
    ocean_np = None
    if height_np is not None:
        ocean_np = _build_ocean_mask(height_np, height_res, game_map.size_x, game_map.size_z)
        ocean_cells = int(ocean_np.sum())
        log.info('Ocean mask: %d/%d cells are ocean (%.1f%%)',
                 ocean_cells, ocean_np.size, 100.0 * ocean_cells / max(ocean_np.size, 1))

    # ── Compute adaptive elevation color breaks ──
    elev_breaks = None
    if height_np is not None:
        elev_breaks = _compute_adaptive_breaks(height_np, ocean_np)
        log.info('Adaptive elevation breaks: %.1f ~ %.1f m (%d levels)',
                 elev_breaks[0], elev_breaks[-1], len(elev_breaks))

    tile_dir = os.path.join(output_dir, str(game_map.id), 'military_tiles')

    if os.path.isdir(tile_dir):
        log.info('Removing old military tiles at %s', tile_dir)
        shutil.rmtree(tile_dir)

    # ── Build task list ──
    # Tile grid must match the Leaflet CRS convention:
    #   At URL zoom z, each tile covers (TILE_STEP_SIZE * 2^z) game units.
    #   Number of tiles per side = ceil(map_size / (TILE_STEP_SIZE * 2^z)).
    tasks: list[dict] = []
    for zoom in range(MAX_ZOOM + 1):
        world_per_tile = TILE_STEP_SIZE * (2 ** zoom)
        tiles_x = max(1, math.ceil(game_map.size_x / world_per_tile))
        tiles_z = max(1, math.ceil(game_map.size_z / world_per_tile))
        log.info('Zoom %d: %d×%d tiles (each covers %dm)', zoom, tiles_x, tiles_z, world_per_tile)
        for tx in range(tiles_x):
            for ty in range(tiles_z):
                out_path = os.path.join(tile_dir, str(zoom), str(tx), str(ty), 'tile.png')
                tasks.append({
                    'tile_zoom': zoom, 'tile_x': tx, 'tile_y': ty,
                    'size_x': game_map.size_x, 'size_z': game_map.size_z,
                    'height_grid': height_np, 'height_res': height_res,
                    'water_grid': water_np, 'water_res': water_res,
                    'ocean_mask': ocean_np,
                    'building_density': building_grid, 'bld_cell': density_cell,
                    'vegetation_density': vegetation_grid, 'veg_cell': density_cell,
                    'max_elevation': max_elev,
                    'elev_breaks': elev_breaks,
                    'tile_step_size': TILE_STEP_SIZE,
                    'output_path': out_path,
                })

    log.info('Rendering %d tiles with %d workers...', len(tasks), max_workers)

    # ── Parallel rendering (non-blocking) ──
    total_tasks = len(tasks)
    map_id = game_map.id

    def _render_all():
        from backend.app.map.service.tile_progress import set_progress
        set_progress(map_id, 'military', 0, total_tasks)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_render_and_save, t): t for t in tasks}
            done = 0
            for future in as_completed(futures):
                future.result()
                done += 1
                if done % 10 == 0 or done == total_tasks:
                    set_progress(map_id, 'military', done, total_tasks)
                if done % 100 == 0:
                    log.info('Progress: %d / %d tiles', done, total_tasks)

    await asyncio.to_thread(_render_all)

    total_tiles = len(tasks)
    log.info('Military tile generation complete: %d tiles total', total_tiles)

    terrain_stats: dict = {}
    if ocean_np is not None:
        terrain_stats['ocean_percent'] = round(
            100.0 * float(ocean_np.sum()) / max(ocean_np.size, 1), 1,
        )
    if elev_breaks is not None:
        terrain_stats['elev_p2'] = round(float(elev_breaks[0]), 1)
        terrain_stats['elev_p98'] = round(float(elev_breaks[-1]), 1)

    return {
        'total_tiles': total_tiles,
        'zoom_levels': list(range(MAX_ZOOM + 1)),
        'tile_dir': tile_dir,
        'terrain_stats': terrain_stats,
    }
