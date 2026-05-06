from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.crud.crud_agent import agent_dao
from backend.app.mcp.crud.crud_agent_tool import agent_tool_dao
from backend.app.mcp.crud.crud_mcp_tool import mcp_tool_dao
from backend.common.exception import errors


class MCPBindingService:
    @staticmethod
    async def bind_agent_tool(
        *,
        db: AsyncSession,
        agent_id: int,
        mcp_tool_id: int,
        user_id: int,
    ) -> None:
        agent = await agent_dao.get(db, agent_id)
        if not agent or agent.user_id != user_id:
            raise errors.NotFoundError(msg='Agent 不存在')
        tool = await mcp_tool_dao.get(db, mcp_tool_id)
        if not tool:
            raise errors.NotFoundError(msg='MCP 工具不存在')
        existing = await agent_tool_dao.get_binding(db, agent_id, mcp_tool_id)
        if existing:
            raise errors.ConflictError(msg='已绑定该工具')
        await agent_tool_dao.create(db, agent_id=agent_id, mcp_tool_id=mcp_tool_id)

    @staticmethod
    async def unbind_agent_tool(
        *,
        db: AsyncSession,
        agent_id: int,
        mcp_tool_id: int,
        user_id: int,
    ) -> int:
        agent = await agent_dao.get(db, agent_id)
        if not agent or agent.user_id != user_id:
            raise errors.NotFoundError(msg='Agent 不存在')
        return await agent_tool_dao.delete_binding(db, agent_id, mcp_tool_id)


mcp_binding_service: MCPBindingService = MCPBindingService()
