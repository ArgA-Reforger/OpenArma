from fastapi import APIRouter

from backend.app.map.api.v1.admin import router as admin_router
from backend.app.map.api.v1.image import public_router as tile_public_router
from backend.app.map.api.v1.image import router as image_router
from backend.app.map.api.v1.import_ import router as import_router
from backend.app.map.api.v1.thematic import router as thematic_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(admin_router, prefix='/maps/admin', tags=['Map Admin'])
v1.include_router(import_router, prefix='/maps/admin', tags=['Map Import'])
v1.include_router(image_router, prefix='/maps/admin', tags=['Map Image'])
v1.include_router(thematic_router, prefix='/maps/admin', tags=['Map Thematic Layers'])
v1.include_router(tile_public_router, prefix='/maps/tiles', tags=['Map Tiles (Public)'])
