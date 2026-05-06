"""Thematic layer API endpoints — ADR-040 dual-mode (Human + LLM)."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.map.crud.crud_map import map_dao
from backend.app.map.service import thematic_layers as tl
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession

router = APIRouter(dependencies=[DependsJwtAuth])


async def _get_map(db: CurrentSession, map_id: int):
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')
    return game_map


@router.get('/maps/{map_id}/thematic/vegetation')
async def get_vegetation_density(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    cell_size: Annotated[float, Query(ge=10, le=1000, description='Grid cell size in meters')] = 100,
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = await tl.vegetation_density(db, game_map, cell_size)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/thematic/builtup')
async def get_builtup_area(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    cell_size: Annotated[float, Query(ge=10, le=1000, description='Grid cell size in meters')] = 200,
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = await tl.builtup_area(db, game_map, cell_size)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/thematic/contours')
async def get_contour_lines(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    interval: Annotated[float, Query(ge=5, le=200, description='Contour interval in meters')] = 20,
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = tl.contour_lines(game_map, interval)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/thematic/slope')
async def get_slope_map(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = tl.slope_map(game_map)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/thematic/water')
async def get_water_bodies(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = tl.water_bodies(game_map)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/thematic/viewshed')
async def get_viewshed(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    x: Annotated[float, Query(description='Observer world X coordinate')],
    z: Annotated[float, Query(description='Observer world Z coordinate')],
    height: Annotated[float, Query(ge=0, le=100, description='Observer height above ground (m)')] = 1.8,
    max_range: Annotated[float, Query(ge=100, le=10000, description='Max viewshed range (m)')] = 2000,
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = tl.viewshed(game_map, x, z, height, max_range)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/thematic/los')
async def get_line_of_sight(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    from_x: Annotated[float, Query(description='From world X')],
    from_z: Annotated[float, Query(description='From world Z')],
    to_x: Annotated[float, Query(description='To world X')],
    to_z: Annotated[float, Query(description='To world Z')],
    height: Annotated[float, Query(ge=0, le=100, description='Observer height above ground (m)')] = 1.8,
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = tl.line_of_sight(game_map, from_x, from_z, to_x, to_z, height)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/thematic/trafficability')
async def get_trafficability(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    cell_size: Annotated[float, Query(ge=10, le=1000, description='Grid cell size in meters')] = 100,
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = await tl.trafficability(db, game_map, cell_size)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/thematic/cover')
async def get_cover_concealment(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    cell_size: Annotated[float, Query(ge=10, le=1000, description='Grid cell size in meters')] = 100,
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = await tl.cover_concealment(db, game_map, cell_size)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/thematic/hillshade')
async def get_hillshade(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    azimuth: Annotated[float, Query(ge=0, le=360, description='Sun azimuth in degrees (315=NW)')] = 315,
    altitude: Annotated[float, Query(ge=5, le=90, description='Sun altitude in degrees')] = 45,
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = tl.hillshade(game_map, azimuth, altitude)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/thematic/mcoo')
async def get_mcoo(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    cell_size: Annotated[float, Query(ge=10, le=1000, description='Grid cell size in meters')] = 100,
    mode: Annotated[str, Query(description='Output mode: human, llm, or both')] = 'both',
) -> ResponseSchemaModel:
    game_map = await _get_map(db, map_id)
    result = await tl.mcoo(db, game_map, cell_size)
    return response_base.success(data=_filter_mode(result, mode))


@router.get('/maps/{map_id}/heightmap')
async def get_heightmap(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    resolution: Annotated[int, Query(ge=50, le=500, description='Target resolution in meters')] = 100,
) -> ResponseSchemaModel:
    """Return a downsampled height grid for frontend cursor elevation display."""
    game_map = await _get_map(db, map_id)
    hg = game_map.height_grid_data
    if not hg:
        return response_base.success(data=None)

    src_res = game_map.height_grid_resolution or 100
    src_rows = len(hg)
    src_cols = len(hg[0]) if hg else 0

    step = max(1, round(resolution / src_res))
    out_rows = (src_rows + step - 1) // step
    out_cols = (src_cols + step - 1) // step

    grid: list[list[float]] = []
    for r in range(out_rows):
        row: list[float] = []
        sr = min(r * step, src_rows - 1)
        for c in range(out_cols):
            sc = min(c * step, src_cols - 1)
            row.append(round(hg[sr][sc], 1))
        grid.append(row)

    return response_base.success(data={
        'resolution': step * src_res,
        'rows': out_rows,
        'cols': out_cols,
        'grid': grid,
    })


def _filter_mode(result: dict, mode: str) -> dict:
    if mode == 'human':
        return {'layer_type': result['layer_type'], 'human': result.get('human')}
    if mode == 'llm':
        return {'layer_type': result['layer_type'], 'llm': result.get('llm')}
    return result
