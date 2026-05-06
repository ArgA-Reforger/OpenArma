from fastapi import APIRouter

from backend.app.project.api.v1.project import router as project_router
from backend.app.project.api.v1.topology import router as topology_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(project_router, prefix='/projects', tags=['项目'])
v1.include_router(topology_router, tags=['拓扑验证'])
