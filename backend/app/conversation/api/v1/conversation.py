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


@router.post('/{pid}/conversations', summary='创建对话', dependencies=[DependsJwtAuth])
async def create_conversation(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    obj: CreateConversationParam,
) -> ResponseSchemaModel[GetConversationDetail]:
    data = await conversation_service.create(
        db=db, project_id=pid, obj=obj, user_id=request.user.id
    )
    return response_base.success(data=data)


@router.get(
    '/{pid}/conversations',
    summary='对话列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_conversations(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    status: Annotated[str | None, Query(description='状态')] = None,
) -> ResponseSchemaModel[PageData[GetConversationDetail]]:
    page_data = await conversation_service.get_list(
        db=db, project_id=pid, user_id=request.user.id, status=status
    )
    return response_base.success(data=page_data)


@router.get('/{pid}/conversations/{pk}', summary='对话详情', dependencies=[DependsJwtAuth])
async def get_conversation(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    pk: Annotated[int, Path(description='对话 ID')],
) -> ResponseSchemaModel[GetConversationDetail]:
    data = await conversation_service.get(db=db, project_id=pid, pk=pk, user_id=request.user.id)
    return response_base.success(data=data)


@router.put('/{pid}/conversations/{pk}', summary='更新对话', dependencies=[DependsJwtAuth])
async def update_conversation(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    pk: Annotated[int, Path(description='对话 ID')],
    obj: UpdateConversationParam,
) -> ResponseModel:
    count = await conversation_service.update(
        db=db, project_id=pid, pk=pk, user_id=request.user.id, obj=obj
    )
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/{pid}/conversations/{pk}', summary='删除对话', dependencies=[DependsJwtAuth])
async def delete_conversation(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    pk: Annotated[int, Path(description='对话 ID')],
) -> ResponseModel:
    count = await conversation_service.delete(
        db=db, project_id=pid, pk=pk, user_id=request.user.id
    )
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{pid}/conversations/{pk}/share', summary='分享对话', dependencies=[DependsJwtAuth])
async def share_conversation(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    pk: Annotated[int, Path(description='对话 ID')],
) -> ResponseSchemaModel[ShareConversationResponse]:
    share_code = await conversation_service.share(
        db=db, project_id=pid, pk=pk, user_id=request.user.id
    )
    base_url = str(request.base_url).rstrip('/')
    share_url = f'{base_url}/shared/{share_code}'
    return response_base.success(data=ShareConversationResponse(share_code=share_code, share_url=share_url))


@router.delete('/{pid}/conversations/{pk}/share', summary='取消分享', dependencies=[DependsJwtAuth])
async def unshare_conversation(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    pk: Annotated[int, Path(description='对话 ID')],
) -> ResponseModel:
    await conversation_service.unshare(db=db, project_id=pid, pk=pk, user_id=request.user.id)
    return response_base.success()


@router.get(
    '/{pid}/conversations/{cid}/messages',
    summary='获取历史消息',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_messages(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    after: Annotated[int | None, Query(description='只返回 ID 大于此值的消息（增量拉取）')] = None,
) -> ResponseSchemaModel[PageData[GetMessageDetail]]:
    page_data = await conversation_service.get_messages(
        db=db, project_id=pid, conversation_id=cid, user_id=request.user.id,
        after_id=after,
    )
    return response_base.success(data=page_data)


@router.put(
    '/{pid}/conversations/{cid}/messages/{mid}',
    summary='更新消息',
    dependencies=[DependsJwtAuth],
)
async def update_message(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    mid: Annotated[int, Path(description='消息 ID')],
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
    summary='编辑消息并截断后续（DeepSeek 模式）',
    dependencies=[DependsJwtAuth],
)
async def edit_and_resend(
    request: Request,
    db: CurrentSessionTransaction,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    mid: Annotated[int, Path(description='消息 ID')],
    obj: SendMessageParam,
) -> ResponseSchemaModel[dict]:
    content = await conversation_service.edit_and_truncate(
        db=db, project_id=pid, conversation_id=cid,
        message_id=mid, user_id=request.user.id, new_content=obj.content,
    )
    return response_base.success(data={'content': content})


@router.delete(
    '/{pid}/conversations/{cid}/messages/{mid}',
    summary='删除消息',
    dependencies=[DependsJwtAuth],
)
async def delete_message(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    mid: Annotated[int, Path(description='消息 ID')],
) -> ResponseModel:
    count = await conversation_service.delete_message(
        db=db, project_id=pid, conversation_id=cid, message_id=mid, user_id=request.user.id
    )
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post(
    '/{pid}/conversations/{cid}/generate-title',
    summary='AI 生成对话标题',
    dependencies=[DependsJwtAuth],
)
async def generate_conversation_title(
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
) -> ResponseSchemaModel[dict]:
    title = await chat_service.generate_title(
        project_id=pid, conversation_id=cid, user_id=request.user.id
    )
    return response_base.success(data={'title': title})


@router.get(
    '/{pid}/conversations/{cid}/branches',
    summary='获取对话的所有分支信息',
    dependencies=[DependsJwtAuth],
)
async def get_conversation_branches(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
) -> ResponseSchemaModel[dict]:
    from backend.app.conversation.crud.crud_message import message_dao as msg_dao
    branch_counts = await msg_dao.get_branch_counts(db, cid)
    return response_base.success(data={'branches': branch_counts})


@router.get(
    '/{pid}/conversations/{cid}/messages/{mid}/branches',
    summary='获取消息的所有分支',
    dependencies=[DependsJwtAuth],
)
async def get_message_branches(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    mid: Annotated[int, Path(description='用户消息 ID')],
) -> ResponseSchemaModel[dict]:
    data = await conversation_service.get_message_branches(
        db=db, project_id=pid, conversation_id=cid,
        message_id=mid, user_id=request.user.id,
    )
    return response_base.success(data=data)


@router.post(
    '/{pid}/conversations/{cid}/messages/{mid}/switch-branch',
    summary='切换消息分支',
    dependencies=[DependsJwtAuth],
)
async def switch_message_branch(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    mid: Annotated[int, Path(description='用户消息 ID')],
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
    summary='发送消息（SSE 流式响应）',
    dependencies=[DependsJwtAuth],
)
async def send_message(
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    obj: SendMessageParam,
) -> StreamingResponse:
    return _build_sse_response(pid, cid, request.user.id, obj.content, resend=False)


@router.post(
    '/{pid}/conversations/{cid}/resend',
    summary='重新生成 AI 回复（SSE 流式响应）',
    dependencies=[DependsJwtAuth],
)
async def resend_message(
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    obj: SendMessageParam,
) -> StreamingResponse:
    return _build_sse_response(pid, cid, request.user.id, obj.content, resend=True)


@router.get(
    '/{pid}/conversations/{cid}/resources',
    summary='对话绑定的资源列表',
    dependencies=[DependsJwtAuth],
)
async def get_conversation_resources(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    resource_type: Annotated[str | None, Query(description='资源类型 knowledge_base/mcp_server')] = None,
) -> ResponseSchemaModel[list[dict]]:
    data = await conversation_service.get_resources(
        db=db, project_id=pid, conversation_id=cid, user_id=request.user.id, resource_type=resource_type
    )
    return response_base.success(data=data)


@router.post(
    '/{pid}/conversations/{cid}/resources',
    summary='绑定资源到对话',
    dependencies=[DependsJwtAuth],
)
async def bind_conversation_resource(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    resource_type: Annotated[str, Query(description='资源类型 knowledge_base/mcp_server')],
    resource_id: Annotated[int, Query(description='资源 ID')],
) -> ResponseModel:
    await conversation_service.bind_resource(
        db=db, project_id=pid, conversation_id=cid,
        user_id=request.user.id, resource_type=resource_type, resource_id=resource_id,
    )
    return response_base.success()


@router.delete(
    '/{pid}/conversations/{cid}/resources',
    summary='解绑对话资源',
    dependencies=[DependsJwtAuth],
)
async def unbind_conversation_resource(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    cid: Annotated[int, Path(description='对话 ID')],
    resource_type: Annotated[str, Query(description='资源类型 knowledge_base/mcp_server')],
    resource_id: Annotated[int, Query(description='资源 ID')],
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
