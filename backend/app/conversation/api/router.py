from fastapi import APIRouter

from backend.app.conversation.api.v1.conversation import router as conversation_router
from backend.app.conversation.api.v1.shared import router as shared_router
from backend.app.conversation.api.v1.shared_replay import router as shared_replay_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)
v1.include_router(conversation_router, prefix='/projects', tags=['Conversation Management'])
v1.include_router(shared_router, prefix='/shared', tags=['Shared Conversations'])
v1.include_router(shared_replay_router, prefix='/shared', tags=['Shared Replays'])
