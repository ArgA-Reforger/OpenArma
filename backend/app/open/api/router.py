from fastapi import APIRouter

from backend.app.open.api.v1.admin import router as admin_router
from backend.app.open.api.v1.arma_config import router as arma_config_router
from backend.app.open.api.v1.command import router as command_router
from backend.app.open.api.v1.replay import router as replay_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(command_router, prefix='/open', tags=['Open API'])
v1.include_router(admin_router, prefix='/open/admin', tags=['Open API Admin'])
v1.include_router(arma_config_router, prefix='/open/admin', tags=['Arma Config'])
v1.include_router(replay_router, prefix='/open/admin', tags=['Battle Replay'])
