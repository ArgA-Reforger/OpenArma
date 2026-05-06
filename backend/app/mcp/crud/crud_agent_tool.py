from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.mcp.model import AgentTool


class CRUDAgentTool(CRUDPlus[AgentTool]):
    async def get(self, db: AsyncSession, pk: int) -> AgentTool | None:
        return await self.select_model_by_column(db, id=pk)

    async def get_by_agent(self, db: AsyncSession, agent_id: int) -> list[AgentTool]:
        return await self.select_models(db, agent_id=agent_id)

    async def get_binding(self, db: AsyncSession, agent_id: int, mcp_tool_id: int) -> AgentTool | None:
        return await self.select_model_by_column(db, agent_id=agent_id, mcp_tool_id=mcp_tool_id)

    async def create(self, db: AsyncSession, agent_id: int, mcp_tool_id: int, is_enabled: bool = True) -> AgentTool:
        instance = self.model(agent_id=agent_id, mcp_tool_id=mcp_tool_id, is_enabled=is_enabled)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def delete_binding(self, db: AsyncSession, agent_id: int, mcp_tool_id: int) -> int:
        binding = await self.get_binding(db, agent_id, mcp_tool_id)
        if not binding:
            return 0
        return await self.delete_model_by_column(db, id=binding.id)


agent_tool_dao: CRUDAgentTool = CRUDAgentTool(AgentTool)
