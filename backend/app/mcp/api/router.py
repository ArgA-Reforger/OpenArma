from fastapi import APIRouter

from backend.app.mcp.api.v1.mcp_binding import router as binding_router
from backend.app.mcp.api.v1.mcp_server import router as server_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)
v1.include_router(server_router, prefix='/mcp-servers', tags=['MCP 服务器'])
v1.include_router(binding_router, prefix='/agents', tags=['Agent 工具绑定'])
