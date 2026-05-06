"""地图图层图片上传 API。

上传图层图片后存储到 static/upload/maps/{map_id}/layers/{layer_id}/。
支持 TGA/PNG/JPG/WEBP，TGA 自动转换为高质量 PNG。
"""

import io
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Path, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageFile

Image.MAX_IMAGE_PIXELS = 100_000_000
ImageFile.LOAD_TRUNCATED_IMAGES = False
MAX_UPLOAD_BYTES = 200 * 1024 * 1024

from backend.app.map.crud.crud_map import layer_dao, map_dao
from backend.app.map.model.map import MapLayer
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth, DependsSuperUser
from backend.core.path_conf import UPLOAD_DIR
from backend.database.db import CurrentSession

router = APIRouter(dependencies=[DependsJwtAuth])
public_router = APIRouter()

MAP_IMAGE_DIR = UPLOAD_DIR / 'maps'
TILE_DIR = UPLOAD_DIR / 'maps'

SUPPORTED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'tga', 'bmp'}
CONVERT_TO_PNG = {'tga', 'bmp'}


def _get_layer_image_dir(map_id: int, layer_id: int) -> str:
    d = MAP_IMAGE_DIR / str(map_id) / 'layers' / str(layer_id)
    os.makedirs(d, exist_ok=True)
    return str(d)


@router.post('/maps/{map_id}/layers/{layer_id}/image', dependencies=[DependsSuperUser])
async def upload_layer_image(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    layer_id: Annotated[int, Path(description='Layer ID')],
    file: UploadFile,
) -> ResponseSchemaModel:
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')

    layer = await layer_dao.get(db, layer_id)
    if not layer or layer.map_id != map_id:
        raise errors.NotFoundError(msg='Layer not found')

    ext = (file.filename or 'layer.png').rsplit('.', 1)[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise errors.RequestError(msg=f'Unsupported image format: {ext}')

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise errors.RequestError(msg=f'Image too large (max {MAX_UPLOAD_BYTES // 1024 // 1024} MB)')
    img_dir = _get_layer_image_dir(map_id, layer_id)

    try:
        if ext in CONVERT_TO_PNG:
            img = Image.open(io.BytesIO(content))
            img.load()
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGBA')
            img_w, img_h = img.size
            filename = f'layer_{uuid.uuid4().hex[:8]}.png'
            filepath = os.path.join(img_dir, filename)
            img.save(filepath, format='PNG', compress_level=1)
            size_bytes = os.path.getsize(filepath)
        else:
            filename = f'layer_{uuid.uuid4().hex[:8]}.{ext}'
            filepath = os.path.join(img_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(content)
            size_bytes = len(content)
            img = Image.open(io.BytesIO(content))
            img.load()
            img_w, img_h = img.size
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise errors.RequestError(msg='Image is too large (possible decompression bomb)')
    except Exception as e:
        raise errors.RequestError(msg=f'Failed to process image: {e}')

    relative_path = f'maps/{map_id}/layers/{layer_id}/{filename}'

    stmt_update = (
        MapLayer.__table__.update()
        .where(MapLayer.id == layer_id)
        .values(image_path=relative_path, image_width_px=img_w, image_height_px=img_h)
    )
    await db.execute(stmt_update)
    await db.commit()

    return response_base.success(data={
        'image_path': relative_path,
        'url': f'/static/upload/{relative_path}',
        'size_bytes': size_bytes,
        'width_px': img_w,
        'height_px': img_h,
    })


@router.get('/maps/{map_id}/layers/{layer_id}/image')
async def get_layer_image(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
    layer_id: Annotated[int, Path(description='Layer ID')],
) -> FileResponse:
    layer = await layer_dao.get(db, layer_id)
    if not layer or layer.map_id != map_id or not layer.image_path:
        raise errors.NotFoundError(msg='Layer image not found')

    filepath = UPLOAD_DIR / layer.image_path
    if not os.path.exists(filepath):
        raise errors.NotFoundError(msg='Image file not found on disk')

    return FileResponse(str(filepath))


TILE_FILENAMES = ('tile.jpg', 'tile.png', 'tile.webp')


def _find_tile(map_id: int, z: int, x: int, y: int) -> str | None:
    """Locate a tile on disk. Compatible with EnfusionMapMaker's LODS/{z}/{x}/{y}/tile.jpg layout."""
    base = TILE_DIR / str(map_id) / 'tiles' / str(z) / str(x) / str(y)
    for fname in TILE_FILENAMES:
        p = base / fname
        if os.path.exists(p):
            return str(p)
    return None


def _find_military_tile(map_id: int, z: int, x: int, y: int) -> str | None:
    """Locate a military base map tile on disk."""
    base = TILE_DIR / str(map_id) / 'military_tiles' / str(z) / str(x) / str(y)
    for fname in TILE_FILENAMES:
        p = base / fname
        if os.path.exists(p):
            return str(p)
    return None


MEDIA_TYPES = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}


@public_router.get('/maps/{map_id}/tiles/{z}/{x}/{y}/tile.jpg')
async def get_satellite_tile(
    map_id: Annotated[int, Path(description='Map ID')],
    z: Annotated[int, Path(description='Zoom level (LOD)')],
    x: Annotated[int, Path(description='Tile X')],
    y: Annotated[int, Path(description='Tile Y')],
) -> FileResponse:
    """Serve satellite tile — disk-first lookup, no DB query per tile."""
    tile_path = _find_tile(map_id, z, x, y)
    if not tile_path:
        raise errors.NotFoundError(msg='Tile not found')

    ext = os.path.splitext(tile_path)[1].lower()
    resp = FileResponse(tile_path, media_type=MEDIA_TYPES.get(ext, 'image/jpeg'))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'public, max-age=604800, immutable'
    return resp


@public_router.get('/maps/{map_id}/military/{z}/{x}/{y}/tile.png')
async def get_military_tile(
    map_id: Annotated[int, Path(description='Map ID')],
    z: Annotated[int, Path(description='Zoom level (LOD)')],
    x: Annotated[int, Path(description='Tile X')],
    y: Annotated[int, Path(description='Tile Y')],
) -> FileResponse:
    """Serve military base map tile."""
    tile_path = _find_military_tile(map_id, z, x, y)
    if not tile_path:
        raise errors.NotFoundError(msg='Tile not found')

    ext = os.path.splitext(tile_path)[1].lower()
    resp = FileResponse(tile_path, media_type=MEDIA_TYPES.get(ext, 'image/png'))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'public, max-age=604800, immutable'
    return resp


ANALYSIS_LAYER_NAMES = (
    'vegetation', 'builtup', 'slope', 'hillshade',
    'contour', 'water', 'trafficability', 'cover', 'mcoo',
    'vegetation_real', 'buildings_real', 'roads', 'features',
)


def _find_analysis_tile(map_id: int, layer: str, z: int, x: int, y: int) -> str | None:
    base = TILE_DIR / str(map_id) / f'{layer}_tiles' / str(z) / str(x) / str(y)
    for fname in TILE_FILENAMES:
        p = base / fname
        if os.path.exists(p):
            return str(p)
    return None


@public_router.get('/maps/{map_id}/analysis/{layer}/{z}/{x}/{y}/tile.png')
async def get_analysis_tile(
    map_id: Annotated[int, Path(description='Map ID')],
    layer: Annotated[str, Path(description='Analysis layer name')],
    z: Annotated[int, Path(description='Zoom level')],
    x: Annotated[int, Path(description='Tile X')],
    y: Annotated[int, Path(description='Tile Y')],
) -> FileResponse:
    """Serve analysis overlay tile (transparent PNG)."""
    if layer not in ANALYSIS_LAYER_NAMES:
        raise errors.NotFoundError(msg=f'Unknown analysis layer: {layer}')

    tile_path = _find_analysis_tile(map_id, layer, z, x, y)
    if not tile_path:
        raise errors.NotFoundError(msg='Tile not found')

    ext = os.path.splitext(tile_path)[1].lower()
    resp = FileResponse(tile_path, media_type=MEDIA_TYPES.get(ext, 'image/png'))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'public, max-age=604800, immutable'
    return resp


@router.get('/maps/{map_id}/tiles/info')
async def get_tile_info(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    """Return satellite tile metadata: zoom range + available zoom levels on disk."""
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')

    tile_root = TILE_DIR / str(map_id) / 'tiles'
    available_zooms: list[int] = []
    overview_grid_size = 1
    if os.path.isdir(tile_root):
        for entry in sorted(os.listdir(tile_root)):
            if entry.isdigit() and os.path.isdir(tile_root / entry):
                available_zooms.append(int(entry))
        max_lod = max(available_zooms) if available_zooms else -1
        if max_lod >= 0:
            overview_dir = tile_root / str(max_lod)
            if os.path.isdir(overview_dir):
                overview_grid_size = len([d for d in os.listdir(overview_dir) if os.path.isdir(overview_dir / d)])

    military_root = TILE_DIR / str(map_id) / 'military_tiles'
    military_zooms: list[int] = []
    military_grid_size = 1
    has_military = os.path.isdir(military_root)
    if has_military:
        for entry in sorted(os.listdir(military_root)):
            if entry.isdigit() and os.path.isdir(military_root / entry):
                military_zooms.append(int(entry))
        if military_zooms:
            mil_max = max(military_zooms)
            mil_dir = military_root / str(mil_max)
            if os.path.isdir(mil_dir):
                military_grid_size = len([d for d in os.listdir(mil_dir) if os.path.isdir(mil_dir / d)])

    analysis_tiles: dict[str, dict] = {}
    for layer_name in ANALYSIS_LAYER_NAMES:
        layer_root = TILE_DIR / str(map_id) / f'{layer_name}_tiles'
        if os.path.isdir(layer_root):
            layer_zooms = sorted(
                int(e) for e in os.listdir(layer_root)
                if e.isdigit() and os.path.isdir(layer_root / e)
            )
            if layer_zooms:
                analysis_tiles[layer_name] = {
                    'ready': True,
                    'zooms': layer_zooms,
                    'url_template': f'/api/v1/maps/tiles/maps/{map_id}/analysis/{layer_name}/{{z}}/{{x}}/{{y}}/tile.png',
                }

    return response_base.success(data={
        'has_satellite_tiles': game_map.has_satellite_tiles,
        'tile_min_zoom': game_map.tile_min_zoom,
        'tile_max_zoom': game_map.tile_max_zoom,
        'available_zooms': available_zooms,
        'overview_grid_size': overview_grid_size,
        'tile_url_template': f'/api/v1/maps/tiles/maps/{map_id}/tiles/{{z}}/{{x}}/{{y}}/tile.jpg',
        'tile_dir_exists': os.path.isdir(tile_root),
        'tile_dir_path': str(tile_root),
        'has_military_tiles': has_military and len(military_zooms) > 0,
        'military_zooms': military_zooms,
        'military_grid_size': military_grid_size,
        'military_url_template': f'/api/v1/maps/tiles/maps/{map_id}/military/{{z}}/{{x}}/{{y}}/tile.png',
        'analysis_tiles': analysis_tiles,
    })


@router.post('/maps/{map_id}/tiles/create-dir', dependencies=[DependsSuperUser])
async def create_tile_directory(
    db: CurrentSession,
    map_id: Annotated[int, Path(description='Map ID')],
) -> ResponseSchemaModel:
    """Create the tile directory for manual file placement."""
    game_map = await map_dao.get(db, map_id)
    if not game_map:
        raise errors.NotFoundError(msg='Map not found')

    tile_root = TILE_DIR / str(map_id) / 'tiles'
    os.makedirs(tile_root, exist_ok=True)

    return response_base.success(data={
        'tile_dir_path': str(tile_root),
        'created': True,
    })
