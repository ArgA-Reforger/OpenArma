from fastapi import APIRouter

from backend.app.knowledge.api.v1.knowledge_base import router as kb_router
from backend.app.knowledge.api.v1.knowledge_document import router as doc_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)
v1.include_router(kb_router, prefix='/knowledge-bases', tags=['Knowledge Bases'])
v1.include_router(doc_router, prefix='/knowledge-bases', tags=['Knowledge Base Documents'])
