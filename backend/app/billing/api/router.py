from fastapi import APIRouter

from backend.app.billing.api.v1.usage import router as usage_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)
v1.include_router(usage_router, prefix='/usage', tags=['用量统计'])
