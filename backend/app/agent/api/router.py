from fastapi import APIRouter

from backend.app.agent.api.v1.agent import router as agent_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)
v1.include_router(agent_router, prefix='/agents', tags=['智能体'])
