from typing import Annotated

from fastapi import APIRouter, Path, Request

from backend.app.mcp.schema.mcp_server import BindAgentToolParam
from backend.app.mcp.service.mcp_binding_service import mcp_binding_service
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSessionTransaction

router = APIRouter()


@router.post('/{aid}/tools', summary='绑定工具到 Agent', dependencies=[DependsJwtAuth])
async def bind_agent_tool(
    db: CurrentSessionTransaction,
    request: Request,
    aid: Annotated[int, Path(description='Agent ID')],
    obj: BindAgentToolParam,
) -> ResponseModel:
    await mcp_binding_service.bind_agent_tool(
        db=db,
        agent_id=aid,
        mcp_tool_id=obj.mcp_tool_id,
        user_id=request.user.id,
    )
    return response_base.success()


@router.delete('/{aid}/tools/{tid}', summary='解绑 Agent 工具', dependencies=[DependsJwtAuth])
async def unbind_agent_tool(
    db: CurrentSessionTransaction,
    request: Request,
    aid: Annotated[int, Path(description='Agent ID')],
    tid: Annotated[int, Path(description='MCP 工具 ID')],
) -> ResponseModel:
    count = await mcp_binding_service.unbind_agent_tool(
        db=db,
        agent_id=aid,
        mcp_tool_id=tid,
        user_id=request.user.id,
    )
    if count > 0:
        return response_base.success()
    return response_base.fail()
