from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.mcp.model import ProjectMCP


class CRUDProjectMCP(CRUDPlus[ProjectMCP]):
    async def get(self, db: AsyncSession, pk: int) -> ProjectMCP | None:
        return await self.select_model_by_column(db, id=pk)

    async def get_by_project(self, db: AsyncSession, project_id: int) -> list[ProjectMCP]:
        return await self.select_models(db, project_id=project_id)

    async def get_binding(self, db: AsyncSession, project_id: int, mcp_server_id: int) -> ProjectMCP | None:
        return await self.select_model_by_column(db, project_id=project_id, mcp_server_id=mcp_server_id)

    async def create(self, db: AsyncSession, project_id: int, mcp_server_id: int) -> ProjectMCP:
        instance = self.model(project_id=project_id, mcp_server_id=mcp_server_id)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def delete_binding(self, db: AsyncSession, project_id: int, mcp_server_id: int) -> int:
        binding = await self.get_binding(db, project_id, mcp_server_id)
        if not binding:
            return 0
        return await self.delete_model_by_column(db, id=binding.id)


project_mcp_dao: CRUDProjectMCP = CRUDProjectMCP(ProjectMCP)
