from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.mcp.model import MCPTool


class CRUDMCPTool(CRUDPlus[MCPTool]):
    async def get(self, db: AsyncSession, pk: int) -> MCPTool | None:
        return await self.select_model_by_column(db, id=pk)

    async def get_by_server(self, db: AsyncSession, mcp_server_id: int) -> list[MCPTool]:
        return await self.select_models(db, mcp_server_id=mcp_server_id)

    async def create(
        self,
        db: AsyncSession,
        *,
        mcp_server_id: int,
        name: str,
        description: str | None = None,
        input_schema: dict | None = None,
    ) -> MCPTool:
        instance = MCPTool(
            mcp_server_id=mcp_server_id,
            name=name,
            description=description,
            input_schema=input_schema,
        )
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def delete_by_server(self, db: AsyncSession, mcp_server_id: int) -> int:
        tools = await self.select_models(db, mcp_server_id=mcp_server_id)
        if not tools:
            return 0
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=[t.id for t in tools])


mcp_tool_dao: CRUDMCPTool = CRUDMCPTool(MCPTool)
