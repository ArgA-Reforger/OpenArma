"""MCP 客户端：连接 MCP Server，发现工具，调用工具。"""

import logging
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

log = logging.getLogger(__name__)


async def discover_tools(
    transport_type: str,
    connection_config: dict,
) -> list[dict[str, Any]]:
    """
    连接 MCP Server 并获取 tools/list。

    :param transport_type: 传输类型 (sse / streamable_http / stdio)
    :param connection_config: 连接配置 (url, command, args, env 等)
    :return: 工具列表 [{name, description, input_schema}, ...]
    """
    url = connection_config.get('url', '')

    if transport_type == 'sse':
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {
                        'name': tool.name,
                        'description': tool.description or '',
                        'input_schema': tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                    }
                    for tool in result.tools
                ]

    elif transport_type == 'streamable_http':
        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {
                        'name': tool.name,
                        'description': tool.description or '',
                        'input_schema': tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                    }
                    for tool in result.tools
                ]

    elif transport_type == 'stdio':
        from mcp.client.stdio import StdioServerParameters, stdio_client

        command = connection_config.get('command', '')
        args = connection_config.get('args', [])
        env = connection_config.get('env')
        server_params = StdioServerParameters(command=command, args=args, env=env)
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {
                        'name': tool.name,
                        'description': tool.description or '',
                        'input_schema': tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                    }
                    for tool in result.tools
                ]

    else:
        raise ValueError(f'Unsupported transport type: {transport_type}')


async def call_tool(
    transport_type: str,
    connection_config: dict,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    """
    调用 MCP Server 上的指定工具。

    :param transport_type: 传输类型
    :param connection_config: 连接配置
    :param tool_name: 工具名称
    :param arguments: 工具参数
    :return: 工具调用结果
    """
    url = connection_config.get('url', '')

    if transport_type == 'sse':
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return _extract_result(result)

    elif transport_type == 'streamable_http':
        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return _extract_result(result)

    elif transport_type == 'stdio':
        from mcp.client.stdio import StdioServerParameters, stdio_client

        command = connection_config.get('command', '')
        args = connection_config.get('args', [])
        env = connection_config.get('env')
        server_params = StdioServerParameters(command=command, args=args, env=env)
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return _extract_result(result)

    else:
        raise ValueError(f'Unsupported transport type: {transport_type}')


def _extract_result(result) -> str:
    """从 MCP CallToolResult 中提取文本内容。"""
    if not result.content:
        return ''
    parts = []
    for item in result.content:
        if hasattr(item, 'text'):
            parts.append(item.text)
    return '\n'.join(parts) if parts else str(result.content)
