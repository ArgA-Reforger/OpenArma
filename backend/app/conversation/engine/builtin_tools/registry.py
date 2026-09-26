"""Builtin tool registry: manages the definitions and executors of all platform builtin tools."""

import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

ToolHandler = Callable[..., Coroutine[Any, Any, str]]


@dataclass
class BuiltinToolDef:
    """Runtime definition of a builtin tool."""

    name: str
    description: str
    input_schema: dict
    handler: ToolHandler
    display_name: str = ''


class BuiltinToolRegistry:
    """
    Builtin tool registry.

    Registers all builtin tool handler functions on system startup.
    At runtime, based on the Agent's builtin_tools config,
    filters the enabled tools and builds tools + handlers for the graph engine to use.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BuiltinToolDef] = {}

    def register(
        self,
        name: str,
        *,
        description: str,
        input_schema: dict,
        display_name: str = '',
    ) -> Callable[[ToolHandler], ToolHandler]:
        """Decorator: registers a builtin tool handler function."""
        def decorator(func: ToolHandler) -> ToolHandler:
            self._tools[name] = BuiltinToolDef(
                name=name,
                description=description,
                input_schema=input_schema,
                handler=func,
                display_name=display_name or name,
            )
            return func
        return decorator

    def get_all(self) -> dict[str, BuiltinToolDef]:
        return dict(self._tools)

    def get(self, name: str) -> BuiltinToolDef | None:
        return self._tools.get(name)

    def build_tools_for_agent(
        self,
        builtin_tools_config: dict | None,
        *,
        context: dict | None = None,
    ) -> tuple[list[dict], dict[str, ToolHandler]]:
        """
        Build the OpenAI tools list and handler mapping from the Agent's builtin_tools config.

        :param builtin_tools_config: Agent.builtin_tools JSON, e.g. {"web_search": {"enabled": true}, ...}
        :param context: runtime context, for ChatService to bind concrete parameters afterward
        :return: (tools_list, handlers_dict)
        """
        if not builtin_tools_config:
            return [], {}

        tools: list[dict] = []
        handlers: dict[str, ToolHandler] = {}

        for tool_name, tool_cfg in builtin_tools_config.items():
            if not isinstance(tool_cfg, dict) or not tool_cfg.get('enabled'):
                continue

            tool_def = self._tools.get(tool_name)
            if not tool_def:
                log.warning(f'Builtin tool not registered: {tool_name}')
                continue

            tools.append({
                'name': tool_def.name,
                'description': tool_def.description,
                'input_schema': tool_def.input_schema,
            })
            handlers[tool_def.name] = tool_def.handler

        return tools, handlers


builtin_registry = BuiltinToolRegistry()
