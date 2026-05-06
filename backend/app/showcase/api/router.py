from fastapi import APIRouter

from backend.app.showcase.api.v1.showcase import router as showcase_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)
v1.include_router(showcase_router, prefix='/showcase', tags=['展示区'])
