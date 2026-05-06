"""知识库文档服务：上传 → MinIO → 创建记录 → 触发向量化。"""

from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.knowledge.crud.crud_knowledge_base import knowledge_base_dao
from backend.app.knowledge.crud.crud_knowledge_document import knowledge_document_dao
from backend.app.knowledge.model import KnowledgeDocument
from backend.app.knowledge.schema.knowledge_document import CreateKnowledgeDocumentParam
from backend.common.exception import errors
from backend.common.minio_client import delete_file, upload_file
from backend.common.pagination import paging_data


class KnowledgeDocumentService:
    @staticmethod
    async def _check_kb_owner(db: AsyncSession, kb_id: int, user_id: int) -> None:
        kb = await knowledge_base_dao.get(db, kb_id)
        if not kb:
            raise errors.NotFoundError(msg='知识库不存在')
        if kb.user_id != user_id:
            raise errors.NotFoundError(msg='知识库不存在')

    @staticmethod
    async def get(*, db: AsyncSession, kb_id: int, doc_id: int, owner_id: int) -> KnowledgeDocument:
        await KnowledgeDocumentService._check_kb_owner(db, kb_id, owner_id)
        obj = await knowledge_document_dao.get(db, doc_id)
        if not obj or obj.knowledge_base_id != kb_id:
            raise errors.NotFoundError(msg='文档不存在')
        return obj

    @staticmethod
    async def get_list(*, db: AsyncSession, kb_id: int, owner_id: int) -> dict[str, Any]:
        await KnowledgeDocumentService._check_kb_owner(db, kb_id, owner_id)
        doc_select = await knowledge_document_dao.get_list(knowledge_base_id=kb_id)
        return await paging_data(db, doc_select)

    @staticmethod
    async def upload(
        *,
        db: AsyncSession,
        kb_id: int,
        owner_id: int,
        file: UploadFile | None = None,
        title: str | None = None,
        source_type: str = 'upload',
        content: str | None = None,
        url: str | None = None,
    ) -> KnowledgeDocument:
        """上传文档：文件存 MinIO，元数据存 DB，触发向量化任务。"""
        await KnowledgeDocumentService._check_kb_owner(db, kb_id, owner_id)

        file_path: str | None = None
        file_size: int | None = None

        if source_type == 'upload':
            if not file:
                raise errors.RequestError(msg='请上传文件')
            file_data = await file.read()
            file_size = len(file_data)
            object_name = f'knowledge/{kb_id}/{file.filename}'
            file_path = upload_file(object_name, file_data, file.content_type or 'application/octet-stream')
            if not title:
                title = file.filename or '未命名文档'
        elif source_type == 'text':
            if not content:
                raise errors.RequestError(msg='请提供文本内容')
            if not title:
                title = content[:50] + ('...' if len(content) > 50 else '')
        elif source_type == 'url':
            if not url:
                raise errors.RequestError(msg='请提供 URL')
            if not title:
                title = url
            content = url
        else:
            raise errors.RequestError(msg=f'不支持的来源类型: {source_type}')

        obj = CreateKnowledgeDocumentParam(
            title=title,
            source_type=source_type,
            file_path=file_path,
            file_size=file_size,
            content=content,
        )
        doc = await knowledge_document_dao.create(db, obj, knowledge_base_id=kb_id)

        from backend.app.knowledge.service.document_pipeline import trigger_vectorize

        trigger_vectorize(doc.id, kb_id)

        return doc

    @staticmethod
    async def delete(*, db: AsyncSession, kb_id: int, doc_id: int, owner_id: int) -> int:
        await KnowledgeDocumentService._check_kb_owner(db, kb_id, owner_id)
        doc = await knowledge_document_dao.get(db, doc_id)
        if not doc or doc.knowledge_base_id != kb_id:
            raise errors.NotFoundError(msg='文档不存在')
        if doc.file_path:
            delete_file(doc.file_path)
        return await knowledge_document_dao.delete(db, doc_id)

    @staticmethod
    async def reprocess(*, db: AsyncSession, kb_id: int, doc_id: int, owner_id: int) -> int:
        await KnowledgeDocumentService._check_kb_owner(db, kb_id, owner_id)
        doc = await knowledge_document_dao.get(db, doc_id)
        if not doc or doc.knowledge_base_id != kb_id:
            raise errors.NotFoundError(msg='文档不存在')
        count = await knowledge_document_dao.update_status(db, doc_id, 'pending', None)

        from backend.app.knowledge.service.document_pipeline import trigger_vectorize

        trigger_vectorize(doc_id, kb_id)
        return count


knowledge_document_service: KnowledgeDocumentService = KnowledgeDocumentService()
