from typing import Annotated

from fastapi import APIRouter, Path

from backend.app.conversation.service.conversation_service import conversation_service
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.database.db import CurrentSession

router = APIRouter()


@router.get('/{share_code}', summary='View shared conversation')
async def get_shared_conversation(
    db: CurrentSession,
    share_code: Annotated[str, Path(description='Share code')],
) -> ResponseSchemaModel:
    data = await conversation_service.get_shared(db=db, share_code=share_code)
    return response_base.success(data=data)
