from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.knowledge.model import ProjectKnowledgeBase


class CRUDProjectKnowledgeBase(CRUDPlus[ProjectKnowledgeBase]):
    async def get_by_project(self, db: AsyncSession, project_id: int) -> list[ProjectKnowledgeBase]:
        return await self.select_models(db, project_id=project_id)

    async def get_binding(self, db: AsyncSession, project_id: int, knowledge_base_id: int) -> ProjectKnowledgeBase | None:
        return await self.select_model_by_column(db, project_id=project_id, knowledge_base_id=knowledge_base_id)

    async def create(self, db: AsyncSession, project_id: int, knowledge_base_id: int) -> ProjectKnowledgeBase:
        instance = self.model(project_id=project_id, knowledge_base_id=knowledge_base_id)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def delete_binding(self, db: AsyncSession, project_id: int, knowledge_base_id: int) -> int:
        return await self.delete_model_by_column(db, project_id=project_id, knowledge_base_id=knowledge_base_id)


project_knowledge_base_dao: CRUDProjectKnowledgeBase = CRUDProjectKnowledgeBase(ProjectKnowledgeBase)
