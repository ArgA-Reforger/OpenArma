from fastapi import APIRouter

from backend.app.builtin_tool.api.v1.builtin_tool import router as builtin_tool_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)
v1.include_router(builtin_tool_router, prefix='/builtin-tools', tags=['内置工具'])
