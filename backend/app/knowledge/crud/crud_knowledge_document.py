from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.knowledge.model import KnowledgeDocument
from backend.app.knowledge.schema.knowledge_document import CreateKnowledgeDocumentParam


class CRUDKnowledgeDocument(CRUDPlus[KnowledgeDocument]):
    async def get(self, db: AsyncSession, pk: int) -> KnowledgeDocument | None:
        return await self.select_model_by_column(db, id=pk, del_flag=False)

    async def get_list(self, knowledge_base_id: int) -> Select:
        return await self.select_order('id', 'desc', knowledge_base_id=knowledge_base_id, del_flag=False)

    async def create(self, db: AsyncSession, obj: CreateKnowledgeDocumentParam, knowledge_base_id: int) -> KnowledgeDocument:
        create_data = obj.model_dump()
        create_data['knowledge_base_id'] = knowledge_base_id
        instance = self.model(**create_data)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(db, id=pk, logical_deletion=True, deleted_flag_column='del_flag')

    async def update_status(self, db: AsyncSession, pk: int, status: str, error_message: str | None = None) -> int:
        data = {'status': status}
        if error_message is not None:
            data['error_message'] = error_message
        return await self.update_model(db, pk, data)


knowledge_document_dao: CRUDKnowledgeDocument = CRUDKnowledgeDocument(KnowledgeDocument)
