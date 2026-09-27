"""MCP client: connect to MCP Server, discover tools, and call tools."""

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
    Connect to MCP Server and get tools/list.

    :param transport_type: Transport type (sse / streamable_http / stdio)
    :param connection_config: Connection config (url, command, args, env, etc.)
    :return: Tool list [{name, description, input_schema}, ...]
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
    Call the specified tool on the MCP Server.

    :param transport_type: Transport type
    :param connection_config: Connection configuration
    :param tool_name: Tool name
    :param arguments: Tool arguments
    :return: Tool call result
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
    """Extract text content from MCP CallToolResult."""
    if not result.content:
        return ''
    parts = []
    for item in result.content:
        if hasattr(item, 'text'):
            parts.append(item.text)
    return '\n'.join(parts) if parts else str(result.content)
