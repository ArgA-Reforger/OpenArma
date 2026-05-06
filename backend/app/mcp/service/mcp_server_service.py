"""MCP Server 管理服务。"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.mcp.crud.crud_mcp_server import mcp_server_dao
from backend.app.mcp.crud.crud_mcp_tool import mcp_tool_dao
from backend.app.mcp.model import MCPServer
from backend.app.mcp.schema.mcp_server import (
    CreateMCPServerParam,
    GetMCPServerDetail,
    UpdateMCPServerParam,
)
from backend.app.mcp.schema.mcp_tool import GetMCPToolDetail
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.utils.timezone import timezone

log = logging.getLogger(__name__)


class MCPServerService:
    @staticmethod
    async def get(*, db: AsyncSession, pk: int, user_id: int) -> GetMCPServerDetail:
        server = await mcp_server_dao.get(db, pk)
        if not server:
            raise errors.NotFoundError(msg='MCP 服务器不存在')
        if server.user_id != user_id and server.visibility == 'private':
            raise errors.NotFoundError(msg='MCP 服务器不存在')
        tools = await mcp_tool_dao.get_by_server(db, pk)
        detail = GetMCPServerDetail.model_validate(server)
        return detail.model_copy(update={'tools': [GetMCPToolDetail.model_validate(t) for t in tools]})

    @staticmethod
    async def get_list(*, db: AsyncSession, user_id: int, visibility: str | None = None) -> dict[str, Any]:
        select = await mcp_server_dao.get_list(user_id=user_id, visibility=visibility)
        return await paging_data(db, select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateMCPServerParam, user_id: int) -> MCPServer:
        return await mcp_server_dao.create(db, obj, user_id=user_id)

    @staticmethod
    async def update(
        *,
        db: AsyncSession,
        pk: int,
        obj: UpdateMCPServerParam,
        user_id: int,
    ) -> int:
        server = await mcp_server_dao.get(db, pk)
        if not server:
            raise errors.NotFoundError(msg='MCP 服务器不存在')
        if server.user_id != user_id:
            raise errors.NotFoundError(msg='MCP 服务器不存在')
        return await mcp_server_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pk: int, user_id: int) -> int:
        server = await mcp_server_dao.get(db, pk)
        if not server:
            raise errors.NotFoundError(msg='MCP 服务器不存在')
        if server.user_id != user_id:
            raise errors.NotFoundError(msg='MCP 服务器不存在')
        return await mcp_server_dao.delete(db, pk)

    @staticmethod
    async def discover(*, db: AsyncSession, pk: int, user_id: int) -> list[GetMCPToolDetail]:
        """连接 MCP Server，发现并持久化工具列表。"""
        server = await mcp_server_dao.get(db, pk)
        if not server:
            raise errors.NotFoundError(msg='MCP 服务器不存在')
        if server.user_id != user_id:
            raise errors.NotFoundError(msg='MCP 服务器不存在')

        from backend.app.mcp.service.mcp_client import discover_tools

        try:
            tools_data = await discover_tools(server.transport_type, server.connection_config)
        except Exception as e:
            log.exception(f'MCP discover failed for server {pk}')
            raise errors.RequestError(msg=f'连接 MCP 服务器失败: {e}')

        await mcp_tool_dao.delete_by_server(db, pk)

        created_tools = []
        for tool_info in tools_data:
            tool = await mcp_tool_dao.create(
                db,
                mcp_server_id=pk,
                name=tool_info['name'],
                description=tool_info.get('description'),
                input_schema=tool_info.get('input_schema'),
            )
            created_tools.append(tool)

        await mcp_server_dao.update_model(db, pk, {'last_discovered_at': timezone.now()})

        return [GetMCPToolDetail.model_validate(t) for t in created_tools]

    @staticmethod
    async def clone(*, db: AsyncSession, pk: int, user_id: int) -> MCPServer:
        source = await mcp_server_dao.get(db, pk)
        if not source:
            raise errors.NotFoundError(msg='MCP 服务器不存在')
        if source.user_id != user_id and source.visibility == 'private':
            raise errors.NotFoundError(msg='MCP 服务器不存在')
        clone_data = CreateMCPServerParam(
            name=f'{source.name} (Copy)',
            description=source.description,
            transport_type=source.transport_type,
            connection_config=source.connection_config,
            is_active=source.is_active,
            visibility='private',
        )
        return await mcp_server_dao.create(db, clone_data, user_id=user_id)


mcp_server_service: MCPServerService = MCPServerService()
