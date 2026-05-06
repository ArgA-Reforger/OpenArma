from fastapi import APIRouter

from backend.app.llm.api.v1.llm_provider import router as llm_provider_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH, tags=['LLM'])

v1.include_router(llm_provider_router, prefix='/llm-providers')
