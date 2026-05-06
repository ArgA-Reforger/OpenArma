"""Analysis layer tile renderer — transparent PNG tile pyramids.

Generates overlay tiles for thematic analysis layers (vegetation, slope,
hillshade, contours, water, trafficability, cover, mcoo, builtup).

Shares the same tile coordinate system as military_renderer.py:
  - TILE_SIZE = 256, MAX_ZOOM = 5, TILE_STEP_SIZE = 100
  - At zoom z, each tile covers (TILE_STEP_SIZE * 2^z) game units.

All output tiles are RGBA PNG with transparent backgrounds so they can
be overlaid on top of any base map via L.tileLayer.
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
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from backend.app.map.model.map import GameMap

log = logging.getLogger(__name__)

TILE_SIZE = 256
MAX_ZOOM = 5
TILE_STEP_SIZE = 100

ANALYSIS_LAYERS = (
    'vegetation', 'builtup', 'slope', 'hillshade',
    'contours', 'water', 'trafficability', 'cover', 'mcoo',
)

BUILDING_CATEGORIES = frozenset([
    'building', 'building_residential', 'building_commercial',
    'building_industrial', 'building_public', 'building_military',
])
VEGETATION_CATEGORIES = frozenset(['tree', 'bush', 'grass', 'vegetation'])
COVER_WEIGHTS: dict[str, float] = {
    'building': 1.0, 'building_residential': 1.0, 'building_commercial': 1.0,
    'building_industrial': 1.0, 'building_public': 1.0, 'building_military': 1.0,
    'fortification': 1.0, 'ruin': 0.7,
    'fence': 0.3, 'structure': 0.5,
    'rock': 0.6, 'cliff': 0.8,
    'tree': 0.5, 'bush': 0.4, 'vegetation': 0.2,
}

SWIM_DEPTH_THRESHOLD = 1.5


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _interpolate_color_scale(
    val: float, scale: list[str], breaks: list[float] | None = None,
) -> tuple[int, int, int]:
    """Map a 0..max value to an RGB color via a color scale."""
    n = len(scale)
    if breaks:
        for i in range(len(breaks) - 1):
            if val <= breaks[i + 1]:
                t = (val - breaks[i]) / max(breaks[i + 1] - breaks[i], 1e-6)
                t = max(0.0, min(1.0, t))
                r0, g0, b0 = _hex_to_rgb(scale[min(i, n - 1)])
                r1, g1, b1 = _hex_to_rgb(scale[min(i + 1, n - 1)])
                return (
                    int(r0 + (r1 - r0) * t),
                    int(g0 + (g1 - g0) * t),
                    int(b0 + (b1 - b0) * t),
                )
        return _hex_to_rgb(scale[-1])
    t = max(0.0, min(1.0, val))
    pos = t * (n - 1)
    idx = int(pos)
    frac = pos - idx
    if idx >= n - 1:
        return _hex_to_rgb(scale[-1])
    r0, g0, b0 = _hex_to_rgb(scale[idx])
    r1, g1, b1 = _hex_to_rgb(scale[idx + 1])
    return (
        int(r0 + (r1 - r0) * frac),
        int(g0 + (g1 - g0) * frac),
        int(b0 + (b1 - b0) * frac),
    )


# ---------------------------------------------------------------------------
# Tile coordinate helpers (identical to military_renderer)
# ---------------------------------------------------------------------------

def _tile_world_coords(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (wx, wz, out_of_bounds) arrays for a tile."""
    world_per_tile = float(TILE_STEP_SIZE * (2 ** tile_zoom))
    tile_world_x0 = tile_x * world_per_tile
    tile_world_z0 = tile_y * world_per_tile

    px = np.arange(TILE_SIZE, dtype=np.float32)
    py = np.arange(TILE_SIZE, dtype=np.float32)
    px_grid, py_grid = np.meshgrid(px, py)

    wx = tile_world_x0 + (px_grid / TILE_SIZE) * world_per_tile
    wz = tile_world_z0 + ((TILE_SIZE - 1 - py_grid) / TILE_SIZE) * world_per_tile
    oob = (wx < 0) | (wx > size_x) | (wz < 0) | (wz > size_z)
    return wx, wz, oob


def _sample_grid(
    wx: np.ndarray, wz: np.ndarray,
    grid: np.ndarray, grid_res: float,
) -> np.ndarray:
    """Sample a data grid at world coordinates (nearest-neighbor)."""
    g_rows, g_cols = grid.shape[:2]
    ri = np.clip((wz / grid_res).astype(np.int32), 0, g_rows - 1)
    ci = np.clip((wx / grid_res).astype(np.int32), 0, g_cols - 1)
    return grid[ri, ci]


def _sample_grid_bilinear(
    wx: np.ndarray, wz: np.ndarray,
    grid: np.ndarray, grid_res: float,
) -> np.ndarray:
    """Sample a float data grid at world coordinates with bilinear interpolation."""
    g_rows, g_cols = grid.shape[:2]
    fz = wz / grid_res
    fx = wx / grid_res
    r0 = np.clip(np.floor(fz).astype(np.int32), 0, g_rows - 1)
    r1 = np.clip(r0 + 1, 0, g_rows - 1)
    c0 = np.clip(np.floor(fx).astype(np.int32), 0, g_cols - 1)
    c1 = np.clip(c0 + 1, 0, g_cols - 1)
    tz = np.clip(fz - np.floor(fz), 0, 1)
    tx = np.clip(fx - np.floor(fx), 0, 1)
    return (grid[r0, c0] * (1 - tz) * (1 - tx)
            + grid[r0, c1] * (1 - tz) * tx
            + grid[r1, c0] * tz * (1 - tx)
            + grid[r1, c1] * tz * tx)


def _build_density_grid(
    positions: list[tuple[float, float]],
    size_x: float, size_z: float, cell_size: float,
) -> np.ndarray:
    cols = max(1, math.ceil(size_x / cell_size))
    rows = max(1, math.ceil(size_z / cell_size))
    if not positions:
        return np.zeros((rows, cols), dtype=np.float32)
    arr = np.array(positions, dtype=np.float32)
    ci = np.clip((arr[:, 0] / cell_size).astype(np.int32), 0, cols - 1)
    ri = np.clip((arr[:, 1] / cell_size).astype(np.int32), 0, rows - 1)
    grid = np.zeros((rows, cols), dtype=np.float32)
    np.add.at(grid, (ri, ci), 1)
    mx = grid.max()
    if mx > 0:
        grid /= mx
    return grid


def _assign_entities_via_grid(
    entities: list[tuple], tasks: list[dict],
    size_x: float, size_z: float,
    margin_min: float = 0.0,
) -> None:
    """Assign entities to tiles using a spatial grid index — O(N+M) instead of O(N*M).

    Builds a coarse grid (bucket_size = largest tile world span), hashes each
    entity into its bucket once, then each tile only checks relevant buckets.
    """
    from collections import defaultdict

    if not entities:
        for t in tasks:
            t.update(size_x=size_x, size_z=size_z, entities=[])
        return

    max_zoom = max(t['tile_zoom'] for t in tasks) if tasks else 0
    bucket_size = float(TILE_STEP_SIZE * (2 ** max_zoom))

    grid: dict[tuple[int, int], list] = defaultdict(list)
    for e in entities:
        bx = int(e[0] / bucket_size)
        bz = int(e[1] / bucket_size)
        grid[(bx, bz)].append(e)

    for t in tasks:
        wpt = float(TILE_STEP_SIZE * (2 ** t['tile_zoom']))
        tx0 = t['tile_x'] * wpt
        tz0 = t['tile_y'] * wpt
        margin = max(wpt * 0.05, margin_min)

        bx_lo = int((tx0 - margin) / bucket_size)
        bx_hi = int((tx0 + wpt + margin) / bucket_size)
        bz_lo = int((tz0 - margin) / bucket_size)
        bz_hi = int((tz0 + wpt + margin) / bucket_size)

        tile_ents = []
        for bx in range(bx_lo, bx_hi + 1):
            for bz in range(bz_lo, bz_hi + 1):
                bucket = grid.get((bx, bz))
                if not bucket:
                    continue
                for e in bucket:
                    if tx0 - margin <= e[0] <= tx0 + wpt + margin and tz0 - margin <= e[1] <= tz0 + wpt + margin:
                        tile_ents.append(e)

        t.update(size_x=size_x, size_z=size_z, entities=tile_ents)


def _tile_tasks(size_x: float, size_z: float, output_dir: str) -> list[dict]:
    tasks = []
    for zoom in range(MAX_ZOOM + 1):
        wpt = TILE_STEP_SIZE * (2 ** zoom)
        tx_count = max(1, math.ceil(size_x / wpt))
        tz_count = max(1, math.ceil(size_z / wpt))
        for tx in range(tx_count):
            for ty in range(tz_count):
                out = os.path.join(output_dir, str(zoom), str(tx), str(ty), 'tile.png')
                tasks.append({'tile_zoom': zoom, 'tile_x': tx, 'tile_y': ty, 'output_path': out})
    return tasks


# ---------------------------------------------------------------------------
# Per-layer tile renderers (run in worker processes)
# ---------------------------------------------------------------------------

def _render_density_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    density_grid: np.ndarray, cell_size: float,
    color_scale: list[str],
    opacity: int = 153,
    texture_mode: str = 'none',
) -> Image.Image:
    """Render a density heatmap tile with optional texture overlay.

    texture_mode: 'none' | 'dots' (tree canopy) | 'grid' (buildings) | 'hatch' (restricted)
    """
    wx, wz, oob = _tile_world_coords(tile_zoom, tile_x, tile_y, size_x, size_z)
    vals = _sample_grid(wx, wz, density_grid, cell_size)

    rgba = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    mask = (vals > 0.02) & ~oob

    if np.any(mask):
        flat_vals = vals[mask]
        n = len(color_scale)
        pos = np.clip(flat_vals, 0, 1) * (n - 1)
        idx = np.clip(pos.astype(np.int32), 0, n - 2)
        frac = pos - idx

        colors = np.array([_hex_to_rgb(c) for c in color_scale], dtype=np.float32)
        lo = colors[idx]
        hi = colors[idx + 1]
        rgb = lo + (hi - lo) * frac[..., np.newaxis]

        rgba[mask, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        alpha_base = np.clip(flat_vals * 200 + 25, 25, opacity).astype(np.uint8)
        rgba[mask, 3] = alpha_base

    if texture_mode != 'none' and np.any(mask):
        img = Image.fromarray(rgba, 'RGBA')
        draw = ImageDraw.Draw(img)
        px_y, px_x = np.meshgrid(np.arange(TILE_SIZE), np.arange(TILE_SIZE), indexing='ij')

        if texture_mode == 'dots':
            spacing = max(4, 12 - tile_zoom * 2)
            dot_mask = mask & (vals > 0.3) & ((px_x % spacing == 0) & (px_y % spacing == 0))
            if np.any(dot_mask):
                ys, xs = np.where(dot_mask)
                for x, y in zip(xs, ys):
                    r = max(1, int(vals[y, x] * 2.5))
                    draw.ellipse([x - r, y - r, x + r, y + r], fill=(20, 80, 20, 60))

        elif texture_mode == 'grid':
            spacing = max(5, 14 - tile_zoom * 2)
            grid_mask = mask & (vals > 0.25) & (((px_x % spacing == 0) | (px_y % spacing == 0)))
            if np.any(grid_mask):
                ys, xs = np.where(grid_mask)
                for x, y in zip(xs, ys):
                    draw.point((x, y), fill=(80, 60, 50, 50))

        elif texture_mode == 'hatch':
            spacing = max(4, 10 - tile_zoom)
            hatch_mask = mask & (vals > 0.3) & (((px_x + px_y) % spacing == 0))
            if np.any(hatch_mask):
                ys, xs = np.where(hatch_mask)
                for x, y in zip(xs, ys):
                    draw.point((x, y), fill=(0, 0, 0, 40))

        return img

    return Image.fromarray(rgba, 'RGBA')


def _render_slope_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    slope_grid: np.ndarray, grid_res: float,
) -> Image.Image:
    """Military-standard slope rendering: flat areas transparent, continuous gradient."""
    scale_colors = np.array([
        [255, 249, 196],  # 5°  — pale yellow
        [255, 183, 77],   # 15° — orange
        [229, 57, 53],    # 30° — red
        [183, 28, 28],    # 45° — dark red
    ], dtype=np.float32)
    scale_breaks = np.array([5.0, 15.0, 30.0, 45.0])

    wx, wz, oob = _tile_world_coords(tile_zoom, tile_x, tile_y, size_x, size_z)
    vals = _sample_grid_bilinear(wx, wz, slope_grid, grid_res)

    rgba = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    mask = (vals > 3.0) & ~oob

    if np.any(mask):
        flat = vals[mask]
        n = len(scale_breaks)
        idx = np.searchsorted(scale_breaks, flat, side='right') - 1
        idx = np.clip(idx, 0, n - 2)
        lo_b = scale_breaks[idx]
        hi_b = scale_breaks[np.minimum(idx + 1, n - 1)]
        denom = hi_b - lo_b
        denom[denom < 1e-6] = 1.0
        t = np.clip((flat - lo_b) / denom, 0, 1)

        lo_c = scale_colors[idx]
        hi_c = scale_colors[np.minimum(idx + 1, n - 1)]
        rgb = lo_c + (hi_c - lo_c) * t[..., np.newaxis]

        rgba[mask, :3] = np.clip(rgb, 0, 255).astype(np.uint8)

        alpha_t = np.clip((flat - 3.0) / 42.0, 0, 1)
        rgba[mask, 3] = np.clip(alpha_t * 170 + 30, 30, 200).astype(np.uint8)

    return Image.fromarray(rgba, 'RGBA')


def _render_hillshade_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    shade_grid: np.ndarray, grid_res: float,
) -> Image.Image:
    wx, wz, oob = _tile_world_coords(tile_zoom, tile_x, tile_y, size_x, size_z)
    vals = _sample_grid_bilinear(wx, wz, shade_grid, grid_res)

    rgba = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    mask = ~oob

    if np.any(mask):
        raw = vals[mask]
        compressed = 0.25 + raw * 0.6
        gamma = np.power(compressed, 0.85)
        lum = np.clip(gamma * 255, 0, 255).astype(np.uint8)

        rgba[mask, 0] = lum
        rgba[mask, 1] = lum
        rgba[mask, 2] = lum

        darkness = 1.0 - gamma
        alpha = np.clip(darkness * 200 + 20, 20, 160).astype(np.uint8)
        rgba[mask, 3] = alpha

    return Image.fromarray(rgba, 'RGBA')


def _marching_squares_segments(
    heights: np.ndarray, level: float, oob: np.ndarray,
) -> list[tuple[float, float, float, float]]:
    """Extract contour line segments using marching squares with linear interpolation."""
    rows, cols = heights.shape
    if rows < 2 or cols < 2:
        return []

    above = (heights >= level).astype(np.uint8)
    cell_code = above[:-1, :-1] | (above[:-1, 1:] << 1) | (above[1:, 1:] << 2) | (above[1:, :-1] << 3)

    valid = ~(oob[:-1, :-1] | oob[:-1, 1:] | oob[1:, 1:] | oob[1:, :-1])
    active = (cell_code > 0) & (cell_code < 15) & valid

    if not np.any(active):
        return []

    ys, xs = np.where(active)
    segments: list[tuple[float, float, float, float]] = []

    def _lerp_t(v0: float, v1: float) -> float:
        d = v1 - v0
        if abs(d) < 1e-9:
            return 0.5
        return np.clip((level - v0) / d, 0.0, 1.0)

    edge_funcs = {
        'top':    lambda r, c: (c + _lerp_t(heights[r, c], heights[r, c + 1]), float(r)),
        'right':  lambda r, c: (float(c + 1), r + _lerp_t(heights[r, c + 1], heights[r + 1, c + 1])),
        'bottom': lambda r, c: (c + _lerp_t(heights[r + 1, c], heights[r + 1, c + 1]), float(r + 1)),
        'left':   lambda r, c: (float(c), r + _lerp_t(heights[r, c], heights[r + 1, c])),
    }

    CASE_EDGES = {
        1:  [('left', 'top')],
        2:  [('top', 'right')],
        3:  [('left', 'right')],
        4:  [('right', 'bottom')],
        5:  [('left', 'bottom'), ('top', 'right')],
        6:  [('top', 'bottom')],
        7:  [('left', 'bottom')],
        8:  [('bottom', 'left')],
        9:  [('bottom', 'top')],
        10: [('top', 'left'), ('right', 'bottom')],
        11: [('bottom', 'right')],
        12: [('right', 'left')],
        13: [('top', 'right')],  # mirror of 2
        14: [('left', 'top')],   # mirror of 1
    }

    for y, x in zip(ys, xs):
        code = int(cell_code[y, x])
        edges = CASE_EDGES.get(code)
        if not edges:
            continue
        for e0, e1 in edges:
            x0, y0 = edge_funcs[e0](y, x)
            x1, y1 = edge_funcs[e1](y, x)
            segments.append((x0, y0, x1, y1))

    return segments


def _render_contour_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    height_grid: np.ndarray, height_res: int,
    max_elevation: float,
) -> Image.Image:
    wx, wz, oob = _tile_world_coords(tile_zoom, tile_x, tile_y, size_x, size_z)
    heights = _sample_grid_bilinear(wx, wz, height_grid, height_res)

    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    interval = 20 if tile_zoom <= 2 else 50 if tile_zoom <= 4 else 100
    major_interval = interval * 5

    minor_color = (180, 150, 120, 140)
    major_color = (130, 90, 60, 220)
    label_positions: list[tuple[float, float, int]] = []

    for level in range(interval, int(max_elevation) + interval, interval):
        segs = _marching_squares_segments(heights, float(level), oob)
        if not segs:
            continue

        is_major = level % major_interval == 0
        color = major_color if is_major else minor_color
        width = 2 if is_major else 1

        for x0, y0, x1, y1 in segs:
            draw.line([(x0, y0), (x1, y1)], fill=color, width=width)

        if is_major and tile_zoom <= 2 and len(segs) >= 3:
            step = max(1, len(segs) // 3)
            for idx in range(step, len(segs), step * 2):
                seg = segs[min(idx, len(segs) - 1)]
                mx = (seg[0] + seg[2]) / 2
                my = (seg[1] + seg[3]) / 2
                if 8 < mx < TILE_SIZE - 25 and 8 < my < TILE_SIZE - 12:
                    label_positions.append((mx, my, level))
                    break

    if label_positions:
        try:
            font = ImageFont.truetype("arial.ttf", 9)
        except (OSError, IOError):
            font = ImageFont.load_default()
        for lx, ly, elev in label_positions:
            txt = str(elev)
            bbox = font.getbbox(txt)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.rectangle([lx - 1, ly - 1, lx + tw + 1, ly + th + 1], fill=(255, 255, 255, 160))
            draw.text((lx, ly), txt, fill=major_color, font=font)

    return img


def _render_water_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    type_grid: np.ndarray, water_res: float,
    ocean_mask: np.ndarray | None = None,
    height_grid: np.ndarray | None = None,
    height_res: float = 100,
) -> Image.Image:
    """Military-standard water rendering with flood-fill ocean + inland water grid."""
    type_colors = {
        1: np.array([92, 157, 200], dtype=np.uint8),   # ocean — deep blue
        2: np.array([126, 184, 218], dtype=np.uint8),   # pond/lake — medium blue
        3: np.array([168, 212, 230], dtype=np.uint8),   # river — lighter blue
    }
    edge_color = np.array([40, 80, 120, 220], dtype=np.uint8)

    wx, wz, oob = _tile_world_coords(tile_zoom, tile_x, tile_y, size_x, size_z)

    rgba = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    water_mask = np.zeros((TILE_SIZE, TILE_SIZE), dtype=bool)

    # Ocean from flood-fill mask (bilinear interpolation for smooth coastlines)
    if ocean_mask is not None and height_grid is not None:
        h_rows, h_cols = height_grid.shape
        fzz = wz / height_res
        fxx = wx / height_res
        rr0 = np.clip(np.floor(fzz).astype(np.int32), 0, h_rows - 1)
        rr1 = np.clip(rr0 + 1, 0, h_rows - 1)
        cc0 = np.clip(np.floor(fxx).astype(np.int32), 0, h_cols - 1)
        cc1 = np.clip(cc0 + 1, 0, h_cols - 1)
        ttz = np.clip(fzz - np.floor(fzz), 0, 1)
        ttx = np.clip(fxx - np.floor(fxx), 0, 1)
        of = ocean_mask.astype(np.float32)
        oi = of[rr0, cc0] * (1 - ttz) * (1 - ttx) + of[rr0, cc1] * (1 - ttz) * ttx + of[rr1, cc0] * ttz * (1 - ttx) + of[rr1, cc1] * ttz * ttx
        is_ocean = (oi > 0.5) & ~oob
        if np.any(is_ocean):
            rgba[is_ocean, :3] = type_colors[1]
            rgba[is_ocean, 3] = 190
            water_mask |= is_ocean

    # Inland water from water grid
    wt = _sample_grid(wx, wz, type_grid, water_res)
    inland = (wt > 0) & ~oob & ~water_mask
    for t_val, color in type_colors.items():
        m = (wt == t_val) & inland
        if np.any(m):
            rgba[m, :3] = color
            rgba[m, 3] = 190
    water_mask |= inland

    if np.any(water_mask):
        edge_h = water_mask[:, :-1] != water_mask[:, 1:]
        edge_v = water_mask[:-1, :] != water_mask[1:, :]
        edge = np.zeros_like(water_mask)
        edge[:, :-1] |= edge_h
        edge[:, 1:] |= edge_h
        edge[:-1, :] |= edge_v
        edge[1:, :] |= edge_v
        edge &= ~oob

        if np.any(edge):
            rgba[edge] = edge_color

        px_y, px_x = np.meshgrid(np.arange(TILE_SIZE), np.arange(TILE_SIZE), indexing='ij')
        wave = np.sin(px_x * 0.3 + px_y * 0.15) * 8
        wave_mask = water_mask & ((px_x + px_y * 3 + wave.astype(np.int32)) % max(6, 16 - tile_zoom * 2) == 0)
        if np.any(wave_mask):
            rgba[wave_mask, :3] = np.clip(rgba[wave_mask, :3].astype(np.int16) - 15, 0, 255).astype(np.uint8)

    return Image.fromarray(rgba, 'RGBA')


def _render_trafficability_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    score_grid: np.ndarray, cell_size: float,
) -> Image.Image:
    """Military-standard trafficability: soft palette + hatch for restricted zones."""
    scale_colors = np.array([
        [198, 40, 40],    # 0.0 — NO GO (muted red)
        [230, 140, 50],   # 0.3 — SLOW GO (amber)
        [200, 200, 100],  # 0.7 — caution (olive yellow)
        [100, 170, 90],   # 1.0 — GO (muted green)
    ], dtype=np.float32)
    scale_breaks = np.array([0.0, 0.3, 0.7, 1.0])

    wx, wz, oob = _tile_world_coords(tile_zoom, tile_x, tile_y, size_x, size_z)
    vals = _sample_grid(wx, wz, score_grid, cell_size)

    rgba = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    mask = ~oob

    if np.any(mask):
        flat = vals[mask]
        n = len(scale_breaks)
        idx = np.searchsorted(scale_breaks, flat, side='right') - 1
        idx = np.clip(idx, 0, n - 2)
        lo_b = scale_breaks[idx]
        hi_b = scale_breaks[np.minimum(idx + 1, n - 1)]
        denom = hi_b - lo_b
        denom[denom < 1e-6] = 1.0
        t = np.clip((flat - lo_b) / denom, 0, 1)

        lo_c = scale_colors[idx]
        hi_c = scale_colors[np.minimum(idx + 1, n - 1)]
        rgb = lo_c + (hi_c - lo_c) * t[..., np.newaxis]

        rgba[mask, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        alpha = np.where(flat < 0.3, 170, np.where(flat < 0.7, 130, 100)).astype(np.uint8)
        rgba[mask, 3] = alpha

    img = Image.fromarray(rgba, 'RGBA')
    draw = ImageDraw.Draw(img)

    restricted = mask & (vals < 0.3)
    if np.any(restricted):
        spacing = max(4, 10 - tile_zoom)
        px_y, px_x = np.meshgrid(np.arange(TILE_SIZE), np.arange(TILE_SIZE), indexing='ij')
        hatch = restricted & ((px_x + px_y) % spacing == 0)
        if np.any(hatch):
            ys, xs = np.where(hatch)
            for x, y in zip(xs, ys):
                draw.point((x, y), fill=(120, 20, 20, 80))

    return img


def _render_cover_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    cover_grid: np.ndarray, cell_size: float,
) -> Image.Image:
    """Cover/concealment: brown-gray palette distinct from vegetation green."""
    scale = ['#EFEBE9', '#BCAAA4', '#8D6E63', '#5D4037', '#3E2723']
    return _render_density_tile(
        tile_zoom, tile_x, tile_y, size_x, size_z,
        cover_grid, cell_size, scale, opacity=160,
    )


def _render_mcoo_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    mcoo_grid: np.ndarray, cell_size: float,
) -> Image.Image:
    """MCOO with military-standard GO/SLOW GO/NO GO rendering + texture fills."""
    cat_colors = {
        0: np.array([100, 170, 90], dtype=np.uint8),   # GO — muted green
        1: np.array([220, 180, 50], dtype=np.uint8),    # SLOW GO — amber
        2: np.array([190, 50, 50], dtype=np.uint8),     # NO GO — muted red
    }
    cat_alpha = {0: 110, 1: 140, 2: 170}

    wx, wz, oob = _tile_world_coords(tile_zoom, tile_x, tile_y, size_x, size_z)
    vals = _sample_grid(wx, wz, mcoo_grid, cell_size)

    rgba = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    for cat_val, color in cat_colors.items():
        m = (vals == cat_val) & ~oob
        if np.any(m):
            rgba[m, :3] = color
            rgba[m, 3] = cat_alpha[cat_val]

    img = Image.fromarray(rgba, 'RGBA')
    draw = ImageDraw.Draw(img)

    px_y, px_x = np.meshgrid(np.arange(TILE_SIZE), np.arange(TILE_SIZE), indexing='ij')
    spacing = max(4, 8 - tile_zoom)

    slow_go = (vals == 1) & ~oob
    if np.any(slow_go):
        hatch = slow_go & ((px_x + px_y) % spacing == 0)
        if np.any(hatch):
            ys, xs = np.where(hatch)
            for x, y in zip(xs, ys):
                draw.point((x, y), fill=(160, 130, 30, 60))

    no_go = (vals == 2) & ~oob
    if np.any(no_go):
        cross = no_go & (((px_x + px_y) % spacing == 0) | ((px_x - px_y) % spacing == 0))
        if np.any(cross):
            ys, xs = np.where(cross)
            for x, y in zip(xs, ys):
                draw.point((x, y), fill=(120, 20, 20, 80))

    return img


# ---------------------------------------------------------------------------
# Worker wrappers (for ProcessPoolExecutor)
# ---------------------------------------------------------------------------

def _save_tile(img: Image.Image, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, format='PNG', optimize=True, compress_level=6)
    return path


def _worker_density(args: dict) -> str:
    img = _render_density_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'],
        args['density_grid'], args['cell_size'], args['color_scale'],
        args.get('opacity', 153),
        args.get('texture_mode', 'none'),
    )
    return _save_tile(img, args['output_path'])


def _worker_slope(args: dict) -> str:
    img = _render_slope_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'],
        args['slope_grid'], args['grid_res'],
    )
    return _save_tile(img, args['output_path'])


def _worker_hillshade(args: dict) -> str:
    img = _render_hillshade_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'],
        args['shade_grid'], args['grid_res'],
    )
    return _save_tile(img, args['output_path'])


def _worker_contour(args: dict) -> str:
    img = _render_contour_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'],
        args['height_grid'], args['height_res'], args['max_elevation'],
    )
    return _save_tile(img, args['output_path'])


def _worker_water(args: dict) -> str:
    img = _render_water_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'],
        args['type_grid'], args['water_res'],
        ocean_mask=args.get('ocean_mask'),
        height_grid=args.get('height_grid'),
        height_res=args.get('height_res', 100),
    )
    return _save_tile(img, args['output_path'])


def _worker_trafficability(args: dict) -> str:
    img = _render_trafficability_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'],
        args['score_grid'], args['cell_size'],
    )
    return _save_tile(img, args['output_path'])


def _worker_cover(args: dict) -> str:
    img = _render_cover_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'],
        args['cover_grid'], args['cell_size'],
    )
    return _save_tile(img, args['output_path'])


def _worker_mcoo(args: dict) -> str:
    img = _render_mcoo_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'],
        args['mcoo_grid'], args['cell_size'],
    )
    return _save_tile(img, args['output_path'])


# ---------------------------------------------------------------------------
# Data preparation helpers
# ---------------------------------------------------------------------------

def _compute_slope(hg_np: np.ndarray, res: float) -> np.ndarray:
    dzdx = np.zeros_like(hg_np)
    dzdy = np.zeros_like(hg_np)
    dzdx[:, 1:-1] = (hg_np[:, 2:] - hg_np[:, :-2]) / (2 * res)
    dzdx[:, 0] = (hg_np[:, 1] - hg_np[:, 0]) / res
    dzdx[:, -1] = (hg_np[:, -1] - hg_np[:, -2]) / res
    dzdy[1:-1, :] = (hg_np[2:, :] - hg_np[:-2, :]) / (2 * res)
    dzdy[0, :] = (hg_np[1, :] - hg_np[0, :]) / res
    dzdy[-1, :] = (hg_np[-1, :] - hg_np[-2, :]) / res
    return np.degrees(np.arctan(np.sqrt(dzdx ** 2 + dzdy ** 2)))


def _compute_hillshade(
    hg_np: np.ndarray, res: float,
    lights: list[tuple[float, float, float]] | None = None,
) -> np.ndarray:
    """Multi-directional hillshade using Horn's method.

    lights: list of (azimuth_deg, altitude_deg, weight) tuples.
    Default uses primary NW light + secondary W fill light for depth.
    """
    if hg_np.shape[0] < 3 or hg_np.shape[1] < 3:
        return np.full(hg_np.shape, 0.5, dtype=np.float32)

    if lights is None:
        lights = [(315, 45, 0.65), (270, 60, 0.25), (0, 70, 0.10)]

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

    shade = np.zeros_like(slope)
    for az_deg, alt_deg, weight in lights:
        az_rad = np.radians(360 - az_deg + 90)
        alt_rad = np.radians(alt_deg)
        s = np.cos(alt_rad) * np.cos(slope) + np.sin(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
        shade += np.clip(s, 0, 1) * weight

    return np.clip(shade, 0, 1).astype(np.float32)


def _compute_trafficability(
    hg_np: np.ndarray | None, hg_res: float,
    wg_raw: list | None, wg_res: float,
    veg_grid: np.ndarray,
    size_x: float, size_z: float, cell_size: float,
) -> np.ndarray:
    cols = max(1, math.ceil(size_x / cell_size))
    rows = max(1, math.ceil(size_z / cell_size))
    score = np.ones((rows, cols), dtype=np.float32)

    if hg_np is not None:
        slope_full = _compute_slope(hg_np, hg_res)
        ri = np.arange(rows)
        ci = np.arange(cols)
        ci_g, ri_g = np.meshgrid(ci, ri)
        hg_ci = np.clip((ci_g * cell_size / hg_res).astype(np.int32), 0, hg_np.shape[1] - 1)
        hg_ri = np.clip((ri_g * cell_size / hg_res).astype(np.int32), 0, hg_np.shape[0] - 1)
        slope_sampled = slope_full[hg_ri, hg_ci]

        slope_factor = np.ones_like(slope_sampled)
        slope_factor[slope_sampled > 45] = 0.0
        slope_factor[(slope_sampled > 30) & (slope_sampled <= 45)] = 0.2
        slope_factor[(slope_sampled > 15) & (slope_sampled <= 30)] = 0.6
        score *= slope_factor

    if wg_raw:
        for r in range(rows):
            for c in range(cols):
                wg_c = min(int(c * cell_size / wg_res), len(wg_raw[0]) - 1)
                wg_r = min(int(r * cell_size / wg_res), len(wg_raw) - 1)
                cell = wg_raw[wg_r][wg_c]
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

    veg_rows, veg_cols = veg_grid.shape
    if veg_rows == rows and veg_cols == cols:
        veg_factor = np.ones_like(score)
        veg_factor[veg_grid > 0.8] = 0.4
        veg_factor[(veg_grid > 0.5) & (veg_grid <= 0.8)] = 0.7
        score *= veg_factor

    return np.round(score, 3)


def _compute_mcoo(
    traff_grid: np.ndarray, cover_grid: np.ndarray,
    hg_np: np.ndarray | None, hg_res: float,
    size_x: float, size_z: float, cell_size: float,
) -> np.ndarray:
    cols = max(1, math.ceil(size_x / cell_size))
    rows = max(1, math.ceil(size_z / cell_size))

    if hg_np is not None:
        slope_full = _compute_slope(hg_np, hg_res)
        ri = np.arange(rows)
        ci = np.arange(cols)
        ci_g, ri_g = np.meshgrid(ci, ri)
        sri = np.clip((ri_g * cell_size / hg_res).astype(np.int32), 0, slope_full.shape[0] - 1)
        sci = np.clip((ci_g * cell_size / hg_res).astype(np.int32), 0, slope_full.shape[1] - 1)
        s_sampled = 1.0 - np.clip(slope_full[sri, sci] / 45.0, 0, 1)
    else:
        s_sampled = np.zeros((rows, cols), dtype=np.float32)

    composite = traff_grid * 0.5 + s_sampled * 0.3 + (1.0 - cover_grid) * 0.2
    return np.where(composite >= 0.7, 0, np.where(composite >= 0.3, 1, 2)).astype(np.float32)


def _parse_water_type_grid(wg_raw: list) -> np.ndarray:
    rows = len(wg_raw)
    cols = len(wg_raw[0]) if wg_raw else 0
    grid = np.zeros((rows, cols), dtype=np.int32)
    for r, row in enumerate(wg_raw):
        for c, cell in enumerate(row):
            if cell and isinstance(cell, list):
                if len(cell) >= 3:
                    grid[r, c] = int(cell[0])
                elif len(cell) == 2:
                    grid[r, c] = 1 if cell[0] else 0
    return grid


# ---------------------------------------------------------------------------
# Public generation functions (one per layer)
# ---------------------------------------------------------------------------

async def _run_parallel(
    worker_fn, tasks: list[dict], max_workers: int, layer_name: str, map_id: int = 0,
) -> int:
    log.info('Rendering %d %s tiles with %d workers...', len(tasks), layer_name, max_workers)
    total = len(tasks)

    def _do():
        from backend.app.map.service.tile_progress import set_progress
        if map_id:
            set_progress(map_id, layer_name, 0, total)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(worker_fn, t): t for t in tasks}
            done = 0
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception:
                    log.exception('%s tile render failed', layer_name)
                done += 1
                if map_id and (done % 10 == 0 or done == total):
                    set_progress(map_id, layer_name, done, total)
                if done % 100 == 0:
                    log.info('%s progress: %d / %d', layer_name, done, total)

    await asyncio.to_thread(_do)
    log.info('%s tile generation complete: %d tiles', layer_name, total)
    return total


def _prepare_output_dir(base_dir: str, map_id: int, layer_name: str) -> str:
    tile_dir = os.path.join(base_dir, str(map_id), f'{layer_name}_tiles')
    if os.path.isdir(tile_dir):
        log.info('Removing old %s tiles at %s', layer_name, tile_dir)
        shutil.rmtree(tile_dir)
    return tile_dir


async def generate_vegetation_tiles(
    db: Any, game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    from sqlalchemy import select
    from backend.app.map.model.map import MapEntity

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'vegetation')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    positions: list[tuple[float, float]] = []
    stmt = (
        select(MapEntity.position_x, MapEntity.position_z)
        .where(MapEntity.map_id == game_map.id, MapEntity.category.in_(VEGETATION_CATEGORIES))
    )
    result = await db.execute(stmt)
    for px, pz in result.all():
        positions.append((float(px), float(pz)))

    cell_size = 100.0
    grid = _build_density_grid(positions, game_map.size_x, game_map.size_z, cell_size)
    scale = ['#E8F5E9', '#A5D6A7', '#66BB6A', '#2E7D32', '#1B5E20']

    for t in tasks:
        t.update(size_x=game_map.size_x, size_z=game_map.size_z,
                 density_grid=grid, cell_size=cell_size, color_scale=scale,
                 texture_mode='dots')

    total = await _run_parallel(_worker_density, tasks, max_workers, 'vegetation', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'vegetation'}


async def generate_builtup_tiles(
    db: Any, game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    from sqlalchemy import select
    from backend.app.map.model.map import MapEntity

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'builtup')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    positions: list[tuple[float, float]] = []
    stmt = (
        select(MapEntity.position_x, MapEntity.position_z)
        .where(MapEntity.map_id == game_map.id, MapEntity.category.in_(BUILDING_CATEGORIES))
    )
    result = await db.execute(stmt)
    for px, pz in result.all():
        positions.append((float(px), float(pz)))

    cell_size = 200.0
    grid = _build_density_grid(positions, game_map.size_x, game_map.size_z, cell_size)
    scale = ['#F5F5F5', '#E0E0E0', '#BDBDBD', '#757575', '#424242']

    for t in tasks:
        t.update(size_x=game_map.size_x, size_z=game_map.size_z,
                 density_grid=grid, cell_size=cell_size, color_scale=scale,
                 texture_mode='grid')

    total = await _run_parallel(_worker_density, tasks, max_workers, 'builtup', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'builtup'}


async def generate_slope_tiles(
    game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    hg = game_map.height_grid_data
    if not hg:
        return {'total_tiles': 0, 'layer': 'slope', 'error': 'no height data'}

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'slope')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    res = game_map.height_grid_resolution or 100
    hg_np = np.array(hg, dtype=np.float32)
    slope_grid = _compute_slope(hg_np, res)

    for t in tasks:
        t.update(size_x=game_map.size_x, size_z=game_map.size_z,
                 slope_grid=slope_grid, grid_res=res)

    total = await _run_parallel(_worker_slope, tasks, max_workers, 'slope', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'slope'}


async def generate_hillshade_tiles(
    game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    hg = game_map.height_grid_data
    if not hg:
        return {'total_tiles': 0, 'layer': 'hillshade', 'error': 'no height data'}

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'hillshade')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    res = game_map.height_grid_resolution or 100
    hg_np = np.array(hg, dtype=np.float32)
    shade = _compute_hillshade(hg_np, res)

    for t in tasks:
        t.update(size_x=game_map.size_x, size_z=game_map.size_z,
                 shade_grid=shade, grid_res=res)

    total = await _run_parallel(_worker_hillshade, tasks, max_workers, 'hillshade', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'hillshade'}


async def generate_contour_tiles(
    game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    hg = game_map.height_grid_data
    if not hg:
        return {'total_tiles': 0, 'layer': 'contours', 'error': 'no height data'}

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'contour')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    res = game_map.height_grid_resolution or 100
    hg_np = np.array(hg, dtype=np.float32)
    max_elev = game_map.max_elevation or game_map.max_elevation_precise or 500

    for t in tasks:
        t.update(size_x=game_map.size_x, size_z=game_map.size_z,
                 height_grid=hg_np, height_res=res, max_elevation=max_elev)

    total = await _run_parallel(_worker_contour, tasks, max_workers, 'contours', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'contours'}


async def generate_water_tiles(
    game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    wg = game_map.water_grid_data
    if not wg:
        return {'total_tiles': 0, 'layer': 'water', 'error': 'no water data'}

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'water')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    res = game_map.water_grid_resolution or 200
    type_grid = _parse_water_type_grid(wg)

    # Build ocean mask from height grid via flood-fill
    ocean_np = None
    height_np = None
    h_res = game_map.height_grid_resolution or 100
    hg_raw = game_map.height_grid_data
    if hg_raw:
        if isinstance(hg_raw, dict) and 'grid' in hg_raw:
            hg_raw = hg_raw['grid']
        height_np = np.array(hg_raw, dtype=np.float32)
        from backend.app.map.service.military_renderer import _build_ocean_mask
        ocean_np = _build_ocean_mask(height_np, h_res, game_map.size_x, game_map.size_z)

    for t in tasks:
        t.update(size_x=game_map.size_x, size_z=game_map.size_z,
                 type_grid=type_grid, water_res=res,
                 ocean_mask=ocean_np, height_grid=height_np, height_res=h_res)

    total = await _run_parallel(_worker_water, tasks, max_workers, 'water', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'water'}


async def generate_trafficability_tiles(
    db: Any, game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    from sqlalchemy import select
    from backend.app.map.model.map import MapEntity

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'trafficability')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    cell_size = 100.0
    hg = game_map.height_grid_data
    hg_np = np.array(hg, dtype=np.float32) if hg else None
    hg_res = game_map.height_grid_resolution or 100

    veg_positions: list[tuple[float, float]] = []
    stmt = (
        select(MapEntity.position_x, MapEntity.position_z)
        .where(MapEntity.map_id == game_map.id, MapEntity.category.in_(VEGETATION_CATEGORIES))
    )
    result = await db.execute(stmt)
    for px, pz in result.all():
        veg_positions.append((float(px), float(pz)))

    veg_grid = _build_density_grid(veg_positions, game_map.size_x, game_map.size_z, cell_size)
    wg_raw = game_map.water_grid_data
    wg_res = game_map.water_grid_resolution or 200

    score = _compute_trafficability(hg_np, hg_res, wg_raw, wg_res, veg_grid,
                                     game_map.size_x, game_map.size_z, cell_size)

    for t in tasks:
        t.update(size_x=game_map.size_x, size_z=game_map.size_z,
                 score_grid=score, cell_size=cell_size)

    total = await _run_parallel(_worker_trafficability, tasks, max_workers, 'trafficability', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'trafficability'}


async def generate_cover_tiles(
    db: Any, game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    from sqlalchemy import select
    from backend.app.map.model.map import MapEntity

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'cover')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    cell_size = 100.0
    cols = max(1, math.ceil(game_map.size_x / cell_size))
    rows = max(1, math.ceil(game_map.size_z / cell_size))
    score_grid = np.zeros((rows, cols), dtype=np.float32)

    for cat, weight in COVER_WEIGHTS.items():
        stmt = (
            select(MapEntity.position_x, MapEntity.position_z)
            .where(MapEntity.map_id == game_map.id, MapEntity.category == cat)
        )
        result = await db.execute(stmt)
        positions = result.all()
        if not positions:
            continue
        arr = np.array([(float(px), float(pz)) for px, pz in positions], dtype=np.float32)
        ci = np.clip((arr[:, 0] / cell_size).astype(np.int32), 0, cols - 1)
        ri = np.clip((arr[:, 1] / cell_size).astype(np.int32), 0, rows - 1)
        np.add.at(score_grid, (ri, ci), weight)

    mx = score_grid.max()
    if mx > 0:
        score_grid /= mx

    for t in tasks:
        t.update(size_x=game_map.size_x, size_z=game_map.size_z,
                 cover_grid=score_grid, cell_size=cell_size)

    total = await _run_parallel(_worker_cover, tasks, max_workers, 'cover', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'cover'}


async def generate_mcoo_tiles(
    db: Any, game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    from sqlalchemy import select
    from backend.app.map.model.map import MapEntity

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'mcoo')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    cell_size = 100.0
    hg = game_map.height_grid_data
    hg_np = np.array(hg, dtype=np.float32) if hg else None
    hg_res = game_map.height_grid_resolution or 100

    veg_positions: list[tuple[float, float]] = []
    stmt = (
        select(MapEntity.position_x, MapEntity.position_z)
        .where(MapEntity.map_id == game_map.id, MapEntity.category.in_(VEGETATION_CATEGORIES))
    )
    result = await db.execute(stmt)
    for px, pz in result.all():
        veg_positions.append((float(px), float(pz)))

    veg_grid = _build_density_grid(veg_positions, game_map.size_x, game_map.size_z, cell_size)
    wg_raw = game_map.water_grid_data
    wg_res = game_map.water_grid_resolution or 200

    traff_grid = _compute_trafficability(hg_np, hg_res, wg_raw, wg_res, veg_grid,
                                          game_map.size_x, game_map.size_z, cell_size)

    cols = max(1, math.ceil(game_map.size_x / cell_size))
    rows = max(1, math.ceil(game_map.size_z / cell_size))
    cover_grid = np.zeros((rows, cols), dtype=np.float32)
    for cat, weight in COVER_WEIGHTS.items():
        stmt2 = (
            select(MapEntity.position_x, MapEntity.position_z)
            .where(MapEntity.map_id == game_map.id, MapEntity.category == cat)
        )
        result2 = await db.execute(stmt2)
        positions = result2.all()
        if not positions:
            continue
        arr = np.array([(float(px), float(pz)) for px, pz in positions], dtype=np.float32)
        ci = np.clip((arr[:, 0] / cell_size).astype(np.int32), 0, cols - 1)
        ri = np.clip((arr[:, 1] / cell_size).astype(np.int32), 0, rows - 1)
        np.add.at(cover_grid, (ri, ci), weight)
    mx = cover_grid.max()
    if mx > 0:
        cover_grid /= mx

    mcoo_grid = _compute_mcoo(traff_grid, cover_grid, hg_np, hg_res,
                               game_map.size_x, game_map.size_z, cell_size)

    for t in tasks:
        t.update(size_x=game_map.size_x, size_z=game_map.size_z,
                 mcoo_grid=mcoo_grid, cell_size=cell_size)

    total = await _run_parallel(_worker_mcoo, tasks, max_workers, 'mcoo', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'mcoo'}


# ---------------------------------------------------------------------------
# Convenience: generate all analysis tiles
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Terrain tile renderers — realistic map features from entity data
# ---------------------------------------------------------------------------

TERRAIN_CATEGORY_COLORS: dict[str, tuple[int, int, int, int]] = {
    'tree':          (34, 100, 34, 190),
    'bush':          (140, 160, 50, 150),
    'grass':         (180, 200, 80, 90),
    'vegetation':    (110, 150, 40, 130),
}

BUILDING_FILL_COLORS: dict[str, tuple[int, int, int, int]] = {
    'building':              (180, 80, 80, 200),
    'building_residential':  (190, 90, 85, 200),
    'building_commercial':   (170, 75, 95, 200),
    'building_industrial':   (160, 70, 70, 200),
    'building_public':       (185, 85, 80, 200),
    'building_military':     (140, 60, 60, 220),
    'ruin':                  (160, 120, 100, 150),
    'fortification':         (120, 50, 50, 230),
}

BUILDING_OUTLINE_COLOR = (100, 30, 30, 230)

ROAD_STYLES: dict[str, tuple[tuple[int, int, int, int], float]] = {
    'main_road':  ((200, 50, 50, 230), 3.0),
    'secondary':  ((220, 160, 40, 210), 2.0),
    'track':      ((180, 140, 80, 180), 1.5),
    'path':       ((150, 120, 80, 140), 1.0),
}

FEATURE_STYLES: dict[str, tuple[tuple[int, int, int, int], str]] = {
    'rock':           ((160, 145, 120, 180), 'circle'),
    'cliff':          ((140, 90, 50, 210), 'line'),
    'fence':          ((60, 60, 60, 160), 'line'),
    'bridge':         ((70, 70, 80, 220), 'rect'),
    'structure':      ((130, 100, 70, 160), 'rect'),
    'infrastructure': ((100, 90, 110, 170), 'diamond'),
}


def _render_vegetation_real_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    entities: list[tuple[float, float, float, float, str]],
) -> Image.Image:
    """Render vegetation as overhead canopy circles from actual entity positions."""
    world_per_tile = float(TILE_STEP_SIZE * (2 ** tile_zoom))
    tile_x0 = tile_x * world_per_tile
    tile_z0 = tile_y * world_per_tile

    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = TILE_SIZE / world_per_tile

    for wx, wz, sx, sz, cat in entities:
        px = (wx - tile_x0) * scale
        py = TILE_SIZE - 1 - (wz - tile_z0) * scale
        radius_world = max(sx, sz) * 0.5
        if radius_world < 0.5:
            radius_world = 2.0 if cat == 'tree' else 1.0
        r = max(1.0, radius_world * scale)

        color = TERRAIN_CATEGORY_COLORS.get(cat, (80, 140, 60, 120))
        draw.ellipse([px - r, py - r, px + r, py + r], fill=color)

    return img


def _render_buildings_real_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    entities: list[tuple],
) -> Image.Image:
    """Render buildings from actual entity positions using world-space corners."""
    import math

    world_per_tile = float(TILE_STEP_SIZE * (2 ** tile_zoom))
    tile_x0 = tile_x * world_per_tile
    tile_z0 = tile_y * world_per_tile

    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = TILE_SIZE / world_per_tile

    for ent in entities:
        wx, wz, sx, sz, cat = ent[0], ent[1], ent[2], ent[3], ent[4]
        rot = ent[5] if len(ent) > 5 else 0.0
        corners_data = ent[6] if len(ent) > 6 else None

        fill = BUILDING_FILL_COLORS.get(cat, (175, 170, 165, 180))

        if corners_data and len(corners_data) == 4:
            pts = [
                ((cx - tile_x0) * scale, TILE_SIZE - 1 - (cz - tile_z0) * scale)
                for cx, cz in corners_data
            ]
            draw.polygon(pts, fill=fill, outline=BUILDING_OUTLINE_COLOR)
        else:
            px = (wx - tile_x0) * scale
            py = TILE_SIZE - 1 - (wz - tile_z0) * scale
            hw = max(sx * 0.5, 2.0) * scale
            hh = max(sz * 0.5, 2.0) * scale

            if abs(rot) < 0.5:
                draw.rectangle([px - hw, py - hh, px + hw, py + hh],
                               fill=fill, outline=BUILDING_OUTLINE_COLOR, width=1)
            else:
                rad = math.radians(-rot)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)
                corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
                rotated = [
                    (px + cx * cos_a - cy * sin_a, py + cx * sin_a + cy * cos_a)
                    for cx, cy in corners
                ]
                draw.polygon(rotated, fill=fill, outline=BUILDING_OUTLINE_COLOR)

    return img


def _render_roads_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    roads: list[tuple[list[list[float]], str, float]],
) -> Image.Image:
    """Render road network as polylines."""
    world_per_tile = float(TILE_STEP_SIZE * (2 ** tile_zoom))
    tile_x0 = tile_x * world_per_tile
    tile_z0 = tile_y * world_per_tile
    tile_x1 = tile_x0 + world_per_tile
    tile_z1 = tile_z0 + world_per_tile

    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = TILE_SIZE / world_per_tile
    margin = world_per_tile * 0.1

    for points, road_type, width in roads:
        if len(points) < 2:
            continue

        in_tile = False
        for pt in points:
            rx = pt[0]
            rz = pt[2] if len(pt) >= 3 else pt[1]
            if (tile_x0 - margin <= rx <= tile_x1 + margin and
                    tile_z0 - margin <= rz <= tile_z1 + margin):
                in_tile = True
                break
        if not in_tile:
            continue

        style = ROAD_STYLES.get(road_type, ((140, 130, 120, 160), 1.5))
        color, base_width = style
        line_width = max(1, int(base_width * (1 + tile_zoom * 0.3)))

        coords = []
        for pt in points:
            rx = pt[0]
            rz = pt[2] if len(pt) >= 3 else pt[1]
            px = (rx - tile_x0) * scale
            py = TILE_SIZE - 1 - (rz - tile_z0) * scale
            coords.append((px, py))

        if len(coords) >= 2:
            draw.line(coords, fill=color, width=line_width, joint='curve')

    return img


def _render_features_tile(
    tile_zoom: int, tile_x: int, tile_y: int,
    size_x: float, size_z: float,
    entities: list[tuple[float, float, float, float, str]],
) -> Image.Image:
    """Render terrain features (rocks, cliffs, fences, bridges) as map symbols."""
    world_per_tile = float(TILE_STEP_SIZE * (2 ** tile_zoom))
    tile_x0 = tile_x * world_per_tile
    tile_z0 = tile_y * world_per_tile

    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = TILE_SIZE / world_per_tile

    for wx, wz, sx, sz, cat in entities:
        px = (wx - tile_x0) * scale
        py = TILE_SIZE - 1 - (wz - tile_z0) * scale
        style = FEATURE_STYLES.get(cat)
        if not style:
            continue
        color, shape = style
        half = max(1.5, max(sx, sz) * 0.5 * scale)

        if shape == 'circle':
            draw.ellipse([px - half, py - half, px + half, py + half], fill=color)
        elif shape == 'rect':
            draw.rectangle([px - half, py - half, px + half, py + half], fill=color, outline=(80, 80, 80, 160), width=1)
        elif shape == 'diamond':
            pts = [(px, py - half), (px + half, py), (px, py + half), (px - half, py)]
            draw.polygon(pts, fill=color, outline=(80, 80, 80, 140))
        elif shape == 'line':
            lw = max(sx, sz) * 0.5 * scale
            if lw < 2:
                lw = 3
            draw.line([(px - lw, py), (px + lw, py)], fill=color, width=max(1, int(half * 0.5)))

    return img


# Workers for terrain tiles

def _worker_vegetation_real(args: dict) -> str:
    img = _render_vegetation_real_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'], args['entities'],
    )
    return _save_tile(img, args['output_path'])


def _worker_buildings_real(args: dict) -> str:
    img = _render_buildings_real_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'], args['entities'],
    )
    return _save_tile(img, args['output_path'])


def _worker_roads(args: dict) -> str:
    img = _render_roads_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'], args['roads'],
    )
    return _save_tile(img, args['output_path'])


def _worker_features(args: dict) -> str:
    img = _render_features_tile(
        args['tile_zoom'], args['tile_x'], args['tile_y'],
        args['size_x'], args['size_z'], args['entities'],
    )
    return _save_tile(img, args['output_path'])


# Generation functions for terrain tiles

TERRAIN_VEG_CATEGORIES = frozenset(['tree', 'bush', 'grass', 'vegetation'])
TERRAIN_BUILDING_CATEGORIES = frozenset([
    'building', 'building_residential', 'building_commercial',
    'building_industrial', 'building_public', 'building_military',
    'ruin', 'fortification',
])
BUILDING_MIN_AREA = 4.0  # m², filter out misclassified tiny entities (< 2m×2m)
TERRAIN_FEATURE_CATEGORIES = frozenset([
    'rock', 'cliff', 'fence', 'bridge', 'structure', 'infrastructure',
])


async def _load_entities_for_tile(
    db: Any, game_map_id: int, categories: frozenset[str],
    tile_x0: float, tile_z0: float, tile_x1: float, tile_z1: float,
    margin: float = 50.0,
) -> list[tuple[float, float, float, float, str]]:
    """Load entities within tile bounds + margin."""
    from sqlalchemy import select
    from backend.app.map.model.map import MapEntity

    stmt = (
        select(MapEntity.position_x, MapEntity.position_z, MapEntity.size_x, MapEntity.size_z, MapEntity.category)
        .where(
            MapEntity.map_id == game_map_id,
            MapEntity.category.in_(categories),
            MapEntity.position_x >= tile_x0 - margin,
            MapEntity.position_x <= tile_x1 + margin,
            MapEntity.position_z >= tile_z0 - margin,
            MapEntity.position_z <= tile_z1 + margin,
        )
    )
    result = await db.execute(stmt)
    return [(float(px), float(pz), float(sx), float(sz), cat) for px, pz, sx, sz, cat in result.all()]


async def generate_vegetation_real_tiles(
    db: Any, game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    from sqlalchemy import select
    from backend.app.map.model.map import MapEntity

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'vegetation_real')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    stmt = (
        select(MapEntity.position_x, MapEntity.position_z, MapEntity.size_x, MapEntity.size_z, MapEntity.category)
        .where(MapEntity.map_id == game_map.id, MapEntity.category.in_(TERRAIN_VEG_CATEGORIES))
    )
    result = await db.execute(stmt)
    all_entities = [(float(px), float(pz), float(sx), float(sz), cat) for px, pz, sx, sz, cat in result.all()]
    log.info('vegetation_real: %d entities, %d tiles', len(all_entities), len(tasks))

    sx, sz = game_map.size_x, game_map.size_z

    def _assign_entities():
        _assign_entities_via_grid(all_entities, tasks, sx, sz)

    await asyncio.to_thread(_assign_entities)

    total = await _run_parallel(_worker_vegetation_real, tasks, max_workers, 'vegetation_real', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'vegetation_real'}


async def generate_buildings_real_tiles(
    db: Any, game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    from sqlalchemy import select
    from backend.app.map.model.map import MapEntity

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'buildings_real')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    stmt = (
        select(
            MapEntity.position_x, MapEntity.position_z,
            MapEntity.size_x, MapEntity.size_z,
            MapEntity.category, MapEntity.rotation,
            MapEntity.corners,
        )
        .where(
            MapEntity.map_id == game_map.id,
            MapEntity.category.in_(TERRAIN_BUILDING_CATEGORIES),
            MapEntity.size_x * MapEntity.size_z >= BUILDING_MIN_AREA,
        )
    )
    result = await db.execute(stmt)
    all_entities = [
        (float(px), float(pz), float(sx), float(sz), cat, float(rot or 0), corners)
        for px, pz, sx, sz, cat, rot, corners in result.all()
    ]
    log.info('buildings_real: %d entities, %d tiles', len(all_entities), len(tasks))

    sx, sz = game_map.size_x, game_map.size_z

    def _assign_entities():
        _assign_entities_via_grid(all_entities, tasks, sx, sz, margin_min=50.0)

    await asyncio.to_thread(_assign_entities)

    total = await _run_parallel(_worker_buildings_real, tasks, max_workers, 'buildings_real', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'buildings_real'}


async def generate_roads_tiles(
    db: Any, game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    from sqlalchemy import select
    from backend.app.map.model.map import MapRoad

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'roads')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    stmt = select(MapRoad.points, MapRoad.type, MapRoad.width).where(MapRoad.map_id == game_map.id)
    result = await db.execute(stmt)
    all_roads = [(pts, rtype or 'track', float(w or 4.0)) for pts, rtype, w in result.all()]

    for t in tasks:
        t.update(size_x=game_map.size_x, size_z=game_map.size_z, roads=all_roads)

    total = await _run_parallel(_worker_roads, tasks, max_workers, 'roads', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'roads'}


async def generate_features_tiles(
    db: Any, game_map: GameMap, output_dir: str, max_workers: int = 4,
) -> dict:
    from sqlalchemy import select
    from backend.app.map.model.map import MapEntity

    tile_dir = _prepare_output_dir(output_dir, game_map.id, 'features')
    tasks = _tile_tasks(game_map.size_x, game_map.size_z, tile_dir)

    stmt = (
        select(MapEntity.position_x, MapEntity.position_z, MapEntity.size_x, MapEntity.size_z, MapEntity.category)
        .where(MapEntity.map_id == game_map.id, MapEntity.category.in_(TERRAIN_FEATURE_CATEGORIES))
    )
    result = await db.execute(stmt)
    all_entities = [(float(px), float(pz), float(sx), float(sz), cat) for px, pz, sx, sz, cat in result.all()]
    log.info('features: %d entities, %d tiles', len(all_entities), len(tasks))

    sx, sz = game_map.size_x, game_map.size_z

    def _assign_entities():
        _assign_entities_via_grid(all_entities, tasks, sx, sz)

    await asyncio.to_thread(_assign_entities)

    total = await _run_parallel(_worker_features, tasks, max_workers, 'features', map_id=game_map.id)
    return {'total_tiles': total, 'layer': 'features'}


LAYER_GENERATORS = {
    'vegetation': generate_vegetation_tiles,
    'builtup': generate_builtup_tiles,
    'slope': generate_slope_tiles,
    'hillshade': generate_hillshade_tiles,
    'contours': generate_contour_tiles,
    'water': generate_water_tiles,
    'trafficability': generate_trafficability_tiles,
    'cover': generate_cover_tiles,
    'mcoo': generate_mcoo_tiles,
    'vegetation_real': generate_vegetation_real_tiles,
    'buildings_real': generate_buildings_real_tiles,
    'roads': generate_roads_tiles,
    'features': generate_features_tiles,
}

LAYERS_NEED_DB = {
    'vegetation', 'builtup', 'trafficability', 'cover', 'mcoo',
    'vegetation_real', 'buildings_real', 'roads', 'features',
}
