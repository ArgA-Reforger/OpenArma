from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.knowledge.crud.crud_knowledge_base import knowledge_base_dao
from backend.app.knowledge.model import KnowledgeBase
from backend.app.knowledge.schema.knowledge_base import CreateKnowledgeBaseParam, UpdateKnowledgeBaseParam
from backend.common.exception import errors
from backend.common.pagination import paging_data


class KnowledgeBaseService:
    @staticmethod
    async def _check_access(db: AsyncSession, pk: int, user_id: int) -> KnowledgeBase:
        obj = await knowledge_base_dao.get(db, pk)
        if not obj:
            raise errors.NotFoundError(msg='知识库不存在')
        if obj.user_id != user_id and obj.visibility == 'private':
            raise errors.NotFoundError(msg='知识库不存在')
        return obj

    @staticmethod
    async def _check_owner(db: AsyncSession, pk: int, user_id: int) -> KnowledgeBase:
        obj = await knowledge_base_dao.get(db, pk)
        if not obj or obj.user_id != user_id:
            raise errors.NotFoundError(msg='知识库不存在')
        return obj

    @staticmethod
    async def get(*, db: AsyncSession, pk: int, owner_id: int) -> KnowledgeBase:
        return await KnowledgeBaseService._check_access(db, pk, owner_id)

    @staticmethod
    async def get_list(*, db: AsyncSession, owner_id: int, visibility: str | None = None) -> dict[str, Any]:
        kb_select = await knowledge_base_dao.get_list(user_id=owner_id, visibility=visibility)
        return await paging_data(db, kb_select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateKnowledgeBaseParam, owner_id: int) -> KnowledgeBase:
        return await knowledge_base_dao.create(db, obj, user_id=owner_id)

    @staticmethod
    async def update(
        *,
        db: AsyncSession,
        pk: int,
        obj: UpdateKnowledgeBaseParam,
        owner_id: int,
    ) -> int:
        await KnowledgeBaseService._check_owner(db, pk, owner_id)
        return await knowledge_base_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int, owner_id: int) -> int:
        await KnowledgeBaseService._check_owner(db, pk, owner_id)
        return await knowledge_base_dao.delete(db, pk)

    @staticmethod
    async def clone(*, db: AsyncSession, pk: int, owner_id: int) -> KnowledgeBase:
        source = await knowledge_base_dao.get(db, pk)
        if not source:
            raise errors.NotFoundError(msg='知识库不存在')
        if source.user_id != owner_id and source.visibility == 'private':
            raise errors.NotFoundError(msg='知识库不存在')
        clone_data = CreateKnowledgeBaseParam(
            name=f'{source.name} (Copy)',
            description=source.description,
            embedding_model=source.embedding_model,
            embedding_provider_id=source.embedding_provider_id if source.user_id == owner_id else None,
            chunk_size=source.chunk_size,
            chunk_overlap=source.chunk_overlap,
            status='ready',
            visibility='private',
        )
        return await knowledge_base_dao.create(db, clone_data, user_id=owner_id)


knowledge_base_service: KnowledgeBaseService = KnowledgeBaseService()
