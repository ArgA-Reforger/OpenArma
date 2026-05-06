"""MGRS-style grid coordinate system for maps.

Provides conversion between three coordinate spaces:
- **MGRS grid**: e.g. (045, 072) with configurable digit precision
- **World (meters)**: absolute position in meters from map origin
- **Pixel**: position on a layer image

Grid origin is bottom-left (0, 0). Easting increases right, northing increases up.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class MapGeometry:
    """Immutable snapshot of a map canvas's coordinate geometry."""

    size_x: float
    size_z: float
    offset_x: float = 0.0
    offset_z: float = 0.0


@dataclass(frozen=True)
class LayerGeometry:
    """Geometry of a single layer on the canvas."""

    image_width_px: int
    image_height_px: int
    bound_left: float
    bound_bottom: float
    bound_right: float
    bound_top: float


MGRS_RESOLUTION = {4: 1000, 6: 100, 8: 10, 10: 1}


def grid_resolution(canvas_size: float, digits: int) -> float:
    """Meters per grid unit. E.g. 6-digit = 100m per unit."""
    return float(MGRS_RESOLUTION.get(digits, 100))


def grid_max(digits: int) -> int:
    """Maximum grid value (exclusive). For 6-digit coords -> 1000."""
    return 10 ** (digits // 2)


def mgrs_to_world(geo: MapGeometry, easting: int, northing: int, digits: int) -> tuple[float, float]:
    """Convert MGRS grid coordinates to world coordinates (meters)."""
    res = grid_resolution(geo.size_x, digits)
    world_x = easting * res + geo.offset_x
    world_z = northing * res + geo.offset_z
    return (world_x, world_z)


def world_to_mgrs(geo: MapGeometry, world_x: float, world_z: float, digits: int) -> tuple[int, int]:
    """Convert world coordinates (meters) to MGRS grid coordinates."""
    res = grid_resolution(geo.size_x, digits)
    easting = max(0, int((world_x - geo.offset_x) / res))
    northing = max(0, int((world_z - geo.offset_z) / res))
    return (easting, northing)


def pixel_to_world(layer: LayerGeometry, pixel_x: float, pixel_y: float) -> tuple[float, float]:
    """Convert pixel coordinates on a layer image to world coordinates.

    Pixel origin is top-left; world origin is bottom-left.
    """
    layer_w = layer.bound_right - layer.bound_left
    layer_h = layer.bound_top - layer.bound_bottom
    world_x = (pixel_x / layer.image_width_px) * layer_w + layer.bound_left
    world_z = (1.0 - pixel_y / layer.image_height_px) * layer_h + layer.bound_bottom
    return (world_x, world_z)


def world_to_pixel(layer: LayerGeometry, world_x: float, world_z: float) -> tuple[float, float]:
    """Convert world coordinates to pixel coordinates on a layer image."""
    layer_w = layer.bound_right - layer.bound_left
    layer_h = layer.bound_top - layer.bound_bottom
    pixel_x = ((world_x - layer.bound_left) / layer_w) * layer.image_width_px
    pixel_y = (1.0 - (world_z - layer.bound_bottom) / layer_h) * layer.image_height_px
    return (pixel_x, pixel_y)


def pixel_to_mgrs(
    layer: LayerGeometry, geo: MapGeometry, pixel_x: float, pixel_y: float, digits: int,
) -> tuple[int, int]:
    """Convert pixel coordinates on a layer to MGRS grid coordinates."""
    world_x, world_z = pixel_to_world(layer, pixel_x, pixel_y)
    return world_to_mgrs(geo, world_x, world_z, digits)


def mgrs_to_pixel(
    layer: LayerGeometry, geo: MapGeometry, easting: int, northing: int, digits: int,
) -> tuple[float, float]:
    """Convert MGRS grid coordinates to pixel coordinates on a layer."""
    world_x, world_z = mgrs_to_world(geo, easting, northing, digits)
    return world_to_pixel(layer, world_x, world_z)


def format_mgrs(easting: int, northing: int, digits: int) -> str:
    """Format MGRS coordinates as a padded string, e.g. '045 072'."""
    half = digits // 2
    fmt = f'{{:0{half}d}}'
    return f'{fmt.format(easting)} {fmt.format(northing)}'


def distance_world(x1: float, z1: float, x2: float, z2: float) -> float:
    """Euclidean distance between two world positions."""
    return math.sqrt((x1 - x2) ** 2 + (z1 - z2) ** 2)


def geometry_from_map(game_map) -> MapGeometry:
    """Build MapGeometry from a GameMap ORM instance."""
    return MapGeometry(
        size_x=game_map.size_x,
        size_z=game_map.size_z,
        offset_x=game_map.offset_x,
        offset_z=game_map.offset_z,
    )
