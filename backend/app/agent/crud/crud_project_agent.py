from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.agent.model.project_agent import ProjectAgent


class CRUDProjectAgent(CRUDPlus[ProjectAgent]):
    async def get_by_project(self, db: AsyncSession, project_id: int) -> list[ProjectAgent]:
        return await self.select_models(db, project_id=project_id)

    async def get_binding(self, db: AsyncSession, project_id: int, agent_id: int) -> ProjectAgent | None:
        return await self.select_model_by_column(db, project_id=project_id, agent_id=agent_id)

    async def create(
        self,
        db: AsyncSession,
        project_id: int,
        agent_id: int,
    ) -> ProjectAgent:
        instance = ProjectAgent(project_id=project_id, agent_id=agent_id)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def delete_binding(self, db: AsyncSession, project_id: int, agent_id: int) -> int:
        binding = await self.get_binding(db, project_id, agent_id)
        if not binding:
            return 0
        return await self.delete_model_by_column(db, id=binding.id)


project_agent_dao: CRUDProjectAgent = CRUDProjectAgent(ProjectAgent)
