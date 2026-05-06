from fastapi import APIRouter

from backend.app.topology.api.v1.topology import router as topology_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)
v1.include_router(topology_router, prefix='/topologies', tags=['拓扑编排'])
