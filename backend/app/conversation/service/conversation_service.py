import uuid

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.conversation.crud.crud_conversation import conversation_dao
from backend.app.conversation.crud.crud_conversation_resource import conversation_resource_dao
from backend.app.conversation.crud.crud_message import message_dao
from backend.app.conversation.model import Conversation
from backend.app.conversation.schema.conversation import CreateConversationParam, UpdateConversationParam
from backend.app.conversation.schema.message import UpdateMessageParam
from backend.app.project.crud.crud_project import project_dao
from backend.common.exception import errors
from backend.common.pagination import paging_data


class ConversationService:
    @staticmethod
    async def _check_project_owner(db: AsyncSession, project_id: int, user_id: int) -> None:
        project = await project_dao.get(db, project_id)
        if not project:
            raise errors.NotFoundError(msg='Project does not exist')
        if project.owner_id != user_id:
            raise errors.NotFoundError(msg='Project does not exist')

    @staticmethod
    async def create(
        *,
        db: AsyncSession,
        project_id: int,
        obj: CreateConversationParam,
        user_id: int,
    ) -> Conversation:
        await ConversationService._check_project_owner(db, project_id, user_id)
        return await conversation_dao.create(db, obj, project_id=project_id, user_id=user_id)

    @staticmethod
    async def get_list(
        *,
        db: AsyncSession,
        project_id: int,
        user_id: int,
        status: str | None = None,
    ) -> dict[str, Any]:
        await ConversationService._check_project_owner(db, project_id, user_id)
        select = await conversation_dao.get_list(project_id=project_id, user_id=user_id, status=status)
        return await paging_data(db, select)

    @staticmethod
    async def get(*, db: AsyncSession, project_id: int, pk: int, user_id: int) -> Conversation:
        await ConversationService._check_project_owner(db, project_id, user_id)
        obj = await conversation_dao.get(db, pk)
        if not obj:
            raise errors.NotFoundError(msg='Conversation does not exist')
        if obj.project_id != project_id:
            raise errors.NotFoundError(msg='Conversation does not exist')
        return obj

    @staticmethod
    async def update(
        *,
        db: AsyncSession,
        project_id: int,
        pk: int,
        user_id: int,
        obj: UpdateConversationParam,
    ) -> int:
        await ConversationService.get(db=db, project_id=project_id, pk=pk, user_id=user_id)
        return await conversation_dao.update(db, pk, obj)

    @staticmethod
    async def share(*, db: AsyncSession, project_id: int, pk: int, user_id: int) -> str:
        conv = await ConversationService.get(db=db, project_id=project_id, pk=pk, user_id=user_id)
        if conv.share_code:
            return conv.share_code
        share_code = str(uuid.uuid4())
        conv.share_code = share_code
        await db.flush()
        return share_code

    @staticmethod
    async def unshare(*, db: AsyncSession, project_id: int, pk: int, user_id: int) -> None:
        conv = await ConversationService.get(db=db, project_id=project_id, pk=pk, user_id=user_id)
        conv.share_code = None
        await db.flush()

    @staticmethod
    async def _build_conv_data(db: AsyncSession, conv: Conversation) -> dict[str, Any]:
        msgs = await message_dao.get_recent(db, conv.id, limit=200)
        return {
            'id': conv.id,
            'title': conv.title,
            'side': conv.side,
            'source': conv.source,
            'messages': [
                {
                    'id': m.id,
                    'role': m.role,
                    'content': m.content,
                    'created_time': str(m.created_time),
                    'metadata': m.metadata_,
                    'structured_data': m.structured_data,
                    'parent_message_id': m.parent_message_id,
                }
                for m in msgs
            ],
        }

    @staticmethod
    async def get_shared(*, db: AsyncSession, share_code: str) -> dict[str, Any]:
        conv = await conversation_dao.get_by_share_code(db, share_code)
        if not conv:
            raise errors.NotFoundError(msg='Share link does not exist or has expired')

        if conv.conversation_group_id:
            group_convs = await conversation_dao.get_by_group_id(db, conv.conversation_group_id)
            conversations = [
                await ConversationService._build_conv_data(db, c)
                for c in group_convs
            ]
        else:
            conversations = [await ConversationService._build_conv_data(db, conv)]

        return {
            'title': conv.title,
            'source': conv.source,
            'is_group': len(conversations) > 1,
            'conversations': conversations,
            'project_id': conv.project_id,
        }

    @staticmethod
    async def delete(*, db: AsyncSession, project_id: int, pk: int, user_id: int) -> int:
        await ConversationService.get(db=db, project_id=project_id, pk=pk, user_id=user_id)
        return await conversation_dao.delete(db, pk)

    @staticmethod
    async def get_messages(
        *,
        db: AsyncSession,
        project_id: int,
        conversation_id: int,
        user_id: int,
        after_id: int | None = None,
    ) -> dict[str, Any]:
        await ConversationService._check_project_owner(db, project_id, user_id)
        conv = await conversation_dao.get(db, conversation_id)
        if not conv:
            raise errors.NotFoundError(msg='Conversation does not exist')
        if conv.project_id != project_id:
            raise errors.NotFoundError(msg='Conversation does not exist')
        select = await message_dao.get_list(conversation_id=conversation_id, after_id=after_id)
        return await paging_data(db, select)

    @staticmethod
    async def update_message(
        *,
        db: AsyncSession,
        project_id: int,
        conversation_id: int,
        message_id: int,
        user_id: int,
        obj: UpdateMessageParam,
    ) -> int:
        await ConversationService._check_project_owner(db, project_id, user_id)
        conv = await conversation_dao.get(db, conversation_id)
        if not conv or conv.project_id != project_id:
            raise errors.NotFoundError(msg='Conversation does not exist')
        msg = await message_dao.get(db, message_id)
        if not msg or msg.conversation_id != conversation_id:
            raise errors.NotFoundError(msg='Message does not exist')
        return await message_dao.update(db, message_id, obj)

    @staticmethod
    async def delete_message(
        *,
        db: AsyncSession,
        project_id: int,
        conversation_id: int,
        message_id: int,
        user_id: int,
    ) -> int:
        await ConversationService._check_project_owner(db, project_id, user_id)
        conv = await conversation_dao.get(db, conversation_id)
        if not conv or conv.project_id != project_id:
            raise errors.NotFoundError(msg='Conversation does not exist')
        msg = await message_dao.get(db, message_id)
        if not msg or msg.conversation_id != conversation_id:
            raise errors.NotFoundError(msg='Message does not exist')
        return await message_dao.delete(db, message_id)

    @staticmethod
    async def get_message_branches(
        *,
        db: AsyncSession,
        project_id: int,
        conversation_id: int,
        message_id: int,
        user_id: int,
    ) -> dict:
        """Get all AI reply branches for a given user message."""
        await ConversationService._check_project_owner(db, project_id, user_id)
        conv = await conversation_dao.get(db, conversation_id)
        if not conv or conv.project_id != project_id:
            raise errors.NotFoundError(msg='Conversation does not exist')
        msg = await message_dao.get(db, message_id)
        if not msg or msg.conversation_id != conversation_id:
            raise errors.NotFoundError(msg='Message does not exist')

        branches = await message_dao.get_branches(db, conversation_id, message_id)

        from datetime import timedelta

        groups: list[dict] = []
        visited: set[int] = set()

        for branch in branches:
            if branch.id in visited:
                continue

            is_multi = branch.metadata_ and branch.metadata_.get('role') in ('agent', 'coordinator', 'aggregator')

            if is_multi:
                window = timedelta(seconds=5)
                group_msgs = []
                for b in branches:
                    if b.id not in visited and abs((b.created_time - branch.created_time).total_seconds()) < window.total_seconds():
                        group_msgs.append(b)
                        visited.add(b.id)

                group_msgs.sort(key=lambda x: (x.created_time, x.id))

                groups.append({
                    'id': group_msgs[0].id,
                    'messages': [
                        {
                            'id': m.id,
                            'role': m.role,
                            'content': m.content,
                            'metadata': m.metadata_,
                            'created_time': str(m.created_time),
                            'del_flag': m.del_flag,
                        }
                        for m in group_msgs
                    ],
                    'is_active': not group_msgs[0].del_flag,
                    'created_time': str(group_msgs[0].created_time),
                })
            else:
                visited.add(branch.id)
                groups.append({
                    'id': branch.id,
                    'messages': [{
                        'id': branch.id,
                        'role': branch.role,
                        'content': branch.content,
                        'metadata': branch.metadata_,
                        'created_time': str(branch.created_time),
                        'del_flag': branch.del_flag,
                    }],
                    'is_active': not branch.del_flag,
                    'created_time': str(branch.created_time),
                })

        active_idx = next((i for i, g in enumerate(groups) if g['is_active']), len(groups) - 1)

        return {
            'parent_message_id': message_id,
            'branches': groups,
            'active_index': active_idx,
            'total': len(groups),
        }

    @staticmethod
    async def switch_message_branch(
        *,
        db: AsyncSession,
        project_id: int,
        conversation_id: int,
        message_id: int,
        target_branch_id: int,
        user_id: int,
    ) -> int:
        """Switch the active branch for a given user message's AI replies."""
        await ConversationService._check_project_owner(db, project_id, user_id)
        conv = await conversation_dao.get(db, conversation_id)
        if not conv or conv.project_id != project_id:
            raise errors.NotFoundError(msg='Conversation does not exist')

        return await message_dao.switch_branch(
            db, conversation_id, message_id, target_branch_id,
        )

    @staticmethod
    async def edit_and_truncate(
        *,
        db: AsyncSession,
        project_id: int,
        conversation_id: int,
        message_id: int,
        user_id: int,
        new_content: str,
    ) -> str:
        """
        Edit a message and truncate all messages after it (DeepSeek mode).
        Returns the edited message content; the frontend then automatically triggers regeneration.
        """
        await ConversationService._check_project_owner(db, project_id, user_id)
        conv = await conversation_dao.get(db, conversation_id)
        if not conv or conv.project_id != project_id:
            raise errors.NotFoundError(msg='Conversation does not exist')
        msg = await message_dao.get(db, message_id)
        if not msg or msg.conversation_id != conversation_id:
            raise errors.NotFoundError(msg='Message does not exist')
        if msg.role != 'user':
            raise errors.RequestError(msg='Only user messages can be edited')

        await message_dao.soft_delete_after(db, conversation_id, message_id)

        from backend.app.conversation.schema.message import UpdateMessageParam
        await message_dao.update(db, message_id, UpdateMessageParam(content=new_content))

        return new_content

    @staticmethod
    async def get_resources(
        *,
        db: AsyncSession,
        project_id: int,
        conversation_id: int,
        user_id: int,
        resource_type: str | None = None,
    ) -> list[dict]:
        await ConversationService.get(db=db, project_id=project_id, pk=conversation_id, user_id=user_id)
        bindings = await conversation_resource_dao.get_by_conversation(db, conversation_id, resource_type)
        return [
            {
                'id': b.id,
                'conversation_id': b.conversation_id,
                'resource_type': b.resource_type,
                'resource_id': b.resource_id,
            }
            for b in bindings
        ]

    @staticmethod
    async def bind_resource(
        *,
        db: AsyncSession,
        project_id: int,
        conversation_id: int,
        user_id: int,
        resource_type: str,
        resource_id: int,
    ) -> None:
        if resource_type not in ('knowledge_base', 'mcp_server'):
            raise errors.RequestError(msg='Unsupported resource type')
        await ConversationService.get(db=db, project_id=project_id, pk=conversation_id, user_id=user_id)
        existing = await conversation_resource_dao.get_binding(db, conversation_id, resource_type, resource_id)
        if existing:
            return
        await conversation_resource_dao.bind(db, conversation_id, resource_type, resource_id)

    @staticmethod
    async def unbind_resource(
        *,
        db: AsyncSession,
        project_id: int,
        conversation_id: int,
        user_id: int,
        resource_type: str,
        resource_id: int,
    ) -> int:
        await ConversationService.get(db=db, project_id=project_id, pk=conversation_id, user_id=user_id)
        return await conversation_resource_dao.unbind(db, conversation_id, resource_type, resource_id)


conversation_service: ConversationService = ConversationService()
