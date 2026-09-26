from typing import Annotated

from fastapi import APIRouter, Path, Query, Request
from fastapi.responses import StreamingResponse

from backend.app.conversation.schema.conversation import (
    CreateConversationParam,
    GetConversationDetail,
    ShareConversationResponse,
    UpdateConversationParam,
)
from backend.app.conversation.schema.message import GetMessageDetail, SendMessageParam, SwitchBranchParam, UpdateMessageParam
from backend.app.conversation.service.chat_service import chat_service
from backend.app.conversation.service.conversation_service import conversation_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.post('/{pid}/conversations', summary='Create conversation', dependencies=[DependsJwtAuth])
async def create_conversation(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    obj: CreateConversationParam,
) -> ResponseSchemaModel[GetConversationDetail]:
    data = await conversation_service.create(
        db=db, project_id=pid, obj=obj, user_id=request.user.id
    )
    return response_base.success(data=data)


@router.get(
    '/{pid}/conversations',
    summary='Conversation list',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_conversations(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    status: Annotated[str | None, Query(description='Status')] = None,
) -> ResponseSchemaModel[PageData[GetConversationDetail]]:
    page_data = await conversation_service.get_list(
        db=db, project_id=pid, user_id=request.user.id, status=status
    )
    return response_base.success(data=page_data)


@router.get('/{pid}/conversations/{pk}', summary='Conversation details', dependencies=[DependsJwtAuth])
async def get_conversation(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    pk: Annotated[int, Path(description='Conversation ID')],
) -> ResponseSchemaModel[GetConversationDetail]:
    data = await conversation_service.get(db=db, project_id=pid, pk=pk, user_id=request.user.id)
    return response_base.success(data=data)


@router.put('/{pid}/conversations/{pk}', summary='Update conversation', dependencies=[DependsJwtAuth])
async def update_conversation(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    pk: Annotated[int, Path(description='Conversation ID')],
    obj: UpdateConversationParam,
) -> ResponseModel:
    count = await conversation_service.update(
        db=db, project_id=pid, pk=pk, user_id=request.user.id, obj=obj
    )
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/{pid}/conversations/{pk}', summary='Delete conversation', dependencies=[DependsJwtAuth])
async def delete_conversation(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    pk: Annotated[int, Path(description='Conversation ID')],
) -> ResponseModel:
    count = await conversation_service.delete(
        db=db, project_id=pid, pk=pk, user_id=request.user.id
    )
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{pid}/conversations/{pk}/share', summary='Share conversation', dependencies=[DependsJwtAuth])
async def share_conversation(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    pk: Annotated[int, Path(description='Conversation ID')],
) -> ResponseSchemaModel[ShareConversationResponse]:
    share_code = await conversation_service.share(
        db=db, project_id=pid, pk=pk, user_id=request.user.id
    )
    base_url = str(request.base_url).rstrip('/')
    share_url = f'{base_url}/shared/{share_code}'
    return response_base.success(data=ShareConversationResponse(share_code=share_code, share_url=share_url))


@router.delete('/{pid}/conversations/{pk}/share', summary='Unshare', dependencies=[DependsJwtAuth])
async def unshare_conversation(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    pk: Annotated[int, Path(description='Conversation ID')],
) -> ResponseModel:
    await conversation_service.unshare(db=db, project_id=pid, pk=pk, user_id=request.user.id)
    return response_base.success()


@router.get(
    '/{pid}/conversations/{cid}/messages',
    summary='Get message history',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_messages(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    after: Annotated[
        int | None,
        Query(description='Only return messages with an ID greater than this value (incremental fetch)'),
    ] = None,
) -> ResponseSchemaModel[PageData[GetMessageDetail]]:
    page_data = await conversation_service.get_messages(
        db=db, project_id=pid, conversation_id=cid, user_id=request.user.id,
        after_id=after,
    )
    return response_base.success(data=page_data)


@router.put(
    '/{pid}/conversations/{cid}/messages/{mid}',
    summary='Update message',
    dependencies=[DependsJwtAuth],
)
async def update_message(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    mid: Annotated[int, Path(description='Message ID')],
    obj: UpdateMessageParam,
) -> ResponseModel:
    count = await conversation_service.update_message(
        db=db, project_id=pid, conversation_id=cid, message_id=mid, user_id=request.user.id, obj=obj
    )
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post(
    '/{pid}/conversations/{cid}/messages/{mid}/edit-and-resend',
    summary='Edit a message and truncate what follows (DeepSeek mode)',
    dependencies=[DependsJwtAuth],
)
async def edit_and_resend(
    request: Request,
    db: CurrentSessionTransaction,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    mid: Annotated[int, Path(description='Message ID')],
    obj: SendMessageParam,
) -> ResponseSchemaModel[dict]:
    content = await conversation_service.edit_and_truncate(
        db=db, project_id=pid, conversation_id=cid,
        message_id=mid, user_id=request.user.id, new_content=obj.content,
    )
    return response_base.success(data={'content': content})


@router.delete(
    '/{pid}/conversations/{cid}/messages/{mid}',
    summary='Delete message',
    dependencies=[DependsJwtAuth],
)
async def delete_message(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    mid: Annotated[int, Path(description='Message ID')],
) -> ResponseModel:
    count = await conversation_service.delete_message(
        db=db, project_id=pid, conversation_id=cid, message_id=mid, user_id=request.user.id
    )
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post(
    '/{pid}/conversations/{cid}/generate-title',
    summary='AI-generate conversation title',
    dependencies=[DependsJwtAuth],
)
async def generate_conversation_title(
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
) -> ResponseSchemaModel[dict]:
    title = await chat_service.generate_title(
        project_id=pid, conversation_id=cid, user_id=request.user.id
    )
    return response_base.success(data={'title': title})


@router.get(
    '/{pid}/conversations/{cid}/branches',
    summary='Get all branch info for the conversation',
    dependencies=[DependsJwtAuth],
)
async def get_conversation_branches(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
) -> ResponseSchemaModel[dict]:
    from backend.app.conversation.crud.crud_message import message_dao as msg_dao
    branch_counts = await msg_dao.get_branch_counts(db, cid)
    return response_base.success(data={'branches': branch_counts})


@router.get(
    '/{pid}/conversations/{cid}/messages/{mid}/branches',
    summary='Get all branches of the message',
    dependencies=[DependsJwtAuth],
)
async def get_message_branches(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    mid: Annotated[int, Path(description='User message ID')],
) -> ResponseSchemaModel[dict]:
    data = await conversation_service.get_message_branches(
        db=db, project_id=pid, conversation_id=cid,
        message_id=mid, user_id=request.user.id,
    )
    return response_base.success(data=data)


@router.post(
    '/{pid}/conversations/{cid}/messages/{mid}/switch-branch',
    summary='Switch message branch',
    dependencies=[DependsJwtAuth],
)
async def switch_message_branch(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    mid: Annotated[int, Path(description='User message ID')],
    obj: SwitchBranchParam,
) -> ResponseModel:
    count = await conversation_service.switch_message_branch(
        db=db, project_id=pid, conversation_id=cid,
        message_id=mid, target_branch_id=obj.target_branch_id,
        user_id=request.user.id,
    )
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post(
    '/{pid}/conversations/{cid}/messages',
    summary='Send message (SSE streaming response)',
    dependencies=[DependsJwtAuth],
)
async def send_message(
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    obj: SendMessageParam,
) -> StreamingResponse:
    return _build_sse_response(pid, cid, request.user.id, obj.content, resend=False)


@router.post(
    '/{pid}/conversations/{cid}/resend',
    summary='Regenerate AI reply (SSE streaming response)',
    dependencies=[DependsJwtAuth],
)
async def resend_message(
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    obj: SendMessageParam,
) -> StreamingResponse:
    return _build_sse_response(pid, cid, request.user.id, obj.content, resend=True)


@router.get(
    '/{pid}/conversations/{cid}/resources',
    summary='List of resources bound to the conversation',
    dependencies=[DependsJwtAuth],
)
async def get_conversation_resources(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    resource_type: Annotated[str | None, Query(description='Resource type knowledge_base/mcp_server')] = None,
) -> ResponseSchemaModel[list[dict]]:
    data = await conversation_service.get_resources(
        db=db, project_id=pid, conversation_id=cid, user_id=request.user.id, resource_type=resource_type
    )
    return response_base.success(data=data)


@router.post(
    '/{pid}/conversations/{cid}/resources',
    summary='Bind a resource to the conversation',
    dependencies=[DependsJwtAuth],
)
async def bind_conversation_resource(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    resource_type: Annotated[str, Query(description='Resource type knowledge_base/mcp_server')],
    resource_id: Annotated[int, Query(description='Resource ID')],
) -> ResponseModel:
    await conversation_service.bind_resource(
        db=db, project_id=pid, conversation_id=cid,
        user_id=request.user.id, resource_type=resource_type, resource_id=resource_id,
    )
    return response_base.success()


@router.delete(
    '/{pid}/conversations/{cid}/resources',
    summary='Unbind a conversation resource',
    dependencies=[DependsJwtAuth],
)
async def unbind_conversation_resource(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    cid: Annotated[int, Path(description='Conversation ID')],
    resource_type: Annotated[str, Query(description='Resource type knowledge_base/mcp_server')],
    resource_id: Annotated[int, Query(description='Resource ID')],
) -> ResponseModel:
    count = await conversation_service.unbind_resource(
        db=db, project_id=pid, conversation_id=cid,
        user_id=request.user.id, resource_type=resource_type, resource_id=resource_id,
    )
    if count > 0:
        return response_base.success()
    return response_base.fail()


def _build_sse_response(
    pid: int, cid: int, user_id: int, content: str, *, resend: bool
) -> StreamingResponse:
    import json

    async def event_stream():
        try:
            async for token in chat_service.send_message_stream(
                project_id=pid,
                conversation_id=cid,
                user_id=user_id,
                content=content,
                resend=resend,
            ):
                yield f'data: {token}\n\n'
            yield 'data: [DONE]\n\n'
        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )
